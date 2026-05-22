"""Tests for ingest record building."""

from src.integrations.jira.client import HistoricalTicket
from src.rag.ingest_utils import build_embed_text, ticket_to_record


def test_build_embed_text_normalizes():
    text = build_embed_text("VPN Issue!", "User cannot connect.")
    assert "vpn issue" in text
    assert "!" not in text


def test_ticket_to_record_shape():
    ticket = HistoricalTicket(
        ticket_id="PROJ-9",
        title="Email bounce",
        description="SMTP 550 errors",
        resolution_text="Whitelist sender domain",
        team="IT Support",
        resolved_at="2026-01-01T00:00:00.000Z",
    )
    rec = ticket_to_record(ticket, [0.0] * 384)
    assert rec["id"] == "PROJ-9"
    assert rec["metadata"]["resolution_text"] == "Whitelist sender domain"
    assert len(rec["values"]) == 384
