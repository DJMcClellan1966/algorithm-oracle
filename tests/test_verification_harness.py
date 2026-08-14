"""
Epic 1.4–1.7: LIS pass/fail, named generators, and paradigm routing.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pytest

from verification.harness import (
    _LIS_BUGGY,
    _LIS_CANDIDATE,
    _LIS_REFERENCE,
    generate_adversarial_arrays,
    generate_adversarial_digraphs,
    generate_adversarial_intervals,
    generate_adversarial_koko,
    generate_adversarial_pairs,
    generate_random_digraph,
    generate_random_intervals,
    generate_random_koko,
    generate_random_pairs,
    run_verification_for_paradigm,
    run_verification_from_source,
)

_IDENTITY_SOLVE = """
def solve(x):
    return x
"""


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


def test_interval_generators_have_valid_shapes():
    random.seed(1)
    for n in range(0, 9):
        intervals = generate_random_intervals(n)
        assert len(intervals) == n
        for start, finish in intervals:
            assert start < finish
    adv = generate_adversarial_intervals()
    descs = {c["desc"] for c in adv}
    assert {"empty", "single", "all overlap"} <= descs
    assert next(c["input"] for c in adv if c["desc"] == "empty") == []
    assert next(c["input"] for c in adv if c["desc"] == "single") == [(0, 5)]


def test_digraph_generators_have_valid_shapes():
    random.seed(1)
    for n in range(0, 6):
        graph = generate_random_digraph(n)
        assert set(graph) == set(range(n))
        for neighbors in graph.values():
            assert all(v in graph for v in neighbors)
    adv = generate_adversarial_digraphs()
    by_desc = {c["desc"]: c["input"] for c in adv}
    assert by_desc["empty"] == {}
    assert by_desc["self-loop"] == {0: [0]}
    assert by_desc["triangle cycle"] == {0: [1], 1: [2], 2: [0]}
    assert by_desc["simple DAG"] == {0: [1], 1: [2], 2: []}


def test_koko_generators_have_valid_shapes():
    random.seed(1)
    for n_piles in range(1, 6):
        piles, h = generate_random_koko(n_piles)
        assert len(piles) == n_piles
        assert all(p >= 1 for p in piles)
        assert h >= len(piles)
    adv = generate_adversarial_koko()
    descs = {c["desc"] for c in adv}
    assert {"single pile", "tight h", "generous h"} <= descs


def test_pair_generators_have_valid_shapes():
    random.seed(1)
    for n in range(0, 11):
        A, target = generate_random_pairs(n)
        assert isinstance(A, list)
        assert len(A) == n
        assert isinstance(target, int)
    adv = generate_adversarial_pairs()
    by_desc = {c["desc"]: c["input"] for c in adv}
    assert by_desc["empty"] == ([], 0)
    assert by_desc["pair hit"] == ([1, 4, 7], 5)
    assert by_desc["pair miss"] == ([1, 4, 7], 100)
    assert by_desc["negatives"] == ([-3, -1, 2], -4)


@pytest.mark.parametrize(
    "paradigm_id, adversarial_fn",
    [
        ("greedy_exchange", generate_adversarial_intervals),
        ("graph_traversal", generate_adversarial_digraphs),
        ("binary_search", generate_adversarial_koko),
        ("two_pointers_sliding", generate_adversarial_pairs),
    ],
)
def test_paradigm_runner_uses_named_generators(paradigm_id, adversarial_fn):
    """Runner adversarial count must match the named generator (fails if disconnected)."""
    random.seed(1)
    report = run_verification_for_paradigm(
        _IDENTITY_SOLVE,
        _IDENTITY_SOLVE,
        paradigm_id,
        num_random=5,
    )
    assert report.num_random_tests == 5
    assert report.num_adversarial_tests == len(adversarial_fn())
    assert report.status == "passed", report.message


def test_paradigm_adversarial_counts_are_distinct():
    """Routing tests only bite if each family has a unique adversarial size."""
    counts = [
        len(generate_adversarial_intervals()),
        len(generate_adversarial_digraphs()),
        len(generate_adversarial_koko()),
        len(generate_adversarial_pairs()),
        len(generate_adversarial_arrays()),
    ]
    assert len(set(counts)) == len(counts)


@pytest.mark.parametrize(
    "paradigm_id, adversarial_fn",
    [
        ("greedy_exchange", generate_adversarial_intervals),
        ("graph_traversal", generate_adversarial_digraphs),
        ("binary_search", generate_adversarial_koko),
        ("two_pointers_sliding", generate_adversarial_pairs),
        ("dp_optimal_substructure", generate_adversarial_arrays),
        ("divide_and_conquer", generate_adversarial_arrays),
        ("not_a_real_paradigm", generate_adversarial_arrays),
    ],
)
def test_paradigm_runner_routes_by_paradigm_id(paradigm_id, adversarial_fn):
    """1.7 — runner selects generators from paradigm_id, including the default array path."""
    random.seed(1)
    report = run_verification_for_paradigm(
        _IDENTITY_SOLVE,
        _IDENTITY_SOLVE,
        paradigm_id,
        num_random=5,
    )
    assert report.num_random_tests == 5
    assert report.num_adversarial_tests == len(adversarial_fn()), (
        f"{paradigm_id} routed to {report.num_adversarial_tests} adversarial cases, "
        f"expected {len(adversarial_fn())} from {adversarial_fn.__name__}"
    )
    assert report.status == "passed", report.message
