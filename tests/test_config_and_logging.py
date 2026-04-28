from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

import app_logging
from config import AppConfig, _normalize_logging_flag, resolve_config_path
from state import AppState


class ConfigTests(unittest.TestCase):
    def test_load_defaults_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "missing.json")
            cfg = AppConfig.load(path)

        self.assertEqual(cfg.provider, "chatgpt")
        self.assertEqual(cfg.theme, "light")
        self.assertEqual(cfg.hotkey_key, "space")
        self.assertEqual(cfg.logging, 0)

    def test_load_reads_file_and_env_overrides(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "provider": "gemini",
                        "theme": "dark",
                        "hotkey_key": "A",
                        "logging": "1",
                        "prompt": "file-prompt",
                        "openai_model": "file-openai-model",
                        "gemini_model": "file-gemini-model",
                        "openai_api_key": "file-openai",
                        "gemini_api_key": "file-gemini",
                    },
                    fh,
                )

            with patch.dict(
                os.environ,
                {
                    "AI_PROVIDER": "chatgpt",
                    "APP_THEME": "light",
                    "HOTKEY_KEY": "b",
                    "APP_LOGGING": "0",
                    "APP_PROMPT": "env-prompt",
                    "OPENAI_MODEL": "env-openai-model",
                    "GEMINI_MODEL": "env-gemini-model",
                    "OPENAI_API_KEY": "env-openai",
                    "GEMINI_API_KEY": "env-gemini",
                },
                clear=False,
            ):
                cfg = AppConfig.load(path)

        self.assertEqual(cfg.provider, "chatgpt")
        self.assertEqual(cfg.theme, "light")
        self.assertEqual(cfg.hotkey_key, "b")
        self.assertEqual(cfg.logging, 0)
        self.assertEqual(cfg.prompt, "env-prompt")
        self.assertEqual(cfg.openai_model, "env-openai-model")
        self.assertEqual(cfg.gemini_model, "env-gemini-model")
        self.assertEqual(cfg.openai_api_key, "env-openai")
        self.assertEqual(cfg.gemini_api_key, "env-gemini")
        self.assertEqual(cfg.path, path)

    def test_invalid_file_values_fall_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "provider": "unknown",
                        "theme": "blue",
                        "hotkey_key": "",
                        "logging": "invalid",
                    },
                    fh,
                )

            cfg = AppConfig.load(path)

        self.assertEqual(cfg.provider, "chatgpt")
        self.assertEqual(cfg.theme, "light")
        self.assertEqual(cfg.hotkey_key, "space")
        self.assertEqual(cfg.logging, 0)

    def test_normalize_logging_flag_accepts_common_forms(self):
        self.assertEqual(_normalize_logging_flag(True, 0), 1)
        self.assertEqual(_normalize_logging_flag(False, 1), 0)
        self.assertEqual(_normalize_logging_flag(1, 0), 1)
        self.assertEqual(_normalize_logging_flag(0, 1), 0)
        self.assertEqual(_normalize_logging_flag("yes", 0), 1)
        self.assertEqual(_normalize_logging_flag("off", 1), 0)
        self.assertEqual(_normalize_logging_flag("bogus", 1), 1)

    def test_load_uses_app_config_path_env(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "custom.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"theme": "dark"}, fh)

            with patch.dict(os.environ, {"APP_CONFIG_PATH": path}, clear=False):
                cfg = AppConfig.load()

        self.assertEqual(cfg.theme, "dark")
        self.assertEqual(cfg.path, path)

    def test_save_writes_current_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "config.json")
            cfg = AppConfig(
                provider="gemini",
                theme="dark",
                hotkey_key="h",
                logging=1,
                prompt="base prompt",
                openai_model="gpt-test",
                gemini_model="gemini-test",
                openai_api_key="openai",
                gemini_api_key="gemini",
                path=path,
            )

            cfg.save()

            with open(path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)

        self.assertEqual(
            payload,
            {
                "provider": "gemini",
                "theme": "dark",
                "hotkey_key": "h",
                "logging": 1,
                "prompt": "base prompt",
                "openai_model": "gpt-test",
                "gemini_model": "gemini-test",
                "openai_api_key": "openai",
                "gemini_api_key": "gemini",
            },
        )

    def test_resolve_config_path_expands_home(self):
        with patch.dict(os.environ, {"APP_CONFIG_PATH": "~/mini-gpt-helper.json"}, clear=False):
            resolved = resolve_config_path()

        self.assertTrue(str(resolved).endswith("mini-gpt-helper.json"))


class AppLoggingTests(unittest.TestCase):
    def tearDown(self):
        app_logging.set_enabled(False)

    def test_log_is_silent_when_disabled(self):
        buffer = io.StringIO()
        app_logging.set_enabled(False)

        with redirect_stdout(buffer):
            app_logging.log("hello")

        self.assertEqual(buffer.getvalue(), "")

    def test_log_writes_prefixed_message_when_enabled(self):
        buffer = io.StringIO()
        app_logging.set_enabled(True)

        with redirect_stderr(buffer):
            app_logging.log("hello")

        output = buffer.getvalue()
        self.assertIn("mini-gpt-helper", output)
        self.assertIn("hello", output)


class StateTests(unittest.TestCase):
    def test_has_result_reflects_last_response(self):
        state = AppState()
        self.assertFalse(state.has_result)

        state.last_response = "done"
        self.assertTrue(state.has_result)
