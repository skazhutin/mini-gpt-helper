from __future__ import annotations

import io
import json
import os
import ssl
import unittest
import urllib.error
from types import SimpleNamespace
from unittest.mock import Mock, patch

from clipboard import ClipboardPayload
from openai_client import AIClipboardClient


class FakeHTTPResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class OpenAIClientTests(unittest.TestCase):
    def test_invalid_provider_raises(self):
        with self.assertRaises(ValueError):
            AIClipboardClient(provider="nope")  # type: ignore[arg-type]

    def test_chatgpt_rejects_empty_clipboard(self):
        client = AIClipboardClient(provider="chatgpt")

        with self.assertRaises(ValueError):
            client.complete("", ClipboardPayload())

    def test_chatgpt_sends_text_and_image_payload(self):
        client = AIClipboardClient(provider="chatgpt", model="gpt-test")
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
        self.assertEqual(content[0]["text"], "summarize")
        self.assertEqual(content[1]["text"], "---\n\nclipboard")
        self.assertEqual(content[2]["text"], "---\n\nAnalyze this clipboard image:")
        self.assertEqual(content[3]["image_url"], "data:image/png;base64,abc123")

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
        client = AIClipboardClient(provider="gemini")
        captured = {}

        def fake_urlopen(request, timeout, context=None):
            captured["url"] = request.full_url
            captured["timeout"] = timeout
            captured["context"] = context
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeHTTPResponse(
                {
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {"text": "hello"},
                                    {"text": "world"},
                                ]
                            }
                        }
                    ]
                }
            )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret"}, clear=True):
            with patch("openai_client.urllib.request.urlopen", side_effect=fake_urlopen):
                result = client.complete("instr", ClipboardPayload(text="clipboard"))

        self.assertEqual(result, "hello\nworld")
        self.assertIn("secret", captured["url"])
        self.assertEqual(captured["timeout"], 60)
        self.assertIsNotNone(captured["context"])
        parts = captured["body"]["contents"][0]["parts"]
        self.assertEqual(parts[0]["text"], "instr")
        self.assertEqual(parts[1]["text"], "---\n\nclipboard")

    def test_gemini_http_error_is_wrapped(self):
        client = AIClipboardClient(provider="gemini")

        error = urllib.error.HTTPError(
            url="https://example.com",
            code=429,
            msg="Too Many Requests",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"rate limit"}'),
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret"}, clear=True):
            with patch("openai_client.urllib.request.urlopen", side_effect=error):
                with self.assertRaises(RuntimeError) as ctx:
                    client.complete("", ClipboardPayload(text="hello"))
        error.close()

        self.assertIn("HTTP 429", str(ctx.exception))

    def test_gemini_network_error_is_wrapped(self):
        client = AIClipboardClient(provider="gemini")

        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret"}, clear=True):
            with patch(
                "openai_client.urllib.request.urlopen",
                side_effect=urllib.error.URLError("offline"),
            ):
                with self.assertRaises(RuntimeError) as ctx:
                    client.complete("", ClipboardPayload(text="hello"))

        self.assertIn("network error", str(ctx.exception).lower())

    def test_gemini_ssl_error_has_actionable_message(self):
        client = AIClipboardClient(provider="gemini")
        ssl_error = urllib.error.URLError(ssl.SSLCertVerificationError("certificate verify failed"))

        with patch.dict(os.environ, {"GEMINI_API_KEY": "secret"}, clear=True):
            with patch("openai_client.urllib.request.urlopen", side_effect=ssl_error):
                with self.assertRaises(RuntimeError) as ctx:
                    client.complete("", ClipboardPayload(text="hello"))

        self.assertIn("ssl verification failed", str(ctx.exception).lower())
        self.assertIn("ssl_cert_file", str(ctx.exception).lower())
