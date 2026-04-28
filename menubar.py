from __future__ import annotations

from AppKit import NSStatusBar, NSVariableStatusItemLength

from state import MenuStatus


class MenuBarController:
    def __init__(self, target, action: str) -> None:
        self.item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        self.item.button().setTitle_(MenuStatus.IDLE.value)
        self.item.button().setTarget_(target)
        self.item.button().setAction_(action)

    def set_status(self, status: MenuStatus) -> None:
        self.item.button().setTitle_(status.value)
