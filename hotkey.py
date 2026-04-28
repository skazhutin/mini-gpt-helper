from __future__ import annotations

from AppKit import NSEvent, NSEventMaskKeyDown
from Quartz import (
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
        self.monitor = None
        normalized = key_name.lower().strip()
        self.key_code = KEYCODE_MAP.get(normalized, KEYCODE_MAP["space"])

    def start(self):
        def handler(event):
            if event.keyCode() == self.key_code:
                flags = event.modifierFlags()
                # Mandatory combination: Control + Shift + selected key
                if (flags & NSEventModifierFlagControl) and (flags & NSEventModifierFlagShift):
                    self.callback()

        self.monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            NSEventMaskKeyDown, handler
        )

    def stop(self):
        if self.monitor:
            NSEvent.removeMonitor_(self.monitor)
            self.monitor = None
