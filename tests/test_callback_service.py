"""Tests for outbound routing callback."""

from unittest.mock import MagicMock, patch

from src.api.v1.schemas import TicketStatusResponse
from src.config import get_settings
from src.services.callback_service import RoutingCallbackService


def _sample_result() -> TicketStatusResponse:
    return TicketStatusResponse(
        ticket_id="T-1",
        assigned_team="DevOps",
        confidence_score=0.9,
        requires_hitl=False,
        status="completed",
    )


def test_notify_skips_when_callback_url_empty(monkeypatch):
    monkeypatch.setenv("TRIAGE_CALLBACK_URL", "")
    get_settings.cache_clear()
    with patch("httpx.Client") as client_cls:
        RoutingCallbackService().notify_triage_result(_sample_result())
        client_cls.assert_not_called()


def test_notify_posts_json_when_url_set(monkeypatch):
    monkeypatch.setenv("TRIAGE_CALLBACK_URL", "http://example.invalid/triage-done")
    monkeypatch.setenv("TRIAGE_CALLBACK_API_KEY", "secret-cb")
    monkeypatch.setenv("TRIAGE_CALLBACK_RETRIES", "0")
    get_settings.cache_clear()

    inner = MagicMock()
    ok = MagicMock()
    ok.raise_for_status = MagicMock()
    inner.post.return_value = ok
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = inner
    mock_cm.__exit__.return_value = False

    with patch("src.services.callback_service.httpx.Client", return_value=mock_cm):
        RoutingCallbackService().notify_triage_result(_sample_result())

    inner.post.assert_called_once()
    call_kw = inner.post.call_args
    assert call_kw[0][0] == "http://example.invalid/triage-done"
    assert call_kw[1]["json"]["ticket_id"] == "T-1"
    assert call_kw[1]["json"]["status"] == "completed"
    assert call_kw[1]["headers"]["X-API-Key"] == "secret-cb"
