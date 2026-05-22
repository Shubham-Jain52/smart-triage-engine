"""Local sentence embeddings for Pinecone ingest and RAG retrieval."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import List, Optional

from src.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer

    name = get_settings().EMBEDDING_MODEL_NAME
    logger.info("Loading embedding model: %s", name)
    return SentenceTransformer(name)


def embedding_dimension() -> int:
    """Vector size for the configured embedding model."""
    return int(_get_model().get_sentence_embedding_dimension())


def embed(text: str) -> List[float]:
    """Embed a single string; returns a list of floats."""
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text")
    vector = _get_model().encode(text, normalize_embeddings=True)
    return vector.tolist()


def embed_batch(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """Embed multiple strings in batches."""
    cleaned = [t if t and t.strip() else " " for t in texts]
    vectors = _get_model().encode(
        cleaned,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=len(cleaned) > 50,
    )
    return [v.tolist() for v in vectors]


def warm_up() -> None:
    """Load model and run a dummy encode (for CLI startup)."""
    embed("warmup")
