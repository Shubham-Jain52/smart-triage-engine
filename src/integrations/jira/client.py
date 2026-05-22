"""Jira Cloud REST client for resolved-issue export (Phase 5 ingest)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from src.config import get_settings
from src.integrations.jira.text_utils import jira_description_to_text

logger = logging.getLogger(__name__)


@dataclass
class HistoricalTicket:
    ticket_id: str
    title: str
    description: str
    resolution_text: str
    team: str
    resolved_at: str


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
        return (
            f'project = "{key}" AND status in (Resolved, Done, Closed) '
            f"AND resolved >= -{months}m ORDER BY resolved DESC"
        )

    def search_issues(self, jql: str, max_results: int = 50, start_at: int = 0) -> Dict[str, Any]:
        params = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": "summary,description,resolutiondate,components,comment,status",
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

        return HistoricalTicket(
            ticket_id=str(key),
            title=title,
            description=description,
            resolution_text=resolution_text,
            team=team,
            resolved_at=resolved_at,
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
