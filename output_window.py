from __future__ import annotations

from AppKit import (
    NSAppearance,
    NSAppearanceNameAqua,
    NSAppearanceNameDarkAqua,
    NSBackingStoreBuffered,
    NSFont,
    NSMakeRect,
    NSScrollView,
    NSTextView,
    NSViewController,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskResizable,
    NSWindowStyleMaskTitled,
)

from app_logging import log


class OutputWindowController:
    def __init__(self, theme: str = "light") -> None:
        self.theme = theme
        self.window = self._build_window()
        self.apply_theme(theme)
        log("OutputWindowController initialized")

    def _build_window(self):
        window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(240, 240, 560, 420),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskResizable,
            NSBackingStoreBuffered,
            False,
        )
        window.setTitle_("mini-gpt-helper Output")

        content = NSViewController.alloc().init()
        scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(0, 0, 560, 420))
        scroll.setHasVerticalScroller_(True)
        scroll.setAutohidesScrollers_(True)

        self.text_view = NSTextView.alloc().initWithFrame_(scroll.bounds())
        self.text_view.setEditable_(False)
        self.text_view.setFont_(NSFont.systemFontOfSize_(13))
        scroll.setDocumentView_(self.text_view)
        content.setView_(scroll)
        window.setContentViewController_(content)
        return window

    def apply_theme(self, theme: str):
        self.theme = theme
        appearance_name = NSAppearanceNameDarkAqua if theme == "dark" else NSAppearanceNameAqua
        self.window.setAppearance_(NSAppearance.appearanceNamed_(appearance_name))
        log(f"Applied output window theme={theme}")

    def set_text(self, text: str):
        self.text_view.setString_(text)
        log(f"Output window text updated ({len(text)} chars)")

    def show(self):
        self.window.makeKeyAndOrderFront_(None)
        log("Output window shown")
