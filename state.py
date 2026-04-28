from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MenuStatus(str, Enum):
    IDLE = "●"
    PROCESSING = "…"
    SUCCESS = "✓"
    ERROR = "!"


@dataclass
class AppState:
    status: MenuStatus = MenuStatus.IDLE
    last_response: Optional[str] = None
    last_error: Optional[str] = None

    @property
    def has_result(self) -> bool:
        return bool(self.last_response)
