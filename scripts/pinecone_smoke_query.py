#!/usr/bin/env python3
"""Smoke-test Pinecone retrieval after ingest (Phase 5 validation).

Usage::

    PYTHONPATH=. python scripts/pinecone_smoke_query.py "VPN disconnects after login"
"""

from __future__ import annotations

import argparse
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

from src.config import get_settings
from src.models.embeddings import embed
from src.models.preprocessor import TextPreprocessor
from src.rag.pinecone_client import PineconeClient

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="?", default="VPN disconnects after login")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.PINECONE_API_KEY:
        logger.error("PINECONE_API_KEY is required")
        return 1

    text = TextPreprocessor.preprocess(args.query, "", max_length_chars=2000)
    vector = embed(text)
    pc = PineconeClient()
    matches = pc.query(vector, top_k=settings.RAG_TOP_K)

    if not matches:
        logger.warning("No matches returned. Run ingest.py first.")
        return 1

    for i, m in enumerate(matches, 1):
        meta = m.get("metadata") or {}
        logger.info(
            "%s. %s score=%.3f team=%s resolution=%s",
            i,
            m["id"],
            m["score"],
            meta.get("team", ""),
            (meta.get("resolution_text") or "")[:120],
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
