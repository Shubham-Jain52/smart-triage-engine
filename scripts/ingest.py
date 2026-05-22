#!/usr/bin/env python3
"""Phase 5: historical tickets -> Pinecone cold-start ingest.

One vector per ticket (title + description embedded; resolution in metadata).

Sources:
  - ``csv`` / ``dummy``: bundled or custom CSV (no Jira) — default for local dev
  - ``jira``: Jira REST API (requires JIRA_* in .env)

Usage::

    PYTHONPATH=. python scripts/setup_pinecone_index.py   # once
    PYTHONPATH=. python scripts/ingest.py                   # dummy CSV (default)
    PYTHONPATH=. python scripts/ingest.py --source jira     # real Jira when ready
    PYTHONPATH=. python scripts/ingest.py --source csv --csv-path path/to.csv
    PYTHONPATH=. python scripts/ingest.py --dry-run
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
from src.integrations.csv_loader import default_dummy_csv_path, load_tickets_from_csv
from src.integrations.jira.client import JiraClient
from src.rag.ingest_pipeline import upsert_tickets_to_pinecone

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_tickets(source: str, csv_path: Path | None, jql: str | None) -> list:
    settings = get_settings()
    source = source.lower().strip()

    if source in ("csv", "dummy"):
        if csv_path is not None:
            path = csv_path
        elif settings.INGEST_CSV_PATH:
            path = Path(settings.INGEST_CSV_PATH)
        else:
            path = default_dummy_csv_path()
        logger.info("Loading tickets from CSV: %s", path)
        return load_tickets_from_csv(path)

    if source == "jira":
        jira = JiraClient()
        logger.info("Fetching issues from Jira...")
        return jira.fetch_resolved_tickets(
            jql=jql,
            max_issues=settings.INGEST_MAX_ISSUES,
        )

    raise ValueError(f"Unknown source {source!r}. Use: dummy, csv, or jira")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest historical tickets into Pinecone")
    parser.add_argument(
        "--source",
        choices=("dummy", "csv", "jira"),
        default="",
        help="Ticket source (default: INGEST_SOURCE env or 'dummy')",
    )
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=None,
        help="CSV file when --source csv or dummy (default: bundled historical_tickets.csv)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Embed only; no Pinecone upsert")
    parser.add_argument("--jql", default="", help="Override INGEST_JQL (jira source only)")
    args = parser.parse_args()

    settings = get_settings()
    if not args.dry_run and not settings.PINECONE_API_KEY:
        logger.error("PINECONE_API_KEY is required (or use --dry-run)")
        return 1

    source = args.source or settings.INGEST_SOURCE or "dummy"
    jql = args.jql.strip() or None

    try:
        tickets = load_tickets(source, args.csv_path, jql)
    except ValueError as e:
        logger.error("%s", e)
        return 1
    except FileNotFoundError as e:
        logger.error("%s", e)
        return 1

    logger.info("Loaded %s tickets (source=%s)", len(tickets), source)
    upsert_tickets_to_pinecone(tickets, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
