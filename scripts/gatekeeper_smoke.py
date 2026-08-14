#!/usr/bin/env python3
"""Pipeline smoke used by run_checks.sh / run_checks.ps1."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import run_oracle

PROBLEM = (
    "Given an array of integers, return the length of the longest "
    "strictly increasing subsequence."
)


def main() -> None:
    result = run_oracle(PROBLEM)
    assert result.get("needs_clarification") is False
    assert result.get("classification") is not None
    assert result["classification"].primary_paradigm_id == "dp_optimal_substructure"
    assert result["verification"].status == "passed", result["verification"].message
    print(
        "pipeline smoke ok:",
        result["classification"].primary_paradigm_id,
        result["verification"].status,
    )


if __name__ == "__main__":
    main()
