"""Pinecone retrieval for Phase 2 RAG."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from src.config import get_settings
from src.models.embeddings import embed
from src.rag.ingest_utils import build_embed_text
from src.rag.pinecone_client import PineconeClient

logger = logging.getLogger(__name__)

# Metadata keys populated by Phase 5 ingest (see ingest_utils.ticket_to_record)
METADATA_KEYS = ("ticket_id", "title", "description", "resolution_text", "team", "resolved_at")


@dataclass
class RetrievalContext:
    ticket_id: str
    title: str
    description: str
    resolution_text: str
    team: str
    score: float


@dataclass
class RetrievalResult:
    similar_past_tickets: List[str] = field(default_factory=list)
    contexts: List[RetrievalContext] = field(default_factory=list)


class TicketRetriever:
    def __init__(self, pinecone_client: Optional[PineconeClient] = None) -> None:
        self._pinecone = pinecone_client

    @property
    def pinecone(self) -> PineconeClient:
        if self._pinecone is None:
            self._pinecone = PineconeClient()
        return self._pinecone

    def retrieve(self, title: str, description: str, top_k: Optional[int] = None) -> RetrievalResult:
        settings = get_settings()
        k = top_k if top_k is not None else settings.RAG_TOP_K
        text = build_embed_text(title, description)
        vector = embed(text)
        matches = self.pinecone.query(vector, top_k=k)

        contexts: List[RetrievalContext] = []
        ids: List[str] = []
        for match in matches:
            meta = match.get("metadata") or {}
            ticket_id = str(meta.get("ticket_id") or match.get("id") or "").strip()
            if ticket_id:
                ids.append(ticket_id)
            contexts.append(
                RetrievalContext(
                    ticket_id=ticket_id,
                    title=str(meta.get("title") or ""),
                    description=str(meta.get("description") or ""),
                    resolution_text=str(meta.get("resolution_text") or ""),
                    team=str(meta.get("team") or ""),
                    score=float(match.get("score") or 0.0),
                )
            )

        logger.info("Retrieved %s similar ticket(s) for RAG", len(contexts))
        return RetrievalResult(similar_past_tickets=ids, contexts=contexts)
