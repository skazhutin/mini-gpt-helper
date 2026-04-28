from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from openai import OpenAI

from clipboard import ClipboardPayload
from config import Provider


class AIClipboardClient:
    def __init__(self, provider: Provider = "chatgpt", model: str = "gpt-4o-mini") -> None:
        self.provider = provider
        self.openai_model = model
        self.openai_client = OpenAI() if provider == "chatgpt" else None

    def complete(self, instruction: str, payload: ClipboardPayload) -> str:
        if self.provider == "gemini":
            return self._complete_gemini(instruction, payload)
        return self._complete_chatgpt(instruction, payload)

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

        response = self.openai_client.responses.create(
            model=self.openai_model,
            input=[{"role": "user", "content": content}],
        )
        text = response.output_text
        if not text:
            raise RuntimeError("Model response was empty.")
        return text.strip()

    def _complete_gemini(self, instruction: str, payload: ClipboardPayload) -> str:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
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
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload_json = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Gemini API error: HTTP {exc.code}: {details}") from exc

        candidates = payload_json.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini response has no candidates.")
        out_parts = candidates[0].get("content", {}).get("parts", [])
        text_chunks = [p.get("text", "") for p in out_parts if p.get("text")]
        text = "\n".join(text_chunks).strip()
        if not text:
            raise RuntimeError("Gemini response was empty.")
        return text
