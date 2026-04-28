from __future__ import annotations

import types
import unittest
from unittest.mock import Mock, patch

import main
import menubar
import popover
from state import MenuStatus


class FakeButton:
    def __init__(self):
        self.title = None
        self.target = None
        self.action = None
        self.enabled = True
        self.font = None

    def setTitle_(self, title):
        self.title = title

    def setTarget_(self, target):
        self.target = target

    def setAction_(self, action):
        self.action = action

    def setEnabled_(self, enabled):
        self.enabled = enabled

    def setFont_(self, font):
        self.font = font


class FakeStatusItem:
    def __init__(self):
        self._button = FakeButton()
        self.enabled = None
        self.highlight = None
        self.menu = None

    def button(self):
        return self._button

    def setEnabled_(self, enabled):
        self.enabled = enabled

    def setHighlightMode_(self, highlight):
        self.highlight = highlight

    def setMenu_(self, menu):
        self.menu = menu


class FakeStatusBar:
    def __init__(self):
        self.item = FakeStatusItem()

    def statusItemWithLength_(self, _length):
        return self.item


class FakeRootView:
    def __init__(self):
        self.appearance = None
        self.background_color = None

    def setAppearance_(self, appearance):
        self.appearance = appearance

    def setBackgroundColor_(self, color):
        self.background_color = color


class FakeField:
    def __init__(self, value=""):
        self._value = value

    def stringValue(self):
        return self._value

    def setStringValue_(self, value):
        self._value = value

    def setTextColor_(self, _color):
        return None


class MenuBarControllerTests(unittest.TestCase):
    def test_initializes_status_item_and_allows_attaching_menu(self):
        fake_bar = FakeStatusBar()
        fake_statusbar_class = types.SimpleNamespace(systemStatusBar=lambda: fake_bar)

        with patch("menubar.NSStatusBar", new=fake_statusbar_class):
            controller = menubar.MenuBarController()

        self.assertTrue(fake_bar.item.enabled)
        self.assertTrue(fake_bar.item.highlight)
        self.assertEqual(fake_bar.item._button.title, MenuStatus.IDLE.value)
        controller.set_menu("menu")
        self.assertEqual(fake_bar.item.menu, "menu")
        controller.set_status(MenuStatus.SUCCESS)
        self.assertEqual(fake_bar.item._button.title, MenuStatus.SUCCESS.value)


class PopoverControllerTests(unittest.TestCase):
    def _make_controller(self):
        return popover.PopoverViewController.alloc().initWithCallbacks_(
            {
                "send": lambda _value: None,
                "show": lambda: None,
                "config": lambda: None,
                "theme": lambda: None,
                "quit": lambda: None,
            }
        )

    def test_send_click_trims_input(self):
        seen = []
        controller = popover.PopoverViewController.alloc().initWithCallbacks_(
            {
                "send": lambda value: seen.append(value),
                "show": lambda: None,
                "config": lambda: None,
                "theme": lambda: None,
                "quit": lambda: None,
            }
        )
        controller.input_field = FakeField("  hello  ")
        controller.sendClicked_(None)
        self.assertEqual(seen, ["hello"])

    def test_show_config_theme_and_quit_buttons_invoke_callbacks(self):
        seen = []
        controller = popover.PopoverViewController.alloc().initWithCallbacks_(
            {
                "send": lambda _value: None,
                "show": lambda: seen.append("show"),
                "config": lambda: seen.append("config"),
                "theme": lambda: seen.append("theme"),
                "quit": lambda: seen.append("quit"),
            }
        )
        controller.showClicked_(None)
        controller.configClicked_(None)
        controller.themeClicked_(None)
        controller.quitClicked_(None)
        self.assertEqual(seen, ["show", "config", "theme", "quit"])

    def test_apply_theme_updates_background_and_button_title(self):
        controller = self._make_controller()
        controller._ensure_view_loaded = lambda: None
        controller._root_view = lambda: FakeRootView()
        controller.theme_button = FakeButton()
        controller.status_label = FakeField("")

        fake_appearance_class = types.SimpleNamespace(appearanceNamed_=lambda name: f"appearance:{name}")
        with patch("popover.NSAppearance", new=fake_appearance_class):
            controller.applyTheme_("dark")

        self.assertEqual(controller.theme, "dark")
        self.assertEqual(controller.theme_button.title, "Theme: Dark")

    def test_set_busy_output_and_status_update_controls(self):
        controller = self._make_controller()
        controller._ensure_view_loaded = lambda: None
        controller.send_button = FakeButton()
        controller.show_button = FakeButton()
        controller.status_label = FakeField("")

        controller.setBusy_(True)
        controller.setOutput_("done")
        controller.setStatusText_("hello")

        self.assertFalse(controller.send_button.enabled)
        self.assertTrue(controller.show_button.enabled)
        self.assertEqual(controller.status_label.stringValue(), "hello")


class MainTests(unittest.TestCase):
    def _make_delegate(self, hotkey_ready=True):
        config = main.AppConfig(provider="chatgpt", theme="light", hotkey_key="space", logging=0)
        config.save = Mock()
        fake_menu_bar = Mock()
        fake_menu_view = Mock()
        fake_menu_view.view.return_value = "menu-view"
        fake_output_window = Mock()
        fake_workspace = Mock()
        fake_workspace.openURL_.return_value = True
        fake_hotkey = Mock()
        fake_hotkey.start.return_value = hotkey_ready
        fake_menu = Mock()
        fake_menu.setAppearance_ = Mock()
        fake_menu.update = Mock()
        fake_menu_class = Mock()
        fake_menu_class.alloc.return_value.initWithTitle_.return_value = fake_menu
        fake_menu_item = Mock()
        fake_menu_item_class = Mock()
        fake_menu_item_class.alloc.return_value.initWithTitle_action_keyEquivalent_.return_value = fake_menu_item

        patches = [
            patch.object(main.AppConfig, "load", return_value=config),
            patch("main.ClipboardService", return_value=Mock()),
            patch("main.AIClipboardClient", return_value=Mock()),
            patch("main.MenuBarController", return_value=fake_menu_bar),
            patch("main.PopoverViewController", new=Mock(alloc=Mock(return_value=Mock(initWithCallbacks_=Mock(return_value=fake_menu_view))))),
            patch("main.OutputWindowController", return_value=fake_output_window),
            patch("main.GlobalHotkey", return_value=fake_hotkey),
            patch("main.NSWorkspace", new=Mock(sharedWorkspace=Mock(return_value=fake_workspace))),
            patch("main.NSURL", new=Mock(fileURLWithPath_=Mock(side_effect=lambda path: f"url:{path}"))),
            patch("main.NSMenu", new=fake_menu_class),
            patch("main.NSMenuItem", new=fake_menu_item_class),
            patch("main.set_enabled"),
        ]

        for item in patches:
            item.start()
            self.addCleanup(item.stop)

        delegate = main.AppDelegate.alloc().init()
        return (
            delegate,
            fake_hotkey,
            fake_menu_bar,
            fake_menu_view,
            fake_output_window,
            fake_workspace,
            fake_menu,
            fake_menu_item,
        )

    def test_ensure_gui_session_raises_without_session(self):
        with patch.object(main, "CGSessionCopyCurrentDictionary", return_value=None):
            with self.assertRaises(SystemExit):
                main.ensure_gui_session()

    def test_ensure_gui_session_passes_with_session(self):
        with patch.object(main, "CGSessionCopyCurrentDictionary", return_value={"session": 1}):
            main.ensure_gui_session()

    def test_delegate_builds_status_menu_and_starts_hotkey(self):
        delegate, fake_hotkey, fake_menu_bar, fake_menu_view, _output_window, _workspace, fake_menu, fake_menu_item = self._make_delegate(True)
        fake_app = Mock()

        with patch.object(main, "NSApp", return_value=fake_app):
            delegate.applicationDidFinishLaunching_(None)

        fake_menu_item.setView_.assert_called_once_with("menu-view")
        fake_menu.addItem_.assert_called_once_with(fake_menu_item)
        fake_menu_bar.set_menu.assert_called_once_with(fake_menu)
        fake_hotkey.start.assert_called_once_with()
        self.assertIsNone(delegate.state.last_error)

    def test_delegate_records_hotkey_failure(self):
        delegate, fake_hotkey, _menu_bar, fake_menu_view, _output_window, _workspace, _menu, _item = self._make_delegate(False)
        fake_app = Mock()

        with patch.object(main, "NSApp", return_value=fake_app):
            delegate.applicationDidFinishLaunching_(None)

        fake_hotkey.start.assert_called_once_with()
        self.assertIn("Accessibility", delegate.state.last_error)
        fake_menu_view.setOutput_.assert_called()

    def test_toggle_theme_updates_menu_and_output_window(self):
        delegate, _fake_hotkey, _menu_bar, fake_menu_view, fake_output_window, _workspace, fake_menu, _item = self._make_delegate(True)
        delegate.toggle_theme()
        self.assertEqual(fake_menu_view.applyTheme_.call_args_list[-1].args, ("dark",))
        self.assertEqual(fake_output_window.apply_theme.call_args_list[-1].args, ("dark",))
        self.assertTrue(fake_menu.setAppearance_.called)
        self.assertTrue(fake_menu.update.called)
        delegate.config.save.assert_called_once_with()

    def test_show_output_window_uses_last_response(self):
        delegate, _fake_hotkey, _menu_bar, _menu_view, fake_output_window, _workspace, _menu, _item = self._make_delegate(True)
        delegate.state.last_response = "result"
        delegate.show_output_window()
        fake_output_window.set_text.assert_called_once_with("result")
        fake_output_window.show.assert_called_once_with()

    def test_open_config_uses_workspace(self):
        delegate, _fake_hotkey, _menu_bar, _menu_view, _output_window, fake_workspace, _menu, _item = self._make_delegate(True)
        delegate.config.path = "/tmp/mini-gpt-helper-config.json"
        delegate.open_config()
        fake_workspace.openURL_.assert_called_once_with("url:/tmp/mini-gpt-helper-config.json")

    def test_process_clipboard_success_path_updates_state(self):
        delegate = types.SimpleNamespace(
            _in_flight=False,
            clipboard=Mock(),
            client=Mock(),
            _set_status=Mock(),
            menu_controller=Mock(),
            output_window=Mock(),
            _on_success=Mock(),
            _on_error=Mock(),
        )
        delegate.clipboard.read.return_value = "payload"
        delegate.client.complete.return_value = "done"

        class ImmediateThread:
            def __init__(self, target, args, daemon):
                self.target = target
                self.args = args
                self.daemon = daemon

            def start(self):
                self.target(*self.args)

        with patch.object(main.threading, "Thread", ImmediateThread):
            with patch.object(main.AppHelper, "callAfter", side_effect=lambda fn, *a: fn(*a)):
                main.AppDelegate._process_clipboard(delegate, "instr")

        delegate._set_status.assert_called_once_with(MenuStatus.PROCESSING)
        delegate.menu_controller.setBusy_.assert_called_once_with(True)
        delegate.menu_controller.setStatusText_.assert_called_once_with("Processing clipboard...")
        delegate.client.complete.assert_called_once_with("instr", "payload")
        delegate._on_success.assert_called_once_with("done")

    def test_process_clipboard_error_path_reports_failure(self):
        delegate = types.SimpleNamespace(
            _in_flight=False,
            clipboard=Mock(),
            client=Mock(),
            _set_status=Mock(),
            menu_controller=Mock(),
            output_window=Mock(),
            _on_success=Mock(),
            _on_error=Mock(),
        )
        delegate.clipboard.read.return_value = "payload"
        delegate.client.complete.side_effect = RuntimeError("boom")

        class ImmediateThread:
            def __init__(self, target, args, daemon):
                self.target = target
                self.args = args
                self.daemon = daemon

            def start(self):
                self.target(*self.args)

        with patch.object(main.threading, "Thread", ImmediateThread):
            with patch.object(main.AppHelper, "callAfter", side_effect=lambda fn, *a: fn(*a)):
                main.AppDelegate._process_clipboard(delegate, "")

        delegate._on_error.assert_called_once_with("boom")

    def test_on_success_updates_clipboard_and_ui(self):
        delegate = types.SimpleNamespace(
            clipboard=Mock(),
            state=types.SimpleNamespace(last_response=None, last_error="old", status=MenuStatus.IDLE),
            _in_flight=True,
            _set_status=Mock(),
            menu_controller=Mock(),
            output_window=Mock(),
        )

        main.AppDelegate._on_success(delegate, "done")

        delegate.clipboard.write_text.assert_called_once_with("done")
        self.assertEqual(delegate.state.last_response, "done")
        self.assertIsNone(delegate.state.last_error)
        self.assertFalse(delegate._in_flight)
        delegate._set_status.assert_called_once_with(MenuStatus.SUCCESS)
        delegate.menu_controller.setBusy_.assert_called_once_with(False)
        delegate.menu_controller.setOutput_.assert_called_once_with("done")
        delegate.menu_controller.setStatusText_.assert_called_once_with("Ready. Output available.")
        delegate.output_window.set_text.assert_called_once_with("done")

    def test_on_error_updates_state_and_ui(self):
        delegate = types.SimpleNamespace(
            state=types.SimpleNamespace(last_error=None, status=MenuStatus.IDLE),
            _in_flight=True,
            _set_status=Mock(),
            menu_controller=Mock(),
            output_window=Mock(),
        )

        main.AppDelegate._on_error(delegate, "boom")

        self.assertEqual(delegate.state.last_error, "boom")
        self.assertFalse(delegate._in_flight)
        delegate._set_status.assert_called_once_with(MenuStatus.ERROR)
        delegate.menu_controller.setBusy_.assert_called_once_with(False)
        delegate.menu_controller.setOutput_.assert_called_once_with("boom")
        delegate.menu_controller.setStatusText_.assert_called_once_with("boom")
        delegate.output_window.set_text.assert_called_once_with("Error: boom")

    def test_set_status_updates_state_and_menu(self):
        delegate = types.SimpleNamespace(
            state=types.SimpleNamespace(status=MenuStatus.IDLE),
            menu=Mock(),
        )

        main.AppDelegate._set_status(delegate, MenuStatus.SUCCESS)

        self.assertEqual(delegate.state.status, MenuStatus.SUCCESS)
        delegate.menu.set_status.assert_called_once_with(MenuStatus.SUCCESS)
