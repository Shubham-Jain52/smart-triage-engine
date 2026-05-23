"""Tests for Jira triage comment formatter."""

from src.api.v1.schemas import TicketStatusResponse
from src.integrations.jira.comment_formatter import format_triage_comment


def test_format_comment_includes_flowcharts(monkeypatch):
    monkeypatch.setenv("INCLUDE_TICKET_IDS_IN_COMMENT", "false")
    from src.config import get_settings

    get_settings.cache_clear()

    result = TicketStatusResponse(
        ticket_id="PROJ-1",
        assigned_team="DevOps",
        confidence_score=0.91,
        requires_hitl=False,
        status="completed",
        problem_flowchart_mermaid="flowchart TD\n  A --> B",
        resolution_flowchart_mermaid="flowchart TD\n  P --> Q",
        rag_resolution_summary="Renew VPN certificate.",
        similar_past_tickets=["DEMO-1"],
    )
    plain, adf = format_triage_comment(result)
    assert "DevOps" in plain
    assert "```mermaid" in plain
    assert "flowchart TD" in plain
    assert "Renew VPN certificate" in plain
    assert "DEMO-1" not in plain
    assert adf["type"] == "doc"
    assert len(adf["content"]) >= 3


def test_format_comment_includes_audit_ids_when_enabled(monkeypatch):
    monkeypatch.setenv("INCLUDE_TICKET_IDS_IN_COMMENT", "true")
    from src.config import get_settings

    get_settings.cache_clear()

    result = TicketStatusResponse(
        ticket_id="PROJ-1",
        assigned_team="DevOps",
        confidence_score=0.91,
        requires_hitl=False,
        status="completed",
        similar_past_tickets=["DEMO-1", "DEMO-2"],
    )
    plain, _ = format_triage_comment(result)
    assert "DEMO-1" in plain
