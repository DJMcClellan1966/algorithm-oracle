#!/usr/bin/env python3
"""
Demo of the executable verification harness.

Shows:
  1. A correct LIS implementation passing against a brute-force reference
  2. A buggy implementation failing with concrete counter-examples
"""

from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from verification.harness import (
    run_verification_from_source,
    _LIS_CANDIDATE,
    _LIS_REFERENCE,
    _LIS_BUGGY,
)


def main():
    print("=" * 60)
    print("1. Correct O(n²) LIS vs exponential brute-force reference")
    print("=" * 60)
    report = run_verification_from_source(
        _LIS_CANDIDATE,
        _LIS_REFERENCE,
        random_n_range=(0, 8),
        num_random=20,
    )
    print(f"  status      : {report.status}")
    print(f"  message     : {report.message}")
    print(f"  passed      : {report.passed_count}")
    print(f"  random tests: {report.num_random_tests}")
    print(f"  adversarial : {report.num_adversarial_tests}")

    print()
    print("=" * 60)
    print("2. Buggy candidate (returns len(A)) — should fail")
    print("=" * 60)
    report2 = run_verification_from_source(
        _LIS_BUGGY,
        _LIS_REFERENCE,
        random_n_range=(0, 6),
        num_random=12,
    )
    print(f"  status      : {report2.status}")
    print(f"  message     : {report2.message}")
    print(f"  failures    : {len(report2.failed_cases)}")
    if report2.failed_cases:
        print("  sample failures:")
        for f in report2.failed_cases[:3]:
            print(f"    input={f.input_desc!r}")
            print(f"      expected={f.expected}  actual={f.actual}")


if __name__ == "__main__":
    main()
