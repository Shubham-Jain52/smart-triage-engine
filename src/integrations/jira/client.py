"""Jira Cloud REST client for resolved-issue export (Phase 5 ingest)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from src.config import get_settings
from src.integrations.jira.text_utils import jira_description_to_text

logger = logging.getLogger(__name__)

RESOLVED_STATUSES = frozenset({"Resolved", "Done", "Closed"})
ISSUE_FIELDS = "summary,description,resolutiondate,components,comment,status"
WORKER_ISSUE_FIELDS = "summary,description,created,status,labels,components,assignee"


@dataclass
class HistoricalTicket:
    ticket_id: str
    title: str
    description: str
    resolution_text: str
    team: str
    resolved_at: str
    status: str = ""


@dataclass
class WorkerIssue:
    """Open issue snapshot for Phase 3 triage worker."""

    ticket_id: str
    title: str
    description: str
    created_at: str
    status: str = ""
    labels: List[str] = field(default_factory=list)


class JiraClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        email: Optional[str] = None,
        api_token: Optional[str] = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.JIRA_BASE_URL).rstrip("/")
        self.email = email or settings.JIRA_EMAIL
        self.api_token = api_token or settings.JIRA_API_TOKEN
        if not self.base_url or not self.email or not self.api_token:
            raise ValueError("JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN are required")

        self._auth = (self.email, self.api_token)
        self._api = f"{self.base_url}/rest/api/3"

    def default_ingest_jql(self, project_key: Optional[str] = None) -> str:
        settings = get_settings()
        key = (project_key or settings.JIRA_PROJECT_KEY).strip()
        if not key:
            raise ValueError("JIRA_PROJECT_KEY is required when INGEST_JQL is empty")
        months = settings.INGEST_MONTHS
        status_list = ", ".join(sorted(RESOLVED_STATUSES))
        return (
            f'project = "{key}" AND status in ({status_list}) '
            f"AND resolved >= -{months}m ORDER BY resolved DESC"
        )

    def recently_resolved_jql(
        self,
        since_minutes: int,
        project_key: Optional[str] = None,
    ) -> str:
        settings = get_settings()
        key = (project_key or settings.JIRA_PROJECT_KEY).strip()
        if not key:
            raise ValueError("JIRA_PROJECT_KEY is required for recently resolved JQL")
        status_list = ", ".join(sorted(RESOLVED_STATUSES))
        return (
            f'project = "{key}" AND status in ({status_list}) '
            f"AND resolved >= -{since_minutes}m ORDER BY resolved DESC"
        )

    def get_issue(self, issue_key: str) -> Optional[HistoricalTicket]:
        """Fetch a single issue by key and parse to HistoricalTicket."""
        with httpx.Client(timeout=60.0) as client:
            r = client.get(
                f"{self._api}/issue/{issue_key}",
                params={"fields": ISSUE_FIELDS},
                auth=self._auth,
                headers={"Accept": "application/json"},
            )
            r.raise_for_status()
            return self._parse_issue(r.json())

    def is_resolved_status(self, status_name: str) -> bool:
        return status_name.strip() in RESOLVED_STATUSES

    def fetch_recently_resolved(
        self,
        since_minutes: int,
        project_key: Optional[str] = None,
    ) -> List[HistoricalTicket]:
        """Fetch issues resolved within the last ``since_minutes``."""
        jql = self.recently_resolved_jql(since_minutes, project_key)
        return self.fetch_resolved_tickets(jql=jql)

    def recently_created_jql(
        self,
        since_minutes: int,
        project_key: Optional[str] = None,
        exclude_label: Optional[str] = None,
    ) -> str:
        settings = get_settings()
        key = (project_key or settings.JIRA_PROJECT_KEY).strip()
        if not key:
            raise ValueError("JIRA_PROJECT_KEY is required for recently created JQL")
        label = (exclude_label if exclude_label is not None else settings.JIRA_WORKER_PROCESSED_LABEL).strip()
        jql = f'project = "{key}" AND created >= -{since_minutes}m'
        if label:
            jql += f' AND labels != "{label}"'
        return f"{jql} ORDER BY created DESC"

    def get_worker_issue(self, issue_key: str) -> Optional[WorkerIssue]:
        with httpx.Client(timeout=60.0) as client:
            r = client.get(
                f"{self._api}/issue/{issue_key}",
                params={"fields": WORKER_ISSUE_FIELDS},
                auth=self._auth,
                headers={"Accept": "application/json"},
            )
            r.raise_for_status()
            return self._parse_worker_issue(r.json())

    def fetch_recently_created(
        self,
        since_minutes: int,
        project_key: Optional[str] = None,
        max_issues: int = 50,
    ) -> List[WorkerIssue]:
        jql = self.recently_created_jql(since_minutes, project_key)
        page_size = min(50, max_issues)
        start_at = 0
        issues: List[WorkerIssue] = []

        while len(issues) < max_issues:
            data = self.search_issues(
                jql,
                max_results=page_size,
                start_at=start_at,
                fields=WORKER_ISSUE_FIELDS,
            )
            batch = data.get("issues") or []
            if not batch:
                break
            for raw in batch:
                parsed = self._parse_worker_issue(raw)
                if parsed:
                    issues.append(parsed)
                if len(issues) >= max_issues:
                    break
            if len(batch) < page_size:
                break
            start_at += len(batch)

        return issues

    def search_issues(
        self,
        jql: str,
        max_results: int = 50,
        start_at: int = 0,
        fields: Optional[str] = None,
    ) -> Dict[str, Any]:
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": fields or ISSUE_FIELDS,
        }
        with httpx.Client(timeout=60.0) as client:
            r = client.get(
                f"{self._api}/search",
                params=params,
                auth=self._auth,
                headers={"Accept": "application/json"},
            )
            r.raise_for_status()
            return r.json()

    def fetch_resolved_tickets(
        self,
        jql: Optional[str] = None,
        max_issues: int = 0,
    ) -> List[HistoricalTicket]:
        settings = get_settings()
        query = (jql or settings.INGEST_JQL or self.default_ingest_jql()).strip()
        page_size = min(settings.INGEST_BATCH_SIZE, 100)
        start_at = 0
        tickets: List[HistoricalTicket] = []

        while True:
            data = self.search_issues(query, max_results=page_size, start_at=start_at)
            issues = data.get("issues") or data.get("values") or []
            if not issues:
                break

            for issue in issues:
                parsed = self._parse_issue(issue)
                if parsed:
                    tickets.append(parsed)
                if max_issues > 0 and len(tickets) >= max_issues:
                    return tickets

            total = data.get("total")
            start_at += len(issues)
            if len(issues) < page_size:
                break
            if total is not None and start_at >= int(total):
                break

        return tickets

    def add_comment(self, issue_key: str, adf_body: Dict[str, Any]) -> None:
        """Add a comment using Atlassian Document Format body."""
        payload: Dict[str, Any] = {"body": adf_body}
        settings = get_settings()
        role = settings.JIRA_COMMENT_VISIBILITY_ROLE.strip()
        if role:
            payload["visibility"] = {"type": "role", "value": role}

        with httpx.Client(timeout=60.0) as client:
            r = client.post(
                f"{self._api}/issue/{issue_key}/comment",
                json=payload,
                auth=self._auth,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
            r.raise_for_status()
        logger.info("Added triage comment to %s", issue_key)

    def update_issue_routing(
        self,
        issue_key: str,
        *,
        component: Optional[str] = None,
        assignee_account_id: Optional[str] = None,
        labels_to_add: Optional[List[str]] = None,
        current_labels: Optional[List[str]] = None,
    ) -> None:
        """Update assignee, component, and/or merge labels."""
        fields: Dict[str, Any] = {}
        if component:
            fields["components"] = [{"name": component}]
        if assignee_account_id:
            fields["assignee"] = {"accountId": assignee_account_id}
        if labels_to_add:
            merged = list(dict.fromkeys((current_labels or []) + labels_to_add))
            fields["labels"] = merged

        if not fields:
            return

        with httpx.Client(timeout=60.0) as client:
            r = client.put(
                f"{self._api}/issue/{issue_key}",
                json={"fields": fields},
                auth=self._auth,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
            r.raise_for_status()
        logger.info("Updated Jira routing fields on %s", issue_key)

    def _parse_worker_issue(self, issue: Dict[str, Any]) -> Optional[WorkerIssue]:
        key = issue.get("key") or issue.get("id")
        fields = issue.get("fields") or {}
        if not key:
            return None

        title = (fields.get("summary") or "").strip()
        description = jira_description_to_text(fields.get("description"))
        created = fields.get("created") or ""
        if not title and not description:
            return None

        status_obj = fields.get("status") or {}
        labels = list(fields.get("labels") or [])

        return WorkerIssue(
            ticket_id=str(key),
            title=title,
            description=description,
            created_at=created,
            status=(status_obj.get("name") or "").strip(),
            labels=labels,
        )

    def _parse_issue(self, issue: Dict[str, Any]) -> Optional[HistoricalTicket]:
        key = issue.get("key") or issue.get("id")
        fields = issue.get("fields") or {}
        if not key:
            return None

        title = (fields.get("summary") or "").strip()
        description = jira_description_to_text(fields.get("description"))
        resolution_text = self._extract_resolution_text(fields)
        if not title and not description:
            return None

        team = ""
        components = fields.get("components") or []
        if components and isinstance(components[0], dict):
            team = (components[0].get("name") or "").strip()

        resolved_at = fields.get("resolutiondate") or ""
        if not resolved_at:
            resolved_at = datetime.now(timezone.utc).isoformat()

        status_obj = fields.get("status") or {}
        status_name = (status_obj.get("name") or "").strip()

        return HistoricalTicket(
            ticket_id=str(key),
            title=title,
            description=description,
            resolution_text=resolution_text,
            team=team,
            resolved_at=resolved_at,
            status=status_name,
        )

    def _extract_resolution_text(self, fields: Dict[str, Any]) -> str:
        comments = (fields.get("comment") or {}).get("comments") or []
        resolution_phrases = ("resolved", "fixed", "solution", "root cause", "workaround")
        for comment in reversed(comments):
            body = comment.get("body")
            text = jira_description_to_text(body)
            if not text:
                continue
            lower = text.lower()
            if any(p in lower for p in resolution_phrases):
                return text
        if comments:
            last = comments[-1]
            return jira_description_to_text(last.get("body"))
        status = fields.get("status") or {}
        return (status.get("name") or "Resolved").strip()
