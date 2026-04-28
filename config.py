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
    logging: int = 0
    openai_api_key: str = ""
    gemini_api_key: str = ""

    @classmethod
    def load(cls, path: str = "config.json") -> "AppConfig":
        cfg = cls()
        file_path = Path(path)
        if file_path.exists():
            raw = json.loads(file_path.read_text(encoding="utf-8"))
            provider = str(raw.get("provider", cfg.provider)).lower()
            theme = str(raw.get("theme", cfg.theme)).lower()
            hotkey_key = str(raw.get("hotkey_key", cfg.hotkey_key)).lower().strip()
            logging_value = raw.get("logging", cfg.logging)
            openai_api_key = str(raw.get("openai_api_key", cfg.openai_api_key)).strip()
            gemini_api_key = str(raw.get("gemini_api_key", cfg.gemini_api_key)).strip()
            if provider in {"chatgpt", "gemini"}:
                cfg.provider = provider
            if theme in {"light", "dark"}:
                cfg.theme = theme
            if hotkey_key:
                cfg.hotkey_key = hotkey_key
            cfg.logging = _normalize_logging_flag(logging_value, cfg.logging)
            cfg.openai_api_key = openai_api_key
            cfg.gemini_api_key = gemini_api_key

        env_provider = os.getenv("AI_PROVIDER", "").lower().strip()
        if env_provider in {"chatgpt", "gemini"}:
            cfg.provider = env_provider

        env_theme = os.getenv("APP_THEME", "").lower().strip()
        if env_theme in {"light", "dark"}:
            cfg.theme = env_theme

        env_hotkey_key = os.getenv("HOTKEY_KEY", "").lower().strip()
        if env_hotkey_key:
            cfg.hotkey_key = env_hotkey_key

        env_logging = os.getenv("APP_LOGGING", "").strip()
        if env_logging:
            cfg.logging = _normalize_logging_flag(env_logging, cfg.logging)

        env_openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if env_openai_api_key:
            cfg.openai_api_key = env_openai_api_key

        env_gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if env_gemini_api_key:
            cfg.gemini_api_key = env_gemini_api_key

        return cfg


def _normalize_logging_flag(value: object, default: int) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return 1 if value else 0

    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return 1
    if text in {"0", "false", "no", "off"}:
        return 0
    return default
