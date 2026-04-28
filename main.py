from __future__ import annotations

import faulthandler
import json
import os
import signal
import sys
import threading
import traceback

from app_logging import log, set_enabled
from config import resolve_config_path


def _load_bootstrap_logging_flag(path: str = "config.json") -> bool:
    env_value = os.getenv("APP_LOGGING", "").strip().lower()
    if env_value in {"1", "true", "yes", "on"}:
        return True
    if env_value in {"0", "false", "no", "off"}:
        return False

    try:
        raw = json.loads(resolve_config_path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return False
    except Exception:
        return False

    value = str(raw.get("logging", "0")).strip().lower()
    return value in {"1", "true", "yes", "on"}


def _install_bootstrap_debug() -> None:
    set_enabled(_load_bootstrap_logging_flag())
    faulthandler.enable(all_threads=True)

    def excepthook(exc_type, exc_value, exc_tb):
        log(f"Uncaught exception: {exc_type.__name__}: {exc_value}")
        traceback.print_exception(exc_type, exc_value, exc_tb)

    sys.excepthook = excepthook
    log("Bootstrap debug initialized")


log("Importing AppKit / PyObjC modules")

from AppKit import (
    NSApp,
    NSAppearance,
    NSAppearanceNameAqua,
    NSAppearanceNameDarkAqua,
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSMenu,
    NSMenuItem,
    NSWorkspace,
)
from Foundation import NSObject, NSURL
from PyObjCTools import AppHelper
from objc import super
from Quartz import CGSessionCopyCurrentDictionary

from clipboard import ClipboardPayload, ClipboardService
from config import AppConfig
from gpt_client import AIClipboardClient
from hotkey import GlobalHotkey
from menubar import MenuBarController
from output_window import OutputWindowController
from popover import PopoverViewController
from state import AppState, MenuStatus

log("Application modules imported")


def ensure_gui_session() -> None:
    if CGSessionCopyCurrentDictionary() is not None:
        return

    raise SystemExit(
        "mini-gpt-helper must be launched from an active macOS GUI login session. "
        "Start it from Terminal/iTerm while logged into the desktop, not from a headless shell."
    )


class AppDelegate(NSObject):
    def init(self):
        self = super().init()
        if self is None:
            return None

        self.config = AppConfig.load()
        set_enabled(bool(self.config.logging))
        log(
            "AppDelegate initialized with "
            f"provider={self.config.provider}, theme={self.config.theme}, "
            f"hotkey_key={self.config.hotkey_key}, logging={self.config.logging}"
        )
        self.state = AppState()
        self.clipboard = ClipboardService()
        self.client = AIClipboardClient(
            provider=self.config.provider,
            openai_model=self.config.openai_model,
            openai_api_key=self.config.openai_api_key,
            gemini_api_key=self.config.gemini_api_key,
            gemini_model=self.config.gemini_model,
            prompt=self.config.prompt,
        )
        self.menu = MenuBarController()
        self._in_flight = False
        log("Menu bar controller created")

        self.menu_controller = PopoverViewController.alloc().initWithCallbacks_(
            {
                "send": self.handle_send,
                "show": self.show_output_window,
                "config": self.open_config,
                "theme": self.toggle_theme,
                "quit": self.quit_application,
            }
        )
        self.output_window = OutputWindowController(theme=self.config.theme)
        self.status_menu = self._build_status_menu()
        self.menu.set_menu(self.status_menu)
        self._apply_theme(self.config.theme)
        log("Status menu and output window configured")

        self.hotkey = GlobalHotkey(self.handle_hotkey, key_name=self.config.hotkey_key)
        return self

    def _build_status_menu(self):
        menu = NSMenu.alloc().initWithTitle_("mini-gpt-helper")
        menu.setAutoenablesItems_(False)
        content_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("", None, "")
        content_item.setView_(self.menu_controller.view())
        menu.addItem_(content_item)
        return menu

    def applicationDidFinishLaunching_(self, _notification):
        NSApp().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        log("Application did finish launching")
        hotkey_ready = self.hotkey.start()
        log(f"Hotkey monitoring start result: {hotkey_ready}")
        if not hotkey_ready:
            self._on_error(
                "Global hotkey is unavailable. Grant Accessibility permission to your terminal/Python in "
                "System Settings > Privacy & Security > Accessibility."
            )

    def applicationWillTerminate_(self, _notification):
        log("Application will terminate; stopping hotkey monitors")
        self.hotkey.stop()

    def _apply_theme(self, theme: str):
        self.menu_controller.applyTheme_(theme)
        self.output_window.apply_theme(theme)
        appearance_name = NSAppearanceNameDarkAqua if theme == "dark" else NSAppearanceNameAqua
        self.status_menu.setAppearance_(NSAppearance.appearanceNamed_(appearance_name))
        self.status_menu.update()
        log(f"Applied status menu theme={theme}")

    def toggle_theme(self):
        self.config.theme = "dark" if self.config.theme == "light" else "light"
        log(f"Theme toggled to {self.config.theme}")
        try:
            self.config.save()
        except Exception as exc:  # noqa: BLE001
            log(f"Failed to save config after theme toggle: {exc}")
        self._apply_theme(self.config.theme)

    def handle_send(self, instruction: str):
        log(f"Send button clicked with instruction_len={len(instruction)}")
        self._process_clipboard(instruction)

    def handle_hotkey(self):
        log("Global hotkey callback fired")
        self._process_clipboard("")

    def show_output_window(self):
        text = self.state.last_response or self.state.last_error or "No output yet."
        self.output_window.set_text(text)
        self.output_window.show()

    def open_config(self):
        config_path = resolve_config_path(self.config.path)
        if not config_path.exists():
            self.config.path = str(config_path)
            self.config.save()

        opened = NSWorkspace.sharedWorkspace().openURL_(NSURL.fileURLWithPath_(str(config_path)))
        if not opened:
            raise RuntimeError(f"Could not open config file: {config_path}")

    def quit_application(self):
        log("Terminating application")
        NSApp().terminate_(self)

    def handle_sigint(self):
        log("SIGINT received; terminating application")
        self.quit_application()

    def _process_clipboard(self, instruction: str):
        if self._in_flight:
            log("Ignoring request because another request is already in flight")
            return

        log(f"Starting clipboard processing with instruction_len={len(instruction)}")
        payload = self.clipboard.read()
        self._in_flight = True
        self._set_status(MenuStatus.PROCESSING)
        self.menu_controller.setBusy_(True)
        self.menu_controller.setStatusText_("Processing clipboard...")

        def worker(copied_payload: ClipboardPayload):
            try:
                log("Worker thread started")
                result = self.client.complete(instruction, copied_payload)
                AppHelper.callAfter(self._on_success, result)
            except Exception as exc:  # noqa: BLE001
                log(f"Worker thread failed: {exc}")
                AppHelper.callAfter(self._on_error, str(exc))

        threading.Thread(target=worker, args=(payload,), daemon=True).start()
        log("Worker thread scheduled")

    def _on_success(self, result: str):
        log(f"Processing succeeded with result_len={len(result)}")
        self.clipboard.write_text(result)
        self.state.last_response = result
        self.state.last_error = None
        self._in_flight = False
        self._set_status(MenuStatus.SUCCESS)
        self.menu_controller.setBusy_(False)
        self.menu_controller.setOutput_(result)
        self.menu_controller.setStatusText_("Ready. Output available.")
        self.output_window.set_text(result)

    def _on_error(self, error_text: str):
        log(f"Processing failed: {error_text}")
        self.state.last_error = error_text
        self._in_flight = False
        self._set_status(MenuStatus.ERROR)
        self.menu_controller.setBusy_(False)
        self.menu_controller.setOutput_(error_text)
        self.menu_controller.setStatusText_(error_text)
        self.output_window.set_text(f"Error: {error_text}")

    def _set_status(self, status: MenuStatus):
        self.state.status = status
        log(f"Status changed to {status.value}")
        self.menu.set_status(status)


def install_signal_handlers(delegate: AppDelegate) -> None:
    state = {"count": 0}

    def handle_signal(signum, _frame):
        state["count"] += 1
        log(f"Received signal {signum}; count={state['count']}")
        if state["count"] == 1:
            AppHelper.callAfter(delegate.handle_sigint)
            return
        log("Forcing process exit after repeated signal")
        os._exit(130)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    log("Installed SIGINT/SIGTERM handlers")


def main() -> None:
    _install_bootstrap_debug()
    ensure_gui_session()
    log("Starting app bootstrap")
    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    install_signal_handlers(delegate)
    log("Entering AppKit event loop")
    AppHelper.runEventLoop(installInterrupt=True)


if __name__ == "__main__":
    main()
