"""Shared helpers for Phase 5 Jira -> Pinecone ingest."""

from __future__ import annotations

from typing import Any, Dict, List

from src.integrations.jira.client import HistoricalTicket
from src.models.preprocessor import TextPreprocessor


def build_embed_text(title: str, description: str) -> str:
    return TextPreprocessor.preprocess(title, description, max_length_chars=8000)


def ticket_to_record(ticket: HistoricalTicket, vector: List[float]) -> Dict[str, Any]:
    meta = {
        "ticket_id": ticket.ticket_id,
        "title": ticket.title[:1000],
        "description": ticket.description[:4000],
        "resolution_text": ticket.resolution_text[:4000],
        "team": ticket.team[:200],
        "resolved_at": ticket.resolved_at[:64],
    }
    return {"id": ticket.ticket_id, "values": vector, "metadata": meta}
