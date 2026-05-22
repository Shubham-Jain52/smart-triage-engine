"""Shared Pinecone upsert pipeline for Phase 5 ingest (any ticket source)."""

from __future__ import annotations

import logging
from typing import List

from src.config import get_settings
from src.integrations.jira.client import HistoricalTicket
from src.models.embeddings import embed_batch, warm_up
from src.rag.ingest_utils import build_embed_text, ticket_to_record
from src.rag.pinecone_client import PineconeClient

logger = logging.getLogger(__name__)


def upsert_tickets_to_pinecone(
    tickets: List[HistoricalTicket],
    *,
    dry_run: bool = False,
) -> int:
    """Embed tickets and upsert to Pinecone. Returns upserted count (0 if dry_run)."""
    if not tickets:
        logger.warning("No tickets to ingest.")
        return 0

    warm_up()
    texts = [build_embed_text(t.title, t.description) for t in tickets]
    logger.info("Generating embeddings for %s tickets...", len(tickets))
    vectors = embed_batch(texts, batch_size=32)
    records = [ticket_to_record(t, v) for t, v in zip(tickets, vectors)]

    if dry_run:
        logger.info(
            "Dry run: would upsert %s vectors. Sample id=%s title=%r",
            len(records),
            records[0]["id"],
            records[0]["metadata"].get("title"),
        )
        return 0

    settings = get_settings()
    pc = PineconeClient()
    upserted = pc.upsert_records(records, batch_size=settings.INGEST_BATCH_SIZE)
    stats = pc.describe_stats()
    logger.info("Upserted %s vectors. Index stats: %s", upserted, stats)
    return upserted
