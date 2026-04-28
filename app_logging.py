from __future__ import annotations

import sys
from datetime import datetime

_enabled = False


def set_enabled(enabled: bool) -> None:
    global _enabled
    _enabled = bool(enabled)


def is_enabled() -> bool:
    return _enabled


def log(message: str) -> None:
    if not _enabled:
        return
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[mini-gpt-helper {timestamp}] {message}", file=sys.stderr, flush=True)
