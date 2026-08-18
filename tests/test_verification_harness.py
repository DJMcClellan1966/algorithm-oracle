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
    generate_adversarial_knapsacks,
    generate_adversarial_koko,
    generate_adversarial_lcs_pairs,
    generate_adversarial_pairs,
    generate_adversarial_flow_networks,
    generate_adversarial_queens_counts,
    generate_adversarial_stair_counts,
    generate_adversarial_tree_plus_edge,
    generate_adversarial_weighted_digraphs,
    generate_random_digraph,
    generate_random_flow_network,
    generate_random_intervals,
    generate_random_knapsack,
    generate_random_koko,
    generate_random_lcs_pair,
    generate_random_pairs,
    generate_random_queens_count,
    generate_random_stair_count,
    generate_random_tree_plus_edge,
    generate_random_weighted_digraph,
    run_verification_for_paradigm,
    run_verification_for_shape,
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


def test_tree_plus_edge_generators_have_valid_shapes():
    random.seed(1)
    for n in range(1, 9):
        edges = generate_random_tree_plus_edge(n)
        nodes = {u for e in edges for u in e}
        assert len(edges) == max(3, n)
        assert len(nodes) == max(3, n)
    adv = generate_adversarial_tree_plus_edge()
    descs = {c["desc"] for c in adv}
    assert {"minimal triangle", "chain closed into a loop", "star plus one shortcut edge"} <= descs


def test_stair_count_generators_have_valid_shapes():
    random.seed(1)
    for _ in range(20):
        n = generate_random_stair_count()
        assert 0 <= n <= 12
    adv = generate_adversarial_stair_counts()
    by_desc = {c["desc"]: c["input"] for c in adv}
    assert by_desc["zero steps"] == 0
    assert by_desc["one step"] == 1


def test_queens_count_generators_have_valid_shapes():
    random.seed(1)
    for _ in range(15):
        n = generate_random_queens_count()
        assert 0 <= n <= 7
    adv = generate_adversarial_queens_counts()
    by_desc = {c["desc"]: c["input"] for c in adv}
    assert by_desc["n=2, provably no solution"] == 2


def test_flow_network_generators_have_valid_shapes():
    random.seed(1)
    for n in range(1, 8):
        num_nodes, edges, s, t = generate_random_flow_network(n)
        assert num_nodes == max(2, n)
        assert s == 1 and t == num_nodes
        for u, v, cap in edges:
            assert 1 <= u <= num_nodes and 1 <= v <= num_nodes
            assert u != v
            assert cap >= 1
    adv = generate_adversarial_flow_networks()
    by_desc = {c["desc"]: c["input"] for c in adv}
    assert by_desc["no edges"] == (2, [], 1, 2)
    assert by_desc["source equals sink"] == (1, [], 1, 1)


def test_lcs_pair_generators_have_valid_shapes():
    random.seed(1)
    for _ in range(20):
        A, B = generate_random_lcs_pair()
        assert isinstance(A, list) and isinstance(B, list)
        assert len(A) <= 6 and len(B) <= 6
    adv = generate_adversarial_lcs_pairs()
    by_desc = {c["desc"]: c["input"] for c in adv}
    assert by_desc["both empty"] == ([], [])
    assert by_desc["partial overlap"] == ([1, 2, 3], [1, 3])


def test_knapsack_generators_have_valid_shapes():
    random.seed(1)
    for _ in range(20):
        weights, values, W = generate_random_knapsack()
        assert len(weights) == len(values)
        assert all(w >= 1 for w in weights)
        assert W >= 0
    adv = generate_adversarial_knapsacks()
    by_desc = {c["desc"]: c["input"] for c in adv}
    assert by_desc["no items"] == ([], [], 0)
    assert by_desc["item heavier than capacity"] == ([5], [10], 4)


def test_run_verification_for_shape_routes_lcs_and_knapsack():
    """These share dp_optimal_substructure's paradigm_id with plain-array DP,
    so they must route by shape, not fall through to the generic array path."""
    random.seed(1)
    lcs_report = run_verification_for_shape(
        _IDENTITY_SOLVE, _IDENTITY_SOLVE, "lcs", "dp_optimal_substructure", num_random=5
    )
    assert lcs_report.num_random_tests == 5
    assert lcs_report.num_adversarial_tests == len(generate_adversarial_lcs_pairs())
    assert lcs_report.status == "passed"

    knapsack_report = run_verification_for_shape(
        _IDENTITY_SOLVE, _IDENTITY_SOLVE, "knapsack", "dp_optimal_substructure", num_random=5
    )
    assert knapsack_report.num_random_tests == 5
    assert knapsack_report.num_adversarial_tests == len(generate_adversarial_knapsacks())
    assert knapsack_report.status == "passed"


def test_run_verification_for_shape_falls_back_to_paradigm_routing():
    """A shape with no special case (including None, e.g. plain LIS) must
    fall through to run_verification_for_paradigm unchanged."""
    random.seed(1)
    report = run_verification_for_shape(
        _IDENTITY_SOLVE, _IDENTITY_SOLVE, None, "dp_optimal_substructure", num_random=5
    )
    assert report.num_adversarial_tests == len(generate_adversarial_arrays())
    assert report.status == "passed"


def test_weighted_digraph_generators_have_valid_shapes():
    random.seed(1)
    for n in range(1, 7):
        num_nodes, times, k = generate_random_weighted_digraph(n)
        assert num_nodes == max(1, n)
        assert 1 <= k <= num_nodes
        for u, v, w in times:
            assert 1 <= u <= num_nodes and 1 <= v <= num_nodes
            assert u != v
            assert w >= 1
    adv = generate_adversarial_weighted_digraphs()
    by_desc = {c["desc"]: c["input"] for c in adv}
    assert by_desc["single node"] == (1, [], 1)
    assert by_desc["unreachable node"] == (3, [(1, 2, 5)], 1)


@pytest.mark.parametrize(
    "paradigm_id, adversarial_fn",
    [
        ("greedy_exchange", generate_adversarial_intervals),
        ("graph_traversal", generate_adversarial_digraphs),
        ("binary_search", generate_adversarial_koko),
        ("two_pointers_sliding", generate_adversarial_pairs),
        ("union_find", generate_adversarial_tree_plus_edge),
        ("shortest_path", generate_adversarial_weighted_digraphs),
        ("math_formula", generate_adversarial_stair_counts),
        ("backtracking", generate_adversarial_queens_counts),
        ("network_flow", generate_adversarial_flow_networks),
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
        len(generate_adversarial_tree_plus_edge()),
        len(generate_adversarial_weighted_digraphs()),
        len(generate_adversarial_stair_counts()),
        len(generate_adversarial_queens_counts()),
        len(generate_adversarial_flow_networks()),
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
        ("union_find", generate_adversarial_tree_plus_edge),
        ("shortest_path", generate_adversarial_weighted_digraphs),
        ("math_formula", generate_adversarial_stair_counts),
        ("backtracking", generate_adversarial_queens_counts),
        ("network_flow", generate_adversarial_flow_networks),
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
