from __future__ import annotations

from typing import Callable

from AppKit import (
    NSAppearance,
    NSAppearanceNameAqua,
    NSAppearanceNameDarkAqua,
    NSBezelStyleRounded,
    NSButton,
    NSFont,
    NSMakeRect,
    NSScrollView,
    NSViewController,
    NSTextField,
    NSTextView,
)


class PopoverViewController(NSViewController):
    compact_size = (300.0, 120.0)
    expanded_size = (300.0, 300.0)

    def initWithCallbacks_(self, send_callback: Callable[[str], None], theme_callback: Callable[[], None]):
        self = super().init()
        if self is None:
            return None
        self.send_callback = send_callback
        self.theme_callback = theme_callback
        self.last_output = ""
        self.expanded = False
        self.theme = "light"
        return self

    def loadView(self):
        width, height = self.compact_size
        self.view = self._build_root_view(width, height)

    def _build_root_view(self, width: float, height: float):
        from AppKit import NSView

        root = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))

        self.input_field = NSTextField.alloc().initWithFrame_(NSMakeRect(12, height - 42, width - 56, 24))
        self.input_field.cell().setPlaceholderString_("Optional instruction...")
        root.addSubview_(self.input_field)

        self.theme_button = NSButton.alloc().initWithFrame_(NSMakeRect(width - 36, height - 44, 24, 24))
        self.theme_button.setBezelStyle_(NSBezelStyleRounded)
        self.theme_button.setTitle_("☀︎")
        self.theme_button.setTarget_(self)
        self.theme_button.setAction_("themeClicked:")
        root.addSubview_(self.theme_button)

        self.send_button = NSButton.alloc().initWithFrame_(NSMakeRect(12, height - 78, 90, 28))
        self.send_button.setBezelStyle_(NSBezelStyleRounded)
        self.send_button.setTitle_("Send")
        self.send_button.setTarget_(self)
        self.send_button.setAction_("sendClicked:")
        root.addSubview_(self.send_button)

        self.toggle_button = NSButton.alloc().initWithFrame_(NSMakeRect(112, height - 78, 110, 28))
        self.toggle_button.setBezelStyle_(NSBezelStyleRounded)
        self.toggle_button.setTitle_("Show Output")
        self.toggle_button.setEnabled_(False)
        self.toggle_button.setTarget_(self)
        self.toggle_button.setAction_("toggleOutput:")
        root.addSubview_(self.toggle_button)

        self.scroll_view = NSScrollView.alloc().initWithFrame_(NSMakeRect(12, 12, width - 24, height - 98))
        self.scroll_view.setHasVerticalScroller_(True)
        self.scroll_view.setAutohidesScrollers_(True)

        self.output_view = NSTextView.alloc().initWithFrame_(self.scroll_view.bounds())
        self.output_view.setEditable_(False)
        self.output_view.setFont_(NSFont.systemFontOfSize_(12))
        self.scroll_view.setDocumentView_(self.output_view)
        self.scroll_view.setHidden_(True)
        root.addSubview_(self.scroll_view)
        return root

    def sendClicked_(self, _sender):
        self.send_callback(str(self.input_field.stringValue()).strip())

    def themeClicked_(self, _sender):
        self.theme_callback()

    def toggleOutput_(self, _sender):
        self.setExpanded_(not self.expanded)

    def setExpanded_(self, expanded: bool):
        self.expanded = expanded
        width, height = self.expanded_size if expanded else self.compact_size
        self.view.setFrameSize_((width, height))

        self.input_field.setFrame_(NSMakeRect(12, height - 42, width - 56, 24))
        self.theme_button.setFrame_(NSMakeRect(width - 36, height - 44, 24, 24))
        self.send_button.setFrame_(NSMakeRect(12, height - 78, 90, 28))
        self.toggle_button.setFrame_(NSMakeRect(112, height - 78, 110, 28))

        if expanded:
            self.toggle_button.setTitle_("Hide Output")
            self.scroll_view.setFrame_(NSMakeRect(12, 12, width - 24, height - 98))
            self.scroll_view.setHidden_(False)
        else:
            self.toggle_button.setTitle_("Show Output")
            self.scroll_view.setHidden_(True)

        if self.view.window() is not None:
            self.view.window().setContentSize_((width, height))

    def applyTheme_(self, theme: str):
        self.theme = theme
        is_dark = theme == "dark"
        self.theme_button.setTitle_("☾" if is_dark else "☀︎")
        appearance_name = NSAppearanceNameDarkAqua if is_dark else NSAppearanceNameAqua
        appearance = NSAppearance.appearanceNamed_(appearance_name)
        self.view.setAppearance_(appearance)

    def setOutput_(self, text: str):
        self.last_output = text
        self.output_view.setString_(text)
        self.toggle_button.setEnabled_(True)
        self.setExpanded_(True)

    def setBusy_(self, busy: bool):
        self.send_button.setEnabled_(not busy)
        self.send_button.setTitle_("Sending..." if busy else "Send")
