"""HTTP clients for Ollama and OpenAI-compatible chat APIs."""

from __future__ import annotations

import logging
from typing import Optional

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Generate text via configured LLM provider (Ollama or OpenAI-compatible)."""

    def __init__(
        self,
        provider: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        settings = get_settings()
        self.provider = (provider or settings.LLM_PROVIDER).lower()
        self.timeout = timeout if timeout is not None else settings.OLLAMA_TIMEOUT_SECONDS
        self.model = model or (
            settings.OLLAMA_MODEL if self.provider == "ollama" else settings.OPENAI_MODEL
        )
        if self.provider == "ollama":
            self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        else:
            self.base_url = (base_url or settings.OPENAI_BASE_URL).rstrip("/")

    def chat(self, system: str, user: str) -> str:
        if self.provider == "ollama":
            return self._ollama_chat(system, user)
        if self.provider in ("openai", "openai_compatible"):
            return self._openai_chat(system, user)
        raise ValueError(f"Unsupported LLM_PROVIDER: {self.provider!r}")

    def _ollama_chat(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(f"{self.base_url}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()
        message = data.get("message") or {}
        content = message.get("content") or data.get("response") or ""
        if not str(content).strip():
            raise ValueError("Ollama returned empty response")
        return str(content).strip()

    def _openai_chat(self, system: str, user: str) -> str:
        settings = get_settings()
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        choices = data.get("choices") or []
        if not choices:
            raise ValueError("OpenAI-compatible API returned no choices")
        content = (choices[0].get("message") or {}).get("content") or ""
        if not str(content).strip():
            raise ValueError("OpenAI-compatible API returned empty content")
        return str(content).strip()
