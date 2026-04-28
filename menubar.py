from __future__ import annotations

from AppKit import NSStatusBar, NSVariableStatusItemLength

from app_logging import log
from state import MenuStatus


class MenuBarController:
    def __init__(self) -> None:
        self.item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        self.item.setHighlightMode_(True)
        self.item.setEnabled_(True)
        self.item.button().setEnabled_(True)
        self.item.button().setTitle_(MenuStatus.IDLE.value)
        log("MenuBarController initialized")

    def set_menu(self, menu) -> None:
        self.item.setMenu_(menu)
        log("Menu bar menu attached")

    def set_status(self, status: MenuStatus) -> None:
        self.item.button().setTitle_(status.value)
        log(f"Menu bar title updated to {status.value}")
