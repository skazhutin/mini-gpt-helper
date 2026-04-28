from __future__ import annotations

from typing import Callable

from AppKit import (
    NSAppearance,
    NSAppearanceNameAqua,
    NSAppearanceNameDarkAqua,
    NSBezelStyleRounded,
    NSButton,
    NSColor,
    NSFont,
    NSMakeRect,
    NSRectFill,
    NSTextField,
    NSView,
    NSViewController,
)
from objc import super

from app_logging import log


class MenuRootView(NSView):
    def initWithFrame_(self, frame):
        self = super().initWithFrame_(frame)
        if self is None:
            return None
        self._background_color = NSColor.windowBackgroundColor()
        self.setWantsLayer_(True)
        return self

    def setBackgroundColor_(self, color):
        self._background_color = color
        if self.layer() is not None:
            self.layer().setBackgroundColor_(color.CGColor())
        self.setNeedsDisplay_(True)

    def isOpaque(self):
        return True

    def drawRect_(self, rect):
        self._background_color.setFill()
        NSRectFill(self.bounds())


class PopoverViewController(NSViewController):
    menu_size = (300.0, 100.0)

    def initWithCallbacks_(self, callbacks: dict[str, Callable[[], None] | Callable[[str], None]]):
        self = super().init()
        if self is None:
            return None
        self.callbacks = callbacks
        self.theme = "light"
        self.busy = False
        self.last_output = ""
        self.status_text = ""
        log("PopoverViewController initialized")
        return self

    def loadView(self):
        width, height = self.menu_size
        root = MenuRootView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))
        self.setView_(root)

        self.input_field = NSTextField.alloc().initWithFrame_(NSMakeRect(12, height - 38, width - 24, 24))
        self.input_field.setFrame_(NSMakeRect(12, height - 34, width - 64, 22))
        input_cell = self.input_field.cell()
        input_cell.setPlaceholderString_("Extra comments...")
        input_cell.setUsesSingleLineMode_(True)
        input_cell.setScrollable_(True)
        input_cell.setWraps_(False)
        root.addSubview_(self.input_field)

        self.config_button = self._make_button("Cfg", NSMakeRect(width - 44, height - 35, 32, 24), "configClicked:")
        self.config_button.setFont_(NSFont.systemFontOfSize_(11))
        root.addSubview_(self.config_button)

        self.status_label = NSTextField.alloc().initWithFrame_(NSMakeRect(12, height - 58, width - 24, 15))
        self.status_label.setBezeled_(False)
        self.status_label.setDrawsBackground_(False)
        self.status_label.setEditable_(False)
        self.status_label.setSelectable_(False)
        self.status_label.setFont_(NSFont.systemFontOfSize_(11))
        self.status_label.setStringValue_("")
        root.addSubview_(self.status_label)

        self.send_button = self._make_button("Send", NSMakeRect(12, 12, 64, 26), "sendClicked:")
        root.addSubview_(self.send_button)

        self.show_button = self._make_button("Show", NSMakeRect(86, 12, 64, 26), "showClicked:")
        self.show_button.setEnabled_(False)
        root.addSubview_(self.show_button)

        self.theme_button = self._make_button("Light", NSMakeRect(158, 12, 64, 26), "themeClicked:")
        root.addSubview_(self.theme_button)

        self.quit_button = self._make_button("Quit", NSMakeRect(222, 12, 64, 26), "quitClicked:")
        root.addSubview_(self.quit_button)

        log(f"Menu view loaded with size=({width}, {height})")
        self.applyTheme_(self.theme)
        self.setBusy_(self.busy)
        self.setStatusText_(self.status_text)
        self.setOutput_(self.last_output)

    def _make_button(self, title: str, frame, action: str):
        button = NSButton.alloc().initWithFrame_(frame)
        button.setBezelStyle_(NSBezelStyleRounded)
        button.setTitle_(title)
        button.setTarget_(self)
        button.setAction_(action)
        return button

    def _root_view(self):
        return self.view()

    def _ensure_view_loaded(self):
        if not hasattr(self, "send_button"):
            log("Menu view requested before load; loading lazily")
            self.loadView()

    def sendClicked_(self, _sender):
        log("Menu Send button pressed")
        callback = self.callbacks["send"]
        callback(str(self.input_field.stringValue()).strip())

    def showClicked_(self, _sender):
        log("Menu Show button pressed")
        self.callbacks["show"]()

    def configClicked_(self, _sender):
        log("Menu Config button pressed")
        self.callbacks["config"]()

    def themeClicked_(self, _sender):
        log("Menu Theme button pressed")
        self.callbacks["theme"]()

    def quitClicked_(self, _sender):
        log("Menu Quit button pressed")
        self.callbacks["quit"]()

    def applyTheme_(self, theme: str):
        self.theme = theme
        self._ensure_view_loaded()
        is_dark = theme == "dark"
        log(f"Applying menu theme={theme}")
        appearance_name = NSAppearanceNameDarkAqua if is_dark else NSAppearanceNameAqua
        appearance = NSAppearance.appearanceNamed_(appearance_name)
        root = self._root_view()
        root.setAppearance_(appearance)
        background_color = (
            NSColor.colorWithCalibratedWhite_alpha_(0.14, 1.0)
            if is_dark
            else NSColor.colorWithCalibratedWhite_alpha_(0.96, 1.0)
        )
        root.setBackgroundColor_(background_color)
        self.theme_button.setTitle_(f"{'Dark' if is_dark else 'Light'}")
        text_color = NSColor.secondaryLabelColor()
        self.status_label.setTextColor_(text_color)

    def setBusy_(self, busy: bool):
        self.busy = busy
        self._ensure_view_loaded()
        log(f"Menu busy state changed to {busy}")
        self.send_button.setEnabled_(not busy)
        self.send_button.setTitle_("Sending..." if busy else "Send")

    def setOutput_(self, text: str):
        self.last_output = text
        self._ensure_view_loaded()
        has_output = bool(text.strip())
        self.show_button.setEnabled_(has_output)
        log(f"Menu output updated; show_enabled={has_output}")

    def setStatusText_(self, text: str):
        self.status_text = text
        self._ensure_view_loaded()
        self.status_label.setStringValue_(text[:80])
        log(f"Menu status text updated to: {text[:80]}")
