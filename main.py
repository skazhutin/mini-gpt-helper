from __future__ import annotations

import threading

from AppKit import (
    NSApp,
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSPopover,
    NSPopoverBehaviorTransient,
)
from Foundation import NSObject
from PyObjCTools import AppHelper

from clipboard import ClipboardService
from config import AppConfig
from hotkey import GlobalHotkey
from menubar import MenuBarController
from openai_client import AIClipboardClient
from popover import PopoverViewController
from state import AppState, MenuStatus


class AppDelegate(NSObject):
    def init(self):
        self = super().init()
        if self is None:
            return None

        self.config = AppConfig.load()
        self.state = AppState()
        self.clipboard = ClipboardService()
        self.client = AIClipboardClient(provider=self.config.provider)
        self.menu = MenuBarController(self, "togglePopover:")
        self.popover = NSPopover.alloc().init()
        self.popover.setBehavior_(NSPopoverBehaviorTransient)

        self.popover_controller = PopoverViewController.alloc().initWithCallbacks_(
            self.handle_send,
            self.toggle_theme,
        )
        self.popover.setContentViewController_(self.popover_controller)
        self.popover_controller.applyTheme_(self.config.theme)

        self.hotkey = GlobalHotkey(self.handle_hotkey, key_name=self.config.hotkey_key)
        self.hotkey.start()
        return self

    def applicationDidFinishLaunching_(self, _notification):
        NSApp().setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    def togglePopover_(self, _sender):
        button = self.menu.item.button()
        if self.popover.isShown():
            self.popover.performClose_(self)
        else:
            size = self.popover_controller.expanded_size if self.popover_controller.expanded else self.popover_controller.compact_size
            self.popover.setContentSize_(size)
            self.popover.showRelativeToRect_ofView_preferredEdge_(button.bounds(), button, 1)

    def toggle_theme(self):
        self.config.theme = "dark" if self.config.theme == "light" else "light"
        self.popover_controller.applyTheme_(self.config.theme)

    def handle_send(self, instruction: str):
        self._process_clipboard(instruction)

    def handle_hotkey(self):
        self._process_clipboard("")

    def _process_clipboard(self, instruction: str):
        self._set_status(MenuStatus.PROCESSING)
        self.popover_controller.setBusy_(True)

        def worker():
            try:
                payload = self.clipboard.read()
                result = self.client.complete(instruction, payload)
                self.clipboard.write_text(result)
                self.state.last_response = result
                self.state.last_error = None
                AppHelper.callAfter(self._on_success, result)
            except Exception as exc:  # noqa: BLE001
                self.state.last_error = str(exc)
                AppHelper.callAfter(self._on_error, str(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _on_success(self, result: str):
        self._set_status(MenuStatus.SUCCESS)
        self.popover_controller.setBusy_(False)
        self.popover_controller.setOutput_(result)

    def _on_error(self, error_text: str):
        self._set_status(MenuStatus.ERROR)
        self.popover_controller.setBusy_(False)
        self.popover_controller.setOutput_(f"Error: {error_text}")

    def _set_status(self, status: MenuStatus):
        self.state.status = status
        self.menu.set_status(status)


if __name__ == "__main__":
    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    AppHelper.runEventLoop()
