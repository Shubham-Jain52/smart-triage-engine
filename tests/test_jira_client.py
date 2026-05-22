"""Tests for Jira client parsing."""

from src.integrations.jira.client import JiraClient


def test_parse_issue_extracts_fields():
    client = JiraClient.__new__(JiraClient)
    issue = {
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
            "status": {"name": "Done"},
        },
    }
    ticket = client._parse_issue(issue)
    assert ticket is not None
    assert ticket.ticket_id == "PROJ-42"
    assert ticket.title == "VPN drops"
    assert "certificate" in ticket.resolution_text.lower()
    assert ticket.team == "Network"
