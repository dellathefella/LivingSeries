"""OpenAI-compatible LLM client.

The gateway is model-agnostic: Strata (`/v1/chat/completions`), vLLM XPU, and MLX all speak the same
shape.  If the endpoint is unreachable the client returns a deterministic stub, so the API and tests
run without a model.  Set `LS_LLM_REQUIRED=1` to make an unreachable endpoint an error instead.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx

from .config import settings


@dataclass
class LlmReply:
    text: str
    model: str
    stub: bool = False


class LlmClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self.required = os.environ.get("LS_LLM_REQUIRED", "0") == "1"

    def chat(self, messages: list[dict[str, str]], *, max_tokens: int | None = None,
             temperature: float | None = None) -> LlmReply:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens or settings.llm_max_tokens,
            "temperature": settings.llm_temperature if temperature is None else temperature,
        }
        try:
            with httpx.Client(timeout=settings.llm_timeout_s) as client:
                r = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
                r.raise_for_status()
                data = r.json()
            text = data["choices"][0]["message"]["content"]
            return LlmReply(text=text.strip(), model=data.get("model", self.model))
        except Exception as exc:  # noqa: BLE001 - the stub is deliberate
            if self.required:
                raise RuntimeError(f"LLM endpoint unreachable: {self.base_url}: {exc}") from exc
            return LlmReply(text=self._stub(messages), model=self.model, stub=True)

    @staticmethod
    def _stub(messages: list[dict[str, str]]) -> str:
        """A deterministic reply that keeps the API testable without a model."""
        user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
        return (
            "I remember you. " + (user[:120] if user else "Tell me something I should keep.")
            + " — and I will keep it."
        )

    def health(self) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=5) as client:
                r = client.get(f"{self.base_url}/models", headers={"Authorization": f"Bearer {self.api_key}"})
                r.raise_for_status()
                return {"ok": True, "models": [m.get("id") for m in r.json().get("data", [])]}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc), "base_url": self.base_url}


def llm_json(client: LlmClient, messages: list[dict[str, str]], *, max_tokens: int = 1024) -> dict[str, Any]:
    """Ask the model for JSON and parse it; fall back to a minimal object on failure."""
    reply = client.chat(messages, max_tokens=max_tokens, temperature=0.4)
    text = reply.text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": reply.text, "stub": reply.stub}
