"""
Epic 1.4 / 1.5: verification harness must accept a correct LIS and reject a buggy one.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from verification.harness import (
    _LIS_BUGGY,
    _LIS_CANDIDATE,
    _LIS_REFERENCE,
    run_verification_from_source,
)


def test_correct_lis_passes_against_brute_force():
    """1.4 — correct toy LIS vs reference reports status passed."""
    random.seed(1)
    report = run_verification_from_source(
        _LIS_CANDIDATE,
        _LIS_REFERENCE,
        random_n_range=(0, 8),
        num_random=20,
    )
    assert report.status == "passed", report.message
    assert report.failed_cases == []
    assert report.passed_count == report.num_random_tests + report.num_adversarial_tests
    assert report.passed_count > 0


def test_buggy_lis_fails_with_counter_example():
    """1.5 — buggy toy LIS vs reference reports failed plus a concrete case."""
    random.seed(1)
    report = run_verification_from_source(
        _LIS_BUGGY,
        _LIS_REFERENCE,
        random_n_range=(0, 6),
        num_random=15,
    )
    assert report.status == "failed", report.message
    assert len(report.failed_cases) >= 1

    case = report.failed_cases[0]
    assert case.passed is False
    assert case.input_desc
    assert case.expected != case.actual
