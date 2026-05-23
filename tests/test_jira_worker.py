"""Tests for Phase 3 Jira triage worker."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from src.api.v1.schemas import TicketStatusResponse
from src.integrations.jira.client import WorkerIssue
from src.integrations.jira.worker import JiraTriageWorker


@pytest.fixture
def worker():
    return JiraTriageWorker(jira_client=MagicMock(), triage_client=MagicMock())


def test_process_issue_skips_already_processed(worker, monkeypatch):
    monkeypatch.setenv("JIRA_WORKER_PROCESSED_LABEL", "auto-triaged")
    from src.config import get_settings

    get_settings.cache_clear()

    worker.jira.get_worker_issue.return_value = WorkerIssue(
        ticket_id="PROJ-1",
        title="VPN",
        description="drops",
        created_at="2026-01-01T00:00:00.000+0000",
        labels=["auto-triaged"],
    )
    result = worker.process_issue("PROJ-1")
    assert result.status == "skipped"
    worker.triage.submit_and_wait.assert_not_called()


def test_process_issue_completes_flow(worker, monkeypatch, tmp_path):
    monkeypatch.setenv("JIRA_WORKER_PROCESSED_LABEL", "auto-triaged")
    mapping_file = tmp_path / "map.json"
    mapping_file.write_text(
        '{"DevOps": {"component": "DevOps", "labels": ["auto-routed"]}, "hitl": {"labels": ["hitl"]}}',
        encoding="utf-8",
    )
    monkeypatch.setenv("JIRA_TEAM_MAPPING_PATH", str(mapping_file))
    from src.config import get_settings

    get_settings.cache_clear()
    worker._mapping = None

    worker.jira.get_worker_issue.return_value = WorkerIssue(
        ticket_id="PROJ-42",
        title="VPN drops",
        description="User issue",
        created_at="2026-01-01T00:00:00.000+0000",
        labels=[],
    )
    worker.triage.submit_and_wait.return_value = TicketStatusResponse(
        ticket_id="PROJ-42",
        assigned_team="DevOps",
        confidence_score=0.92,
        requires_hitl=False,
        status="completed",
        problem_flowchart_mermaid="flowchart TD\n  A --> B",
        resolution_flowchart_mermaid="flowchart TD\n  P --> Q",
        rag_resolution_summary="Check cert.",
    )

    result = worker.process_issue("PROJ-42")
    assert result.status == "completed"
    worker.triage.submit_and_wait.assert_called_once()
    worker.jira.update_issue_routing.assert_called_once()
    worker.jira.add_comment.assert_called_once()
    adf = worker.jira.add_comment.call_args[0][1]
    assert adf["type"] == "doc"


def test_process_issue_hitl_uses_hitl_mapping(worker, monkeypatch, tmp_path):
    monkeypatch.setenv("JIRA_WORKER_PROCESSED_LABEL", "auto-triaged")
    mapping_file = tmp_path / "map.json"
    mapping_file.write_text(
        '{"DevOps": {"assigneeAccountId": "acc-1", "labels": []}, "hitl": {"labels": ["hitl"]}}',
        encoding="utf-8",
    )
    monkeypatch.setenv("JIRA_TEAM_MAPPING_PATH", str(mapping_file))
    from src.config import get_settings

    get_settings.cache_clear()
    worker._mapping = None

    worker.jira.get_worker_issue.return_value = WorkerIssue(
        ticket_id="PROJ-99",
        title="t",
        description="d",
        created_at="2026-01-01T00:00:00.000+0000",
    )
    worker.triage.submit_and_wait.return_value = TicketStatusResponse(
        ticket_id="PROJ-99",
        assigned_team="DevOps",
        confidence_score=0.5,
        requires_hitl=True,
        status="completed",
    )

    worker.process_issue("PROJ-99")
    kwargs = worker.jira.update_issue_routing.call_args.kwargs
    assert kwargs.get("assignee_account_id") is None
    assert "hitl" in kwargs.get("labels_to_add", [])
