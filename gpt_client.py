from __future__ import annotations

import base64
import importlib
import os
import ssl
from typing import Any, Optional

from openai import OpenAI

from app_logging import log
from clipboard import ClipboardPayload
from config import Provider


class AIClipboardClient:
    def __init__(
        self,
        provider: Provider = "chatgpt",
        openai_model: str = "gpt-4o-mini",
        openai_api_key: str = "",
        gemini_api_key: str = "",
        gemini_model: str = "gemini-2.5-flash",
        prompt: str = "",
    ) -> None:
        if provider not in {"chatgpt", "gemini"}:
            raise ValueError(f"Unsupported provider: {provider}")
        self.provider = provider
        self.openai_model = openai_model.strip() or "gpt-4o-mini"
        self.openai_api_key = openai_api_key.strip()
        self.gemini_api_key = gemini_api_key.strip()
        self._openai_client: Optional[OpenAI] = None
        self._gemini_client: Optional[Any] = None
        self.gemini_model = gemini_model.strip() or "gemini-2.5-flash"
        self.prompt = prompt.strip()
        log(
            "AIClipboardClient initialized with "
            f"provider={provider}, openai_model={self.openai_model}, gemini_model={self.gemini_model}"
        )

    def complete(self, instruction: str, payload: ClipboardPayload) -> str:
        effective_instruction = self._merge_instruction(instruction)
        log(
            "Dispatching completion request: "
            f"provider={self.provider}, instruction_len={len(effective_instruction)}, "
            f"text_present={bool(payload.text)}, image_present={bool(payload.image_b64)}"
        )
        if self.provider == "gemini":
            return self._complete_gemini(effective_instruction, payload)
        return self._complete_chatgpt(effective_instruction, payload)

    def _merge_instruction(self, instruction: str) -> str:
        segments = [segment.strip() for segment in (self.prompt, instruction) if segment and segment.strip()]
        return "\n\n".join(segments)

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
            content.append({"type": "input_text", "text": f"Instruction:\n{instruction}"})

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
        api_key = self._resolve_gemini_api_key()
        if not api_key:
            raise ValueError(
                "Gemini API key is not set. Configure `gemini_api_key` in `config.json`, "
                "`GEMINI_API_KEY`, or `GOOGLE_API_KEY`."
            )
        if not payload.text and not payload.image_b64:
            raise ValueError("Clipboard is empty or unsupported. Copy text or an image and try again.")

        _genai, types, errors = self._get_gemini_sdk()

        contents: list[Any] = []
        if instruction:
            contents.append(f"Instruction:\n{instruction}")

        if payload.text:
            contents.append(payload.text)

        if payload.image_b64:
            if not payload.text:
                contents.append("Describe this clipboard image.")
            contents.append(
                types.Part.from_bytes(
                    data=base64.b64decode(payload.image_b64),
                    mime_type="image/png",
                )
            )

        log(
            "Sending Gemini request: "
            f"model={self.gemini_model}, contents={len(contents)}, text_chars={len(payload.text or '')}, "
            f"image_b64_chars={len(payload.image_b64 or '')}"
        )

        try:
            response = self._get_gemini_client(api_key).models.generate_content(
                model=self.gemini_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
        except errors.APIError as exc:
            details = getattr(exc, "message", str(exc))
            code = getattr(exc, "code", "unknown")
            log(f"Gemini API error: status={code}, details={details[:400]}")
            raise RuntimeError(f"Gemini API error: HTTP {code}: {details}") from exc
        except Exception as exc:  # noqa: BLE001
            if self._is_ssl_verification_error(exc):
                message = (
                    "Gemini API SSL verification failed. If you are behind a proxy or TLS inspection, "
                    "install that root certificate or set `SSL_CERT_FILE` to a CA bundle that trusts it."
                )
                log(f"Gemini API SSL verification error: {exc}")
                raise RuntimeError(message) from exc
            if self._looks_like_network_error(exc):
                log(f"Gemini API network error: {exc}")
                raise RuntimeError(f"Gemini API network error: {exc}") from exc
            log(f"Gemini API request failed: {exc}")
            raise RuntimeError(f"Gemini API request failed: {exc}") from exc

        text = (getattr(response, "text", "") or "").strip()
        if not text:
            raise RuntimeError("Gemini response was empty.")
        log(f"Gemini response received ({len(text)} chars)")
        return text

    def _resolve_gemini_api_key(self) -> str:
        return (
            self.gemini_api_key
            or os.getenv("GEMINI_API_KEY", "").strip()
            or os.getenv("GOOGLE_API_KEY", "").strip()
        )

    def _get_gemini_sdk(self) -> tuple[Any, Any, Any]:
        try:
            genai = importlib.import_module("google.genai")
            types = importlib.import_module("google.genai.types")
            errors = importlib.import_module("google.genai.errors")
        except ImportError as exc:
            raise RuntimeError(
                "Gemini provider requires the `google-genai` package. "
                "Run `pip install -r requirements.txt` or `pip install -U google-genai`."
            ) from exc
        return genai, types, errors

    def _get_gemini_client(self, api_key: str) -> Any:
        if self._gemini_client is None:
            genai, _types, _errors = self._get_gemini_sdk()
            log("Creating Gemini client")
            self._gemini_client = genai.Client(api_key=api_key)
        return self._gemini_client

    @staticmethod
    def _is_ssl_verification_error(exc: BaseException) -> bool:
        pending = [exc]
        seen: set[int] = set()

        while pending:
            current = pending.pop()
            marker = id(current)
            if marker in seen:
                continue
            seen.add(marker)

            if isinstance(current, ssl.SSLCertVerificationError):
                return True

            text = str(current).lower()
            if "certificate verify failed" in text or "ssl_cert_file" in text:
                return True

            for attr in ("__cause__", "__context__", "reason"):
                nested = getattr(current, attr, None)
                if isinstance(nested, BaseException):
                    pending.append(nested)

        return False

    @staticmethod
    def _looks_like_network_error(exc: BaseException) -> bool:
        text = f"{type(exc).__name__}: {exc}".lower()
        markers = (
            "timeout",
            "timed out",
            "connection",
            "connect",
            "network",
            "dns",
            "offline",
            "proxy",
            "temporarily unavailable",
        )
        return isinstance(exc, OSError) or any(marker in text for marker in markers)
