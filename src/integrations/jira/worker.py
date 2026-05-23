"""Phase 3: Jira issue created → triage API → update Jira + comment."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from src.api.v1.schemas import TicketPayload, TicketStatusResponse
from src.config import get_settings
from src.integrations.jira.client import JiraClient, WorkerIssue
from src.integrations.jira.comment_formatter import format_triage_comment
from src.integrations.jira.team_mapping import TeamJiraMapping, load_team_mapping, resolve_mapping
from src.integrations.jira.triage_client import TriageApiClient

logger = logging.getLogger(__name__)


@dataclass
class WorkerResult:
    ticket_id: str
    status: str
    message: str = ""


class JiraTriageWorker:
    def __init__(
        self,
        jira_client: Optional[JiraClient] = None,
        triage_client: Optional[TriageApiClient] = None,
    ) -> None:
        self._jira = jira_client
        self._triage = triage_client
        self._mapping: Optional[dict[str, TeamJiraMapping]] = None

    @property
    def jira(self) -> JiraClient:
        if self._jira is None:
            self._jira = JiraClient()
        return self._jira

    @property
    def triage(self) -> TriageApiClient:
        if self._triage is None:
            self._triage = TriageApiClient()
        return self._triage

    @property
    def mapping(self) -> dict[str, TeamJiraMapping]:
        if self._mapping is None:
            self._mapping = load_team_mapping()
        return self._mapping

    def process_issue(self, issue_key: str, *, dry_run: bool = False) -> WorkerResult:
        settings = get_settings()
        issue = self.jira.get_worker_issue(issue_key)
        if issue is None:
            return WorkerResult(ticket_id=issue_key, status="failed", message="Issue not found")

        processed_label = settings.JIRA_WORKER_PROCESSED_LABEL.strip()
        if processed_label and processed_label in issue.labels:
            return WorkerResult(
                ticket_id=issue_key,
                status="skipped",
                message=f"Already has label {processed_label!r}",
            )

        if dry_run:
            logger.info("Dry run: would triage %s — %r", issue_key, issue.title)
            return WorkerResult(ticket_id=issue_key, status="skipped", message="dry run")

        try:
            payload = self._issue_to_payload(issue)
            triage_result = self.triage.submit_and_wait(payload)
            self._apply_jira_updates(issue, triage_result)
            return WorkerResult(
                ticket_id=issue_key,
                status="completed" if triage_result.status == "completed" else triage_result.status,
                message=f"triage={triage_result.status} team={triage_result.assigned_team}",
            )
        except Exception as e:
            logger.exception("Worker failed for %s", issue_key)
            return WorkerResult(ticket_id=issue_key, status="failed", message=str(e))

    def poll_and_process(self, since_minutes: Optional[int] = None) -> List[WorkerResult]:
        settings = get_settings()
        lookback = since_minutes if since_minutes is not None else settings.JIRA_WORKER_POLL_MINUTES
        issues = self.jira.fetch_recently_created(lookback)
        logger.info("Found %s new issue(s) to process (last %sm)", len(issues), lookback)
        return [self.process_issue(issue.ticket_id) for issue in issues]

    def _issue_to_payload(self, issue: WorkerIssue) -> TicketPayload:
        return TicketPayload(
            ticket_id=issue.ticket_id,
            title=issue.title,
            description=issue.description or issue.title,
            created_at=_parse_jira_datetime(issue.created_at),
        )

    def _apply_jira_updates(self, issue: WorkerIssue, result: TicketStatusResponse) -> None:
        if result.status != "completed":
            logger.warning(
                "Skipping Jira updates for %s: triage status=%s",
                issue.ticket_id,
                result.status,
            )
            return

        settings = get_settings()
        team_map = resolve_mapping(result.assigned_team, result.requires_hitl, self.mapping)

        labels = list(team_map.labels)
        processed_label = settings.JIRA_WORKER_PROCESSED_LABEL.strip()
        if processed_label:
            labels.append(processed_label)

        assignee_id = None if result.requires_hitl else team_map.assignee_account_id

        self.jira.update_issue_routing(
            issue.ticket_id,
            component=team_map.component,
            assignee_account_id=assignee_id,
            labels_to_add=labels or None,
            current_labels=issue.labels,
        )

        _, adf = format_triage_comment(result)
        self.jira.add_comment(issue.ticket_id, adf)


def _parse_jira_datetime(value: str) -> datetime:
    if not value or not value.strip():
        return datetime.now(timezone.utc)
    text = value.strip().replace("Z", "+00:00")
    text = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", text)
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        logger.warning("Could not parse Jira datetime %r; using now()", value)
        return datetime.now(timezone.utc)
