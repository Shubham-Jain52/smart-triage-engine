#!/usr/bin/env python3
"""Evaluate routing accuracy against a labeled CSV (PRD >= 85% target).

Expected columns: ``title``, ``description``, ``expected_team`` (optional ``ticket_id``).

Uses the same ``MLClassifier`` and environment (``CANDIDATE_LABELS``, ``ZS_MODEL_NAME``) as the API.

Usage from project root::

    PYTHONPATH=. python scripts/evaluate_accuracy.py
    PYTHONPATH=. python scripts/evaluate_accuracy.py path/to/custom.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.ml_classifier import MLClassifier  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate triage accuracy on a labeled CSV.")
    parser.add_argument(
        "csv_path",
        nargs="?",
        default=str(ROOT / "src/data/validation_set.csv"),
        help="Path to CSV with title, description, expected_team",
    )
    args = parser.parse_args()
    path = Path(args.csv_path)
    if not path.is_file():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    clf = MLClassifier()
    total = 0
    correct = 0
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = (row.get("title") or "").strip()
            description = (row.get("description") or "").strip()
            expected = (row.get("expected_team") or "").strip()
            if not title and not description:
                continue
            pred, score = clf.classify(title, description)
            total += 1
            ok = pred.strip() == expected
            if ok:
                correct += 1
            mark = "OK" if ok else "XX"
            tid = row.get("ticket_id") or f"row{total}"
            print(f"{mark} {tid}: expected={expected!r} pred={pred!r} score={score:.3f}")

    if total == 0:
        print("No rows evaluated.", file=sys.stderr)
        sys.exit(1)
    acc = correct / total
    print(f"\nAccuracy: {correct}/{total} = {acc:.1%} (PRD target >= 85%)")


if __name__ == "__main__":
    main()
