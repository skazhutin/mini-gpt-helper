from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Provider = Literal["chatgpt", "gemini"]
Theme = Literal["light", "dark"]


@dataclass
class AppConfig:
    provider: Provider = "chatgpt"
    theme: Theme = "light"
    hotkey_key: str = "space"

    @classmethod
    def load(cls, path: str = "config.json") -> "AppConfig":
        cfg = cls()
        file_path = Path(path)
        if file_path.exists():
            raw = json.loads(file_path.read_text(encoding="utf-8"))
            provider = str(raw.get("provider", cfg.provider)).lower()
            theme = str(raw.get("theme", cfg.theme)).lower()
            hotkey_key = str(raw.get("hotkey_key", cfg.hotkey_key)).lower().strip()
            if provider in {"chatgpt", "gemini"}:
                cfg.provider = provider
            if theme in {"light", "dark"}:
                cfg.theme = theme
            if hotkey_key:
                cfg.hotkey_key = hotkey_key

        env_provider = os.getenv("AI_PROVIDER", "").lower().strip()
        if env_provider in {"chatgpt", "gemini"}:
            cfg.provider = env_provider

        env_theme = os.getenv("APP_THEME", "").lower().strip()
        if env_theme in {"light", "dark"}:
            cfg.theme = env_theme

        env_hotkey_key = os.getenv("HOTKEY_KEY", "").lower().strip()
        if env_hotkey_key:
            cfg.hotkey_key = env_hotkey_key

        return cfg
