"""Phase 3.1: ingest a single resolved Jira ticket into Pinecone."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Optional

from src.config import get_settings
from src.integrations.jira.client import HistoricalTicket, JiraClient, RESOLVED_STATUSES
from src.rag.ingest_pipeline import upsert_tickets_to_pinecone

logger = logging.getLogger(__name__)

IngestOutcome = Literal["ingested", "skipped", "failed"]


@dataclass
class IngestResult:
    ticket_id: str
    status: IngestOutcome
    message: str = ""


class ResolveIngestService:
    def __init__(
        self,
        jira_client: Optional[JiraClient] = None,
    ) -> None:
        self._jira = jira_client

    @property
    def jira(self) -> JiraClient:
        if self._jira is None:
            self._jira = JiraClient()
        return self._jira

    def ingest_resolved_ticket(
        self,
        ticket_id: str,
        *,
        dry_run: bool = False,
        skip_enabled_check: bool = False,
    ) -> IngestResult:
        settings = get_settings()
        ticket_id = ticket_id.strip()
        if not ticket_id:
            return IngestResult(ticket_id="", status="failed", message="ticket_id is required")

        if not skip_enabled_check and not settings.INGEST_ON_RESOLVE_ENABLED:
            return IngestResult(
                ticket_id=ticket_id,
                status="skipped",
                message="INGEST_ON_RESOLVE_ENABLED is false",
            )

        if not dry_run and not settings.PINECONE_API_KEY:
            return IngestResult(
                ticket_id=ticket_id,
                status="failed",
                message="PINECONE_API_KEY is required",
            )

        try:
            ticket = self.jira.get_issue(ticket_id)
        except Exception as e:
            logger.exception("Failed to fetch Jira issue %s", ticket_id)
            return IngestResult(ticket_id=ticket_id, status="failed", message=str(e))

        if ticket is None:
            return IngestResult(
                ticket_id=ticket_id,
                status="failed",
                message="Issue not found or could not be parsed",
            )

        skip_reason = self._skip_reason(ticket, settings.INGEST_ON_RESOLVE_REQUIRE_RESOLUTION)
        if skip_reason:
            logger.info("Skipping ingest for %s: %s", ticket_id, skip_reason)
            return IngestResult(ticket_id=ticket_id, status="skipped", message=skip_reason)

        try:
            count = upsert_tickets_to_pinecone([ticket], dry_run=dry_run)
        except Exception as e:
            logger.exception("Failed to upsert %s to Pinecone", ticket_id)
            return IngestResult(ticket_id=ticket_id, status="failed", message=str(e))

        if dry_run:
            return IngestResult(
                ticket_id=ticket_id,
                status="ingested",
                message="dry run: would upsert 1 vector",
            )

        return IngestResult(
            ticket_id=ticket_id,
            status="ingested",
            message=f"upserted {count} vector(s)",
        )

    def _skip_reason(self, ticket: HistoricalTicket, require_resolution: bool) -> str:
        if ticket.status and ticket.status not in RESOLVED_STATUSES:
            return f"issue status is {ticket.status!r}, not resolved"

        if not ticket.title and not ticket.description:
            return "empty title and description"

        if require_resolution and not self._has_usable_resolution(ticket.resolution_text):
            return "no usable resolution text"

        return ""

    @staticmethod
    def _has_usable_resolution(resolution_text: str) -> bool:
        text = (resolution_text or "").strip()
        if not text:
            return False
        if text.lower() in {s.lower() for s in RESOLVED_STATUSES}:
            return False
        return True
