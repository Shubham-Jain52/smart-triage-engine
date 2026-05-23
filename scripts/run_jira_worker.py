#!/usr/bin/env python3
"""Phase 3: Jira worker — triage new issues and post flowcharts to Jira.

Usage::

    # Single issue (Jira Automation webhook target or manual):
    PYTHONPATH=. python scripts/run_jira_worker.py --issue PROJ-42

    # Poll recently created issues (cron fallback):
    PYTHONPATH=. python scripts/run_jira_worker.py --once
    PYTHONPATH=. python scripts/run_jira_worker.py              # daemon loop

    PYTHONPATH=. python scripts/run_jira_worker.py --issue PROJ-42 --dry-run
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
from src.integrations.jira.worker import JiraTriageWorker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run(*, issue: str | None, once: bool, dry_run: bool, since_minutes: int | None) -> int:
    settings = get_settings()
    worker = JiraTriageWorker()

    if issue:
        result = worker.process_issue(issue, dry_run=dry_run)
        logger.info("%s: %s — %s", result.ticket_id, result.status, result.message)
        return 0 if result.status in ("completed", "skipped") else 1

    lookback = since_minutes if since_minutes is not None else settings.JIRA_WORKER_POLL_MINUTES
    interval = settings.JIRA_WORKER_POLL_INTERVAL_SECONDS

    def poll_once() -> int:
        results = worker.poll_and_process(since_minutes=lookback)
        failed = sum(1 for r in results if r.status == "failed")
        return 1 if failed else 0

    if once:
        return poll_once()

    logger.info("Polling every %ss (lookback %sm); Ctrl+C to stop", interval, lookback)
    while True:
        poll_once()
        time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="Jira triage worker (Phase 3)")
    parser.add_argument("--issue", default="", help="Process a single Jira issue key")
    parser.add_argument("--once", action="store_true", help="Run one poll cycle (for cron)")
    parser.add_argument("--dry-run", action="store_true", help="Fetch only; no triage or Jira writes")
    parser.add_argument(
        "--since-minutes",
        type=int,
        default=None,
        help="Poll lookback override (default: JIRA_WORKER_POLL_MINUTES)",
    )
    args = parser.parse_args()

    try:
        return run(
            issue=args.issue.strip() or None,
            once=args.once,
            dry_run=args.dry_run,
            since_minutes=args.since_minutes,
        )
    except KeyboardInterrupt:
        logger.info("Stopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
