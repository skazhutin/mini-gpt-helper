from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Optional

from AppKit import (
    NSPasteboard,
    NSPasteboardTypePNG,
    NSPasteboardTypeString,
    NSPasteboardTypeTIFF,
    NSBitmapImageRep,
    NSBitmapImageFileTypePNG,
    NSImage,
)

from app_logging import log


@dataclass
class ClipboardPayload:
    text: Optional[str] = None
    image_b64: Optional[str] = None


class ClipboardService:
    def __init__(self) -> None:
        self.pb = NSPasteboard.generalPasteboard()
        log("ClipboardService initialized")

    def read(self) -> ClipboardPayload:
        log("Reading clipboard payload")
        text = self.pb.stringForType_(NSPasteboardTypeString)
        if text:
            log(f"Clipboard contains text ({len(str(text))} chars)")
            return ClipboardPayload(text=str(text))

        png_data = self.pb.dataForType_(NSPasteboardTypePNG)
        if png_data is not None:
            log(f"Clipboard contains PNG image ({len(bytes(png_data))} bytes)")
            return ClipboardPayload(image_b64=base64.b64encode(bytes(png_data)).decode("utf-8"))

        tiff_data = self.pb.dataForType_(NSPasteboardTypeTIFF)
        if tiff_data is not None:
            log(f"Clipboard contains TIFF image ({len(bytes(tiff_data))} bytes)")
            image = NSImage.alloc().initWithData_(tiff_data)
            if image is not None:
                image_tiff_data = image.TIFFRepresentation()
                if image_tiff_data is not None:
                    rep = NSBitmapImageRep.imageRepWithData_(image_tiff_data)
                    if rep is not None:
                        png = rep.representationUsingType_properties_(NSBitmapImageFileTypePNG, None)
                        if png is not None:
                            log(f"Converted TIFF clipboard image to PNG ({len(bytes(png))} bytes)")
                            return ClipboardPayload(
                                image_b64=base64.b64encode(bytes(png)).decode("utf-8")
                            )

        log("Clipboard is empty or unsupported")
        return ClipboardPayload()

    def write_text(self, text: str) -> None:
        log(f"Writing result back to clipboard ({len(text)} chars)")
        self.pb.clearContents()
        self.pb.setString_forType_(text, NSPasteboardTypeString)
