"""Tests for Jira client parsing and Phase 3.1 helpers."""

from unittest.mock import MagicMock, patch

import pytest

from src.integrations.jira.client import JiraClient, RESOLVED_STATUSES


def _sample_issue(status_name: str = "Done") -> dict:
    return {
        "key": "PROJ-42",
        "fields": {
            "summary": "VPN drops",
            "description": "User loses connection",
            "resolutiondate": "2026-01-10T12:00:00.000+0000",
            "components": [{"name": "Network"}],
            "comment": {
                "comments": [
                    {"body": "Investigating"},
                    {"body": "Resolved by renewing certificate"},
                ]
            },
            "status": {"name": status_name},
        },
    }


def test_parse_issue_extracts_fields():
    client = JiraClient.__new__(JiraClient)
    ticket = client._parse_issue(_sample_issue())
    assert ticket is not None
    assert ticket.ticket_id == "PROJ-42"
    assert ticket.title == "VPN drops"
    assert "certificate" in ticket.resolution_text.lower()
    assert ticket.team == "Network"
    assert ticket.status == "Done"


def test_is_resolved_status():
    client = JiraClient.__new__(JiraClient)
    assert client.is_resolved_status("Done") is True
    assert client.is_resolved_status("In Progress") is False


def test_recently_resolved_jql(monkeypatch):
    monkeypatch.setenv("JIRA_PROJECT_KEY", "PROJ")
    from src.config import get_settings

    get_settings.cache_clear()
    client = JiraClient.__new__(JiraClient)
    jql = client.recently_resolved_jql(15)
    assert 'project = "PROJ"' in jql
    assert "resolved >= -15m" in jql
    for status in RESOLVED_STATUSES:
        assert status in jql


@patch("src.integrations.jira.client.httpx.Client")
def test_get_issue(mock_client_cls, monkeypatch):
    monkeypatch.setenv("JIRA_BASE_URL", "https://test.atlassian.net")
    monkeypatch.setenv("JIRA_EMAIL", "a@b.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "token")
    from src.config import get_settings

    get_settings.cache_clear()

    mock_response = MagicMock()
    mock_response.json.return_value = _sample_issue()
    mock_response.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_response
    mock_client_cls.return_value = mock_client

    client = JiraClient()
    ticket = client.get_issue("PROJ-42")
    assert ticket is not None
    assert ticket.ticket_id == "PROJ-42"
    mock_client.get.assert_called_once()
    assert "PROJ-42" in mock_client.get.call_args[0][0]


@patch.object(JiraClient, "fetch_resolved_tickets")
def test_fetch_recently_resolved(mock_fetch, monkeypatch):
    monkeypatch.setenv("JIRA_BASE_URL", "https://test.atlassian.net")
    monkeypatch.setenv("JIRA_EMAIL", "a@b.com")
    monkeypatch.setenv("JIRA_API_TOKEN", "token")
    monkeypatch.setenv("JIRA_PROJECT_KEY", "PROJ")
    from src.config import get_settings

    get_settings.cache_clear()

    mock_fetch.return_value = []
    client = JiraClient()
    client.fetch_recently_resolved(30)
    mock_fetch.assert_called_once()
    jql = mock_fetch.call_args.kwargs["jql"]
    assert "resolved >= -30m" in jql
