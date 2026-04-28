from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Optional

import certifi
from openai import OpenAI

from app_logging import log
from clipboard import ClipboardPayload
from config import Provider


class AIClipboardClient:
    def __init__(
        self,
        provider: Provider = "chatgpt",
        model: str = "gpt-4o-mini",
        openai_api_key: str = "",
        gemini_api_key: str = "",
    ) -> None:
        if provider not in {"chatgpt", "gemini"}:
            raise ValueError(f"Unsupported provider: {provider}")
        self.provider = provider
        self.openai_model = model
        self.openai_api_key = openai_api_key.strip()
        self.gemini_api_key = gemini_api_key.strip()
        self._openai_client: Optional[OpenAI] = None
        log(f"AIClipboardClient initialized with provider={provider}, model={model}")

    def complete(self, instruction: str, payload: ClipboardPayload) -> str:
        log(
            "Dispatching completion request: "
            f"provider={self.provider}, instruction_len={len(instruction)}, "
            f"text_present={bool(payload.text)}, image_present={bool(payload.image_b64)}"
        )
        if self.provider == "gemini":
            return self._complete_gemini(instruction, payload)
        return self._complete_chatgpt(instruction, payload)

    def _get_openai_client(self) -> OpenAI:
        if self._openai_client is None:
            log("Creating OpenAI client")
            if self.openai_api_key:
                self._openai_client = OpenAI(api_key=self.openai_api_key)
            else:
                self._openai_client = OpenAI()
        return self._openai_client

    def _complete_chatgpt(self, instruction: str, payload: ClipboardPayload) -> str:
        if not payload.text and not payload.image_b64:
            raise ValueError("Clipboard is empty or unsupported. Copy text or an image and try again.")

        content = []
        if instruction:
            content.append({"type": "input_text", "text": instruction})

        if payload.text:
            body = payload.text if not instruction else f"---\n\n{payload.text}"
            content.append({"type": "input_text", "text": body})

        if payload.image_b64:
            if instruction:
                content.append({"type": "input_text", "text": "---\n\nAnalyze this clipboard image:"})
            content.append(
                {
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{payload.image_b64}",
                }
            )

        log(
            "Sending ChatGPT request: "
            f"content_blocks={len(content)}, text_chars={len(payload.text or '')}, "
            f"image_b64_chars={len(payload.image_b64 or '')}"
        )
        response = self._get_openai_client().responses.create(
            model=self.openai_model,
            input=[{"role": "user", "content": content}],
        )
        text = response.output_text
        if not text:
            raise RuntimeError("Model response was empty.")
        log(f"ChatGPT response received ({len(text.strip())} chars)")
        return text.strip()

    def _complete_gemini(self, instruction: str, payload: ClipboardPayload) -> str:
        api_key = self.gemini_api_key or os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        if not payload.text and not payload.image_b64:
            raise ValueError("Clipboard is empty or unsupported. Copy text or an image and try again.")

        parts = []
        if instruction:
            parts.append({"text": instruction})

        if payload.text:
            parts.append({"text": payload.text if not instruction else f"---\n\n{payload.text}"})

        if payload.image_b64:
            if instruction:
                parts.append({"text": "---\n\nAnalyze this clipboard image:"})
            parts.append(
                {
                    "inlineData": {
                        "mimeType": "image/png",
                        "data": payload.image_b64,
                    }
                }
            )

        body = {"contents": [{"parts": parts}]}
        log(
            "Sending Gemini request: "
            f"parts={len(parts)}, text_chars={len(payload.text or '')}, "
            f"image_b64_chars={len(payload.image_b64 or '')}"
        )
        req = urllib.request.Request(
            url=(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-2.0-flash:generateContent?key={api_key}"
            ),
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(req, timeout=60, context=ssl_context) as resp:
                payload_json = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                details = exc.read().decode("utf-8", errors="ignore")
            finally:
                exc.close()
            log(f"Gemini API HTTP error: status={exc.code}, details={details[:400]}")
            raise RuntimeError(f"Gemini API error: HTTP {exc.code}: {details}") from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(exc):
                message = (
                    "Gemini API SSL verification failed. The app is using the certifi CA bundle, "
                    "but your Python/macOS trust chain still rejected the certificate. "
                    "If you are behind a proxy or custom antivirus TLS inspection, install that root "
                    "certificate or set SSL_CERT_FILE to a CA bundle that trusts it."
                )
                log(f"Gemini API SSL verification error: {exc}")
                raise RuntimeError(message) from exc
            log(f"Gemini API network error: {exc}")
            raise RuntimeError(f"Gemini API network error: {exc}") from exc

        candidates = payload_json.get("candidates", [])
        if not candidates:
            log(f"Gemini response missing candidates: keys={list(payload_json.keys())}")
            raise RuntimeError("Gemini response has no candidates.")
        out_parts = candidates[0].get("content", {}).get("parts", [])
        text_chunks = [p.get("text", "") for p in out_parts if p.get("text")]
        text = "\n".join(text_chunks).strip()
        if not text:
            raise RuntimeError("Gemini response was empty.")
        log(f"Gemini response received ({len(text)} chars)")
        return text
