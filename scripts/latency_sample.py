#!/usr/bin/env python3
"""Run one end-to-end classify() and print wall time in milliseconds.

Usage from project root::

    PYTHONPATH=. python scripts/latency_sample.py

**Methodology (PRD <200ms classification layer):** The first line includes model construction
and first inference (cold). For steady-state latency, ignore cold start: call ``classify()``
once to warm up, then time subsequent calls or use a loop and report p50/p95. PRD targets
the classification step on representative hardware after warm-up.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.ml_classifier import MLClassifier  # noqa: E402


def main() -> None:
    t_load = time.perf_counter()
    clf = MLClassifier()
    load_ms = (time.perf_counter() - t_load) * 1000

    t0 = time.perf_counter()
    team, score = clf.classify("VPN disconnects", "Remote access drops after two minutes")
    infer_ms = (time.perf_counter() - t0) * 1000

    print(f"init+first_classify total: {load_ms:.1f} ms")
    print(f"classify() only: {infer_ms:.1f} ms -> {team!r} ({score:.3f})")
    print("PRD note: target <200 ms for classification layer (measure steady-state after warm-up).")


if __name__ == "__main__":
    main()
