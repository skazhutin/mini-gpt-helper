from __future__ import annotations

import time

from AppKit import NSEvent, NSEventMaskKeyDown
from app_logging import log
from PyObjCTools import AppHelper
from Quartz import (
    CFMachPortCreateRunLoopSource,
    CFRunLoopAddSource,
    CFRunLoopGetCurrent,
    CFRunLoopRemoveSource,
    CGEventGetFlags,
    CGEventGetIntegerValueField,
    CGEventMaskBit,
    CGEventTapCreate,
    CGEventTapEnable,
    kCFRunLoopCommonModes,
    kCGEventFlagMaskControl,
    kCGEventFlagMaskShift,
    kCGEventKeyDown,
    kCGEventTapOptionListenOnly,
    kCGHeadInsertEventTap,
    kCGKeyboardEventKeycode,
    kCGSessionEventTap,
    NSEventModifierFlagControl,
    NSEventModifierFlagShift,
)

KEYCODE_MAP = {
    "space": 49,
    "a": 0,
    "s": 1,
    "d": 2,
    "f": 3,
    "h": 4,
    "g": 5,
    "z": 6,
    "x": 7,
    "c": 8,
    "v": 9,
    "b": 11,
    "q": 12,
    "w": 13,
    "e": 14,
    "r": 15,
    "y": 16,
    "t": 17,
    "1": 18,
    "2": 19,
    "3": 20,
    "4": 21,
    "6": 22,
    "5": 23,
    "=": 24,
    "9": 25,
    "7": 26,
    "-": 27,
    "8": 28,
    "0": 29,
}


class GlobalHotkey:
    def __init__(self, callback, key_name: str = "space"):
        self.callback = callback
        self.local_monitor = None
        self.event_tap = None
        self.run_loop_source = None
        self._last_fire_at = 0.0
        normalized = key_name.lower().strip()
        self.key_code = KEYCODE_MAP.get(normalized, KEYCODE_MAP["space"])
        log(f"GlobalHotkey initialized with key_name={normalized}, key_code={self.key_code}")

    def start(self):
        log("Starting hotkey monitors")

        def dispatch_callback(source: str):
            now = time.monotonic()
            if now - self._last_fire_at < 0.25:
                log(f"Ignoring duplicate hotkey event from {source}")
                return
            self._last_fire_at = now
            log(f"Dispatching hotkey callback from {source}")
            AppHelper.callAfter(self.callback)

        def should_handle(event) -> bool:
            if event is None:
                return False
            if event.isARepeat():
                return False
            if event.keyCode() == self.key_code:
                flags = event.modifierFlags()
                matched = bool((flags & NSEventModifierFlagControl) and (flags & NSEventModifierFlagShift))
                if matched:
                    log("Hotkey matched Control+Shift+configured key")
                return matched
            return False

        def tap_callback(_proxy, event_type, event, _refcon):
            if event_type != kCGEventKeyDown:
                return event

            key_code = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            flags = CGEventGetFlags(event)
            matched = (
                key_code == self.key_code
                and bool(flags & kCGEventFlagMaskControl)
                and bool(flags & kCGEventFlagMaskShift)
            )
            if matched:
                log("Quartz event tap received matching hotkey")
                dispatch_callback("event_tap")
            return event

        def local_handler(event):
            if should_handle(event):
                log("Local hotkey monitor received matching event")
                dispatch_callback("local_monitor")
            return event

        self.local_monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            NSEventMaskKeyDown, local_handler
        )
        self.event_tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,
            CGEventMaskBit(kCGEventKeyDown),
            tap_callback,
            None,
        )
        if self.event_tap is not None:
            self.run_loop_source = CFMachPortCreateRunLoopSource(None, self.event_tap, 0)
            CFRunLoopAddSource(CFRunLoopGetCurrent(), self.run_loop_source, kCFRunLoopCommonModes)
            CGEventTapEnable(self.event_tap, True)
            log("Quartz event tap registered")
        else:
            log("Quartz event tap could not be created; Accessibility permission is likely missing")

        log(
            "Hotkey monitors registered: "
            f"local={self.local_monitor is not None}, "
            f"tap={self.event_tap is not None}"
        )
        return self.event_tap is not None

    def stop(self):
        if self.event_tap:
            CGEventTapEnable(self.event_tap, False)
            if self.run_loop_source is not None:
                CFRunLoopRemoveSource(CFRunLoopGetCurrent(), self.run_loop_source, kCFRunLoopCommonModes)
                self.run_loop_source = None
            self.event_tap = None
            log("Quartz event tap disabled and run loop source removed")
        if self.local_monitor:
            NSEvent.removeMonitor_(self.local_monitor)
            self.local_monitor = None
            log("Local hotkey monitor removed")
