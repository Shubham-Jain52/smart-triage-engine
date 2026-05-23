#!/usr/bin/env python3
"""Phase 3.1: poll Jira for recently resolved issues and upsert to Pinecone.

Fallback when Jira Automation webhooks are unavailable or missed.

Usage::

    PYTHONPATH=. python scripts/poll_resolved_ingest.py --once
    PYTHONPATH=. python scripts/poll_resolved_ingest.py --once --dry-run
    PYTHONPATH=. python scripts/poll_resolved_ingest.py   # daemon loop
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
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
from src.integrations.jira.client import JiraClient
from src.services.resolve_ingest_service import ResolveIngestService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_poll(*, once: bool, dry_run: bool, since_minutes: int | None) -> int:
    settings = get_settings()
    if not settings.INGEST_ON_RESOLVE_ENABLED:
        logger.error("INGEST_ON_RESOLVE_ENABLED is false; enable in .env")
        return 1

    if not dry_run and not settings.PINECONE_API_KEY:
        logger.error("PINECONE_API_KEY is required (or use --dry-run)")
        return 1

    lookback = since_minutes if since_minutes is not None else settings.INGEST_ON_RESOLVE_POLL_MINUTES
    interval = settings.INGEST_ON_RESOLVE_POLL_INTERVAL_SECONDS
    service = ResolveIngestService()
    jira = JiraClient()

    def poll_once() -> tuple[int, int, int]:
        ingested = skipped = failed = 0
        try:
            tickets = jira.fetch_recently_resolved(lookback)
        except Exception as e:
            logger.exception("Failed to fetch recently resolved issues: %s", e)
            return 0, 0, 1

        logger.info("Found %s recently resolved issue(s) (last %sm)", len(tickets), lookback)
        for ticket in tickets:
            result = service.ingest_resolved_ticket(
                ticket.ticket_id,
                dry_run=dry_run,
                skip_enabled_check=True,
            )
            if result.status == "ingested":
                ingested += 1
            elif result.status == "skipped":
                skipped += 1
            else:
                failed += 1
            logger.info(
                "%s: %s%s",
                ticket.ticket_id,
                result.status,
                f" — {result.message}" if result.message else "",
            )
        return ingested, skipped, failed

    if once:
        _, _, failed = poll_once()
        return 1 if failed else 0

    logger.info("Polling every %ss (lookback %sm); Ctrl+C to stop", interval, lookback)
    while True:
        poll_once()
        time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll Jira for resolved issues and upsert to Pinecone")
    parser.add_argument("--once", action="store_true", help="Run one poll cycle (for cron)")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and validate only; no Pinecone upsert")
    parser.add_argument(
        "--since-minutes",
        type=int,
        default=None,
        help="JQL lookback override (default: INGEST_ON_RESOLVE_POLL_MINUTES)",
    )
    args = parser.parse_args()

    try:
        return run_poll(once=args.once, dry_run=args.dry_run, since_minutes=args.since_minutes)
    except KeyboardInterrupt:
        logger.info("Stopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
