"""Tests for Phase 3.1 on-resolve ingest service."""

from unittest.mock import MagicMock, patch

import pytest

from src.integrations.jira.client import HistoricalTicket
from src.services.resolve_ingest_service import ResolveIngestService


def _resolved_ticket(**kwargs) -> HistoricalTicket:
    defaults = {
        "ticket_id": "PROJ-1",
        "title": "VPN issue",
        "description": "drops often",
        "resolution_text": "Renewed certificate",
        "team": "Network",
        "resolved_at": "2026-01-01T00:00:00Z",
        "status": "Done",
    }
    defaults.update(kwargs)
    return HistoricalTicket(**defaults)


@pytest.fixture
def mock_jira():
    return MagicMock()


@pytest.fixture
def service(mock_jira):
    return ResolveIngestService(jira_client=mock_jira)


def test_ingest_happy_path(service, mock_jira, monkeypatch):
    monkeypatch.setenv("INGEST_ON_RESOLVE_ENABLED", "true")
    monkeypatch.setenv("PINECONE_API_KEY", "pk-test")
    from src.config import get_settings

    get_settings.cache_clear()
    mock_jira.get_issue.return_value = _resolved_ticket()

    with patch("src.services.resolve_ingest_service.upsert_tickets_to_pinecone", return_value=1) as mock_upsert:
        result = service.ingest_resolved_ticket("PROJ-1")

    assert result.status == "ingested"
    assert result.ticket_id == "PROJ-1"
    mock_upsert.assert_called_once()


def test_ingest_skipped_when_disabled(service, monkeypatch):
    monkeypatch.setenv("INGEST_ON_RESOLVE_ENABLED", "false")
    from src.config import get_settings

    get_settings.cache_clear()
    result = service.ingest_resolved_ticket("PROJ-1")
    assert result.status == "skipped"
    assert "INGEST_ON_RESOLVE_ENABLED" in result.message


def test_ingest_skipped_non_resolved_status(service, mock_jira, monkeypatch):
    monkeypatch.setenv("INGEST_ON_RESOLVE_ENABLED", "true")
    monkeypatch.setenv("PINECONE_API_KEY", "pk-test")
    from src.config import get_settings

    get_settings.cache_clear()
    mock_jira.get_issue.return_value = _resolved_ticket(status="In Progress")

    result = service.ingest_resolved_ticket("PROJ-1")
    assert result.status == "skipped"
    assert "not resolved" in result.message


def test_ingest_skipped_no_resolution(service, mock_jira, monkeypatch):
    monkeypatch.setenv("INGEST_ON_RESOLVE_ENABLED", "true")
    monkeypatch.setenv("PINECONE_API_KEY", "pk-test")
    monkeypatch.setenv("INGEST_ON_RESOLVE_REQUIRE_RESOLUTION", "true")
    from src.config import get_settings

    get_settings.cache_clear()
    mock_jira.get_issue.return_value = _resolved_ticket(resolution_text="Done")

    result = service.ingest_resolved_ticket("PROJ-1")
    assert result.status == "skipped"
    assert "resolution" in result.message.lower()


def test_ingest_failed_jira_error(service, mock_jira, monkeypatch):
    monkeypatch.setenv("INGEST_ON_RESOLVE_ENABLED", "true")
    monkeypatch.setenv("PINECONE_API_KEY", "pk-test")
    from src.config import get_settings

    get_settings.cache_clear()
    mock_jira.get_issue.side_effect = RuntimeError("Jira down")

    result = service.ingest_resolved_ticket("PROJ-1")
    assert result.status == "failed"
    assert "Jira down" in result.message


def test_ingest_failed_pinecone_error(service, mock_jira, monkeypatch):
    monkeypatch.setenv("INGEST_ON_RESOLVE_ENABLED", "true")
    monkeypatch.setenv("PINECONE_API_KEY", "pk-test")
    from src.config import get_settings

    get_settings.cache_clear()
    mock_jira.get_issue.return_value = _resolved_ticket()

    with patch(
        "src.services.resolve_ingest_service.upsert_tickets_to_pinecone",
        side_effect=RuntimeError("Pinecone error"),
    ):
        result = service.ingest_resolved_ticket("PROJ-1")

    assert result.status == "failed"
    assert "Pinecone" in result.message


def test_dry_run(service, mock_jira, monkeypatch):
    monkeypatch.setenv("INGEST_ON_RESOLVE_ENABLED", "true")
    from src.config import get_settings

    get_settings.cache_clear()
    mock_jira.get_issue.return_value = _resolved_ticket()

    with patch("src.services.resolve_ingest_service.upsert_tickets_to_pinecone", return_value=0) as mock_upsert:
        result = service.ingest_resolved_ticket("PROJ-1", dry_run=True)

    assert result.status == "ingested"
    assert mock_upsert.call_args.kwargs["dry_run"] is True
