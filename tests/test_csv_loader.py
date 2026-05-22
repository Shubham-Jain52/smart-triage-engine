"""Tests for CSV historical ticket loader."""

from pathlib import Path

from src.integrations.csv_loader import default_dummy_csv_path, load_tickets_from_csv


def test_default_dummy_csv_loads():
    path = default_dummy_csv_path()
    assert path.is_file()
    tickets = load_tickets_from_csv(path)
    assert len(tickets) >= 10
    assert tickets[0].ticket_id.startswith("DEMO-")


def test_load_custom_csv(tmp_path: Path):
    csv_file = tmp_path / "tickets.csv"
    csv_file.write_text(
        "ticket_id,title,description,resolution_text,team,resolved_at\n"
        "T-1,Test title,Test desc,Fixed it,DevOps,2026-01-01T00:00:00Z\n",
        encoding="utf-8",
    )
    tickets = load_tickets_from_csv(csv_file)
    assert len(tickets) == 1
    assert tickets[0].ticket_id == "T-1"
    assert tickets[0].team == "DevOps"
