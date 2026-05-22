"""Load historical tickets from CSV for Phase 5 ingest without Jira."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import List, Optional

from src.integrations.jira.client import HistoricalTicket

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"ticket_id", "title", "description", "resolution_text"}
OPTIONAL_COLUMNS = {"team", "resolved_at"}


def load_tickets_from_csv(path: Path) -> List[HistoricalTicket]:
    """Read historical tickets from a CSV file."""
    if not path.is_file():
        raise FileNotFoundError(f"CSV not found: {path}")

    tickets: List[HistoricalTicket] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header row: {path}")
        missing = REQUIRED_COLUMNS - {h.strip() for h in reader.fieldnames if h}
        if missing:
            raise ValueError(f"CSV missing columns {missing}: {path}")

        for row_num, row in enumerate(reader, start=2):
            ticket_id = (row.get("ticket_id") or "").strip()
            title = (row.get("title") or "").strip()
            description = (row.get("description") or "").strip()
            if not ticket_id:
                logger.warning("Skipping row %s: empty ticket_id", row_num)
                continue
            if not title and not description:
                logger.warning("Skipping row %s: empty title and description", row_num)
                continue

            tickets.append(
                HistoricalTicket(
                    ticket_id=ticket_id,
                    title=title,
                    description=description,
                    resolution_text=(row.get("resolution_text") or "").strip(),
                    team=(row.get("team") or "").strip(),
                    resolved_at=(row.get("resolved_at") or "").strip() or "1970-01-01T00:00:00Z",
                )
            )

    logger.info("Loaded %s tickets from %s", len(tickets), path)
    return tickets


def default_dummy_csv_path() -> Path:
    """Bundled sample data for local development without Jira."""
    return Path(__file__).resolve().parents[1] / "data" / "historical_tickets.csv"
