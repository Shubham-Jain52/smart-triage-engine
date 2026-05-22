"""Pinecone vector store client for ingest and RAG retrieval."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.config import get_settings

logger = logging.getLogger(__name__)


class PineconeClient:
    """Thin wrapper around the Pinecone Python SDK."""

    def __init__(self, api_key: Optional[str] = None, index_name: Optional[str] = None) -> None:
        settings = get_settings()
        self.api_key = (api_key or settings.PINECONE_API_KEY).strip()
        self.index_name = (index_name or settings.PINECONE_INDEX_NAME).strip()
        self.namespace = settings.PINECONE_NAMESPACE.strip() or None
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY is required")
        if not self.index_name:
            raise ValueError("PINECONE_INDEX_NAME is required")

        from pinecone import Pinecone

        self._pc = Pinecone(api_key=self.api_key)
        self._index = self._pc.Index(self.index_name)

    def upsert_records(
        self,
        records: List[Dict[str, Any]],
        batch_size: int = 100,
    ) -> int:
        """
        Upsert vectors. Each record: id, values, metadata (optional).
        Returns total upserted count.
        """
        total = 0
        for i in range(0, len(records), batch_size):
            chunk = records[i : i + batch_size]
            kwargs: Dict[str, Any] = {"vectors": chunk}
            if self.namespace:
                kwargs["namespace"] = self.namespace
            self._index.upsert(**kwargs)
            total += len(chunk)
        return total

    def query(
        self,
        vector: List[float],
        top_k: int = 3,
        include_metadata: bool = True,
    ) -> List[Dict[str, Any]]:
        """Return matches with id, score, and metadata."""
        kwargs: Dict[str, Any] = {
            "vector": vector,
            "top_k": top_k,
            "include_metadata": include_metadata,
        }
        if self.namespace:
            kwargs["namespace"] = self.namespace
        response = self._index.query(**kwargs)
        matches = getattr(response, "matches", None) or response.get("matches", [])
        out: List[Dict[str, Any]] = []
        for m in matches:
            if hasattr(m, "id"):
                out.append(
                    {
                        "id": m.id,
                        "score": float(m.score),
                        "metadata": dict(m.metadata or {}),
                    }
                )
            else:
                out.append(
                    {
                        "id": m["id"],
                        "score": float(m.get("score", 0)),
                        "metadata": dict(m.get("metadata") or {}),
                    }
                )
        return out

    def describe_stats(self) -> Dict[str, Any]:
        """Index statistics for validation."""
        kwargs: Dict[str, Any] = {}
        if self.namespace:
            kwargs["namespace"] = self.namespace
        stats = self._index.describe_index_stats(**kwargs)
        if hasattr(stats, "to_dict"):
            return stats.to_dict()
        if hasattr(stats, "total_vector_count"):
            return {"total_vector_count": stats.total_vector_count, "namespaces": getattr(stats, "namespaces", {})}
        return dict(stats) if isinstance(stats, dict) else {"raw": str(stats)}


def ensure_serverless_index(
    dimension: int,
    metric: str = "cosine",
) -> None:
    """
    Create serverless index if it does not exist (BYOK setup helper).
    Used by scripts/setup_pinecone_index.py.
    """
    from pinecone import Pinecone, ServerlessSpec

    settings = get_settings()
    if not settings.PINECONE_API_KEY:
        raise ValueError("PINECONE_API_KEY is required")

    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    listed = pc.list_indexes()
    names = set(getattr(listed, "names", lambda: [])())
    if not names and hasattr(listed, "indexes"):
        names = {getattr(i, "name", i.get("name")) for i in listed.indexes()}
    if settings.PINECONE_INDEX_NAME in names:
        logger.info("Pinecone index %s already exists", settings.PINECONE_INDEX_NAME)
        return

    logger.info(
        "Creating Pinecone index %s (dim=%s, metric=%s)",
        settings.PINECONE_INDEX_NAME,
        dimension,
        metric,
    )
    pc.create_index(
        name=settings.PINECONE_INDEX_NAME,
        dimension=dimension,
        metric=metric,
        spec=ServerlessSpec(cloud=settings.PINECONE_CLOUD, region=settings.PINECONE_REGION),
    )
