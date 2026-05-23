"""Tests for BYOK LLM client."""

from unittest.mock import MagicMock, patch

import pytest


@patch("src.integrations.llm.client.httpx.Client")
def test_ollama_chat(mock_client_cls, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")
    from src.config import get_settings

    get_settings.cache_clear()

    mock_response = MagicMock()
    mock_response.json.return_value = {"message": {"content": "flowchart TD\n  A --> B"}}
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = mock_response
    mock_client_cls.return_value = mock_client

    from src.integrations.llm.client import LLMClient

    client = LLMClient()
    text = client.chat("system", "user")
    assert "flowchart TD" in text
    mock_client.post.assert_called_once()
    assert "/api/chat" in mock_client.post.call_args[0][0]
