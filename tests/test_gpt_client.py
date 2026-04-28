from __future__ import annotations

import base64
import os
import ssl
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from clipboard import ClipboardPayload
from gpt_client import AIClipboardClient


class FakeThinkingConfig:
    def __init__(self, thinking_budget: int):
        self.thinking_budget = thinking_budget


class FakeGenerateContentConfig:
    def __init__(self, system_instruction=None, thinking_config=None):
        self.system_instruction = system_instruction
        self.thinking_config = thinking_config


class FakeAPIError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class FakeGeminiClient:
    instances = []
    response_text = "hello\nworld"
    side_effect: Exception | None = None

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.models = SimpleNamespace(generate_content=Mock(side_effect=self._generate_content))
        self.__class__.instances.append(self)

    def _generate_content(self, *args, **kwargs):
        if self.__class__.side_effect is not None:
            raise self.__class__.side_effect
        return SimpleNamespace(text=self.__class__.response_text)

    @classmethod
    def reset(cls):
        cls.instances = []
        cls.response_text = "hello\nworld"
        cls.side_effect = None


def make_fake_gemini_sdk():
    FakeGeminiClient.reset()
    fake_part = SimpleNamespace(
        from_bytes=Mock(side_effect=lambda data, mime_type: {"data": data, "mime_type": mime_type})
    )
    fake_types = SimpleNamespace(
        Part=fake_part,
        GenerateContentConfig=FakeGenerateContentConfig,
        ThinkingConfig=FakeThinkingConfig,
    )
    fake_genai = SimpleNamespace(Client=FakeGeminiClient)
    fake_errors = SimpleNamespace(APIError=FakeAPIError)
    return fake_genai, fake_types, fake_errors


class GPTClientTests(unittest.TestCase):
    def test_invalid_provider_raises(self):
        with self.assertRaises(ValueError):
            AIClipboardClient(provider="nope")  # type: ignore[arg-type]

    def test_chatgpt_rejects_empty_clipboard(self):
        client = AIClipboardClient(provider="chatgpt")

        with self.assertRaises(ValueError):
            client.complete("", ClipboardPayload())

    def test_chatgpt_sends_text_and_image_payload(self):
        client = AIClipboardClient(provider="chatgpt", openai_model="gpt-test")
        response_client = SimpleNamespace(
            responses=SimpleNamespace(create=Mock(return_value=SimpleNamespace(output_text="  result  ")))
        )
        payload = ClipboardPayload(text="clipboard", image_b64="abc123")

        with patch.object(client, "_get_openai_client", return_value=response_client):
            result = client.complete("summarize", payload)

        self.assertEqual(result, "result")
        create_call = response_client.responses.create.call_args.kwargs
        self.assertEqual(create_call["model"], "gpt-test")
        content = create_call["input"][0]["content"]
        self.assertEqual(content[0]["text"], "Instruction:\nsummarize")
        self.assertEqual(content[1]["text"], "---\n\nclipboard")
        self.assertEqual(content[2]["text"], "---\n\nAnalyze this clipboard image:")
        self.assertEqual(content[3]["image_url"], "data:image/png;base64,abc123")

    def test_prompt_is_merged_with_runtime_instruction(self):
        client = AIClipboardClient(provider="chatgpt", prompt="base prompt")
        response_client = SimpleNamespace(
            responses=SimpleNamespace(create=Mock(return_value=SimpleNamespace(output_text="  result  ")))
        )

        with patch.object(client, "_get_openai_client", return_value=response_client):
            client.complete("extra", ClipboardPayload(text="clipboard"))

        content = response_client.responses.create.call_args.kwargs["input"][0]["content"]
        self.assertEqual(content[0]["text"], "Instruction:\nbase prompt\n\nextra")

    def test_chatgpt_raises_on_empty_response_text(self):
        client = AIClipboardClient(provider="chatgpt")
        response_client = SimpleNamespace(
            responses=SimpleNamespace(create=Mock(return_value=SimpleNamespace(output_text="")))
        )

        with patch.object(client, "_get_openai_client", return_value=response_client):
            with self.assertRaises(RuntimeError):
                client.complete("", ClipboardPayload(text="hello"))

    def test_gemini_requires_api_key(self):
        client = AIClipboardClient(provider="gemini")

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                client.complete("", ClipboardPayload(text="hello"))

    def test_gemini_successfully_parses_response(self):
        client = AIClipboardClient(provider="gemini", prompt="base prompt")
        fake_genai, fake_types, fake_errors = make_fake_gemini_sdk()
        image_b64 = base64.b64encode(b"png-bytes").decode("ascii")

        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret"}, clear=True):
            with patch.object(client, "_get_gemini_sdk", return_value=(fake_genai, fake_types, fake_errors)):
                result = client.complete("instr", ClipboardPayload(text="clipboard", image_b64=image_b64))

        self.assertEqual(result, "hello\nworld")
        self.assertEqual(len(FakeGeminiClient.instances), 1)
        self.assertEqual(FakeGeminiClient.instances[0].api_key, "secret")

        create_call = FakeGeminiClient.instances[0].models.generate_content.call_args.kwargs
        self.assertEqual(create_call["model"], "gemini-2.5-flash")
        self.assertEqual(create_call["contents"][0], "Instruction:\nbase prompt\n\ninstr")
        self.assertEqual(create_call["contents"][1], "clipboard")
        self.assertEqual(create_call["contents"][2]["data"], b"png-bytes")
        self.assertEqual(create_call["contents"][2]["mime_type"], "image/png")
        self.assertEqual(create_call["config"].thinking_config.thinking_budget, 0)

    def test_gemini_http_error_is_wrapped(self):
        client = AIClipboardClient(provider="gemini")
        fake_genai, fake_types, fake_errors = make_fake_gemini_sdk()
        FakeGeminiClient.side_effect = FakeAPIError(429, "rate limit")

        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret"}, clear=True):
            with patch.object(client, "_get_gemini_sdk", return_value=(fake_genai, fake_types, fake_errors)):
                with self.assertRaises(RuntimeError) as ctx:
                    client.complete("", ClipboardPayload(text="hello"))

        self.assertIn("HTTP 429", str(ctx.exception))

    def test_gemini_network_error_is_wrapped(self):
        client = AIClipboardClient(provider="gemini")
        fake_genai, fake_types, fake_errors = make_fake_gemini_sdk()
        FakeGeminiClient.side_effect = OSError("offline")

        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret"}, clear=True):
            with patch.object(client, "_get_gemini_sdk", return_value=(fake_genai, fake_types, fake_errors)):
                with self.assertRaises(RuntimeError) as ctx:
                    client.complete("", ClipboardPayload(text="hello"))

        self.assertIn("network error", str(ctx.exception).lower())

    def test_gemini_ssl_error_has_actionable_message(self):
        client = AIClipboardClient(provider="gemini")
        fake_genai, fake_types, fake_errors = make_fake_gemini_sdk()
        FakeGeminiClient.side_effect = ssl.SSLCertVerificationError("certificate verify failed")

        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret"}, clear=True):
            with patch.object(client, "_get_gemini_sdk", return_value=(fake_genai, fake_types, fake_errors)):
                with self.assertRaises(RuntimeError) as ctx:
                    client.complete("", ClipboardPayload(text="hello"))

        self.assertIn("ssl verification failed", str(ctx.exception).lower())
        self.assertIn("ssl_cert_file", str(ctx.exception).lower())

    def test_gemini_sdk_missing_has_actionable_message(self):
        client = AIClipboardClient(provider="gemini")

        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret"}, clear=True):
            with patch.object(client, "_get_gemini_sdk", side_effect=RuntimeError("install google-genai")):
                with self.assertRaises(RuntimeError) as ctx:
                    client.complete("", ClipboardPayload(text="hello"))

        self.assertIn("install google-genai", str(ctx.exception).lower())
