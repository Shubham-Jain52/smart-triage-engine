#!/usr/bin/env python3
"""Create Pinecone serverless index if missing (BYOK setup).

Index dimension must match EMBEDDING_MODEL_NAME (384 for all-MiniLM-L6-v2).

Usage::

    cp .env.example .env   # set PINECONE_API_KEY, PINECONE_INDEX_NAME, etc.
    PYTHONPATH=. python scripts/setup_pinecone_index.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from src.models.embeddings import embedding_dimension, warm_up
from src.rag.pinecone_client import ensure_serverless_index

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    warm_up()
    dim = embedding_dimension()
    logger.info("Embedding dimension: %s", dim)
    ensure_serverless_index(dimension=dim, metric="cosine")
    logger.info("Pinecone index ready.")


if __name__ == "__main__":
    main()
