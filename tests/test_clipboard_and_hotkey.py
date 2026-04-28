from __future__ import annotations

import base64
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import clipboard
import hotkey


class FakePasteboard:
    def __init__(self, text=None, png=None, tiff=None):
        self._text = text
        self._png = png
        self._tiff = tiff
        self.cleared = False
        self.written = None

    def stringForType_(self, _kind):
        return self._text

    def dataForType_(self, kind):
        if kind == clipboard.NSPasteboardTypePNG:
            return self._png
        if kind == clipboard.NSPasteboardTypeTIFF:
            return self._tiff
        return None

    def clearContents(self):
        self.cleared = True

    def setString_forType_(self, text, kind):
        self.written = (text, kind)


class ClipboardServiceTests(unittest.TestCase):
    def test_read_prefers_text(self):
        pasteboard = FakePasteboard(text="hello", png=b"png")

        fake_pasteboard_class = SimpleNamespace(generalPasteboard=lambda: pasteboard)
        with patch("clipboard.NSPasteboard", new=fake_pasteboard_class):
            service = clipboard.ClipboardService()
            payload = service.read()

        self.assertEqual(payload.text, "hello")
        self.assertIsNone(payload.image_b64)

    def test_read_png_returns_base64_payload(self):
        pasteboard = FakePasteboard(png=b"\x89PNG")

        fake_pasteboard_class = SimpleNamespace(generalPasteboard=lambda: pasteboard)
        with patch("clipboard.NSPasteboard", new=fake_pasteboard_class):
            service = clipboard.ClipboardService()
            payload = service.read()

        self.assertEqual(payload.image_b64, base64.b64encode(b"\x89PNG").decode("utf-8"))

    def test_read_empty_returns_empty_payload(self):
        pasteboard = FakePasteboard()

        fake_pasteboard_class = SimpleNamespace(generalPasteboard=lambda: pasteboard)
        with patch("clipboard.NSPasteboard", new=fake_pasteboard_class):
            service = clipboard.ClipboardService()
            payload = service.read()

        self.assertIsNone(payload.text)
        self.assertIsNone(payload.image_b64)

    def test_write_text_updates_pasteboard(self):
        pasteboard = FakePasteboard()

        fake_pasteboard_class = SimpleNamespace(generalPasteboard=lambda: pasteboard)
        with patch("clipboard.NSPasteboard", new=fake_pasteboard_class):
            service = clipboard.ClipboardService()
            service.write_text("done")

        self.assertTrue(pasteboard.cleared)
        self.assertEqual(pasteboard.written, ("done", clipboard.NSPasteboardTypeString))


class FakeEvent:
    def __init__(self, key_code, flags, repeat=False):
        self._key_code = key_code
        self._flags = flags
        self._repeat = repeat

    def isARepeat(self):
        return self._repeat

    def keyCode(self):
        return self._key_code

    def modifierFlags(self):
        return self._flags


class HotkeyTests(unittest.TestCase):
    def test_start_registers_monitors_and_fires_callback_for_matching_events(self):
        callbacks = []
        captured = {}

        class FakeNSEvent:
            @staticmethod
            def addLocalMonitorForEventsMatchingMask_handler_(_mask, handler):
                captured["local"] = handler
                return "local-monitor"

            @staticmethod
            def removeMonitor_(_monitor):
                return None

        fake_app_helper = SimpleNamespace(callAfter=lambda fn: fn())
        with patch("hotkey.NSEvent", new=FakeNSEvent):
            with patch("hotkey.AppHelper", new=fake_app_helper):
                with patch("hotkey.CGEventTapCreate", return_value="tap"):
                    with patch("hotkey.CFMachPortCreateRunLoopSource", return_value="source"):
                        with patch("hotkey.CFRunLoopAddSource"):
                            with patch("hotkey.CGEventTapEnable"):
                                hk = hotkey.GlobalHotkey(lambda: callbacks.append("called"), key_name="space")
                                started = hk.start()
                                matching_flags = hotkey.NSEventModifierFlagControl | hotkey.NSEventModifierFlagShift
                                event = FakeEvent(hotkey.KEYCODE_MAP["space"], matching_flags)
                                captured["local"](event)

        self.assertTrue(started)
        self.assertEqual(callbacks, ["called"])
        self.assertEqual(hk.local_monitor, "local-monitor")
        self.assertEqual(hk.event_tap, "tap")

    def test_start_ignores_non_matching_event(self):
        callbacks = []
        captured = {}

        class FakeNSEvent:
            @staticmethod
            def addLocalMonitorForEventsMatchingMask_handler_(_mask, handler):
                captured["local"] = handler
                return "local"

            @staticmethod
            def removeMonitor_(_monitor):
                return None

        fake_app_helper = SimpleNamespace(callAfter=lambda fn: fn())
        with patch("hotkey.NSEvent", new=FakeNSEvent):
            with patch("hotkey.AppHelper", new=fake_app_helper):
                with patch("hotkey.CGEventTapCreate", return_value="tap"):
                    with patch("hotkey.CFMachPortCreateRunLoopSource", return_value="source"):
                        with patch("hotkey.CFRunLoopAddSource"):
                            with patch("hotkey.CGEventTapEnable"):
                                hk = hotkey.GlobalHotkey(lambda: callbacks.append("called"), key_name="a")
                                hk.start()
                                event = FakeEvent(hotkey.KEYCODE_MAP["b"], 0)
                                captured["local"](event)

        self.assertEqual(callbacks, [])

    def test_stop_removes_registered_monitors(self):
        hk = hotkey.GlobalHotkey(lambda: None)
        hk.local_monitor = "local"
        hk.event_tap = "tap"
        removed = []
        enabled = []

        class FakeNSEvent:
            @staticmethod
            def removeMonitor_(monitor):
                removed.append(monitor)

        with patch("hotkey.NSEvent", new=FakeNSEvent):
            with patch("hotkey.CGEventTapEnable", side_effect=lambda tap, flag: enabled.append((tap, flag))):
                hk.stop()

        self.assertEqual(enabled, [("tap", False)])
        self.assertEqual(removed, ["local"])
        self.assertIsNone(hk.local_monitor)
        self.assertIsNone(hk.event_tap)
