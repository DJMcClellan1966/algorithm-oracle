"""
Problem-shape detection: the single source of truth classifier, instantiator,
and explainer now all defer to. Exists because those three used to maintain
independent keyword lists that had drifted apart -- the regression tests below
pin down concrete phrasings that used to fall through in one file but not
another, silently landing on a generic fallback instead of the real template.
"""

from __future__ import annotations

import pytest

from src.problem_shapes import detect_shape, SHAPE_PARADIGM


@pytest.mark.parametrize(
    "text, expected_shape",
    [
        ("You are given a list of activities, each with a start time and a finish time.", "activity"),
        ("Return the length of the longest strictly increasing subsequence.", "lis"),
        ("Determine whether a directed graph contains a cycle.", "cycle"),
        ("Return a topological ordering of the nodes.", "topo"),
        ("Sort an array using a divide-and-conquer approach.", "mergesort"),
        ("Koko can eat bananas at speed k.", "koko"),
        ("Find a pair that sums to the target.", "two_sum"),
        ("Compute the longest common subsequence of two strings.", "lcs"),
        ("0/1 knapsack: maximize value under a weight capacity.", "knapsack"),
        ("US coin denominations (1, 5, 10, 25), find the minimum count.", "coin_change"),
        ("Use Union-Find to find the redundant connection in this graph.", "redundant_connection"),
        ("Find the shortest path using Dijkstra's algorithm.", "network_delay"),
        ("You are climbing stairs and can take 1 or 2 steps at a time.", "climbing_stairs"),
    ],
)
def test_detect_shape_canonical_phrasings(text, expected_shape):
    assert detect_shape(text) == expected_shape


def test_network_delay_checked_before_cycle():
    """A shortest-path problem's phrasing can mention a directed graph too;
    the shortest-path-specific cue must win, not the generic cycle shape."""
    text = "On this directed weighted graph, find the shortest path from node k."
    assert detect_shape(text) == "network_delay"


def test_topo_checked_before_cycle():
    """Topo-sort problems also mention 'directed graph'; topo must win."""
    text = "Given a directed graph, return a topological ordering, or report a cycle exists."
    assert detect_shape(text) == "topo"


def test_redundant_connection_checked_before_cycle():
    """The redundant-connection problem's own text mentions 'cycle'; the
    union-find-specific phrasing must win, not the generic cycle shape."""
    text = "Union-Find: identify the redundant edge that creates a single cycle."
    assert detect_shape(text) == "redundant_connection"


def test_coin_change_requires_both_currency_and_canonical_cue():
    assert detect_shape("Given some coin denominations, find the minimum count.") is None
    assert detect_shape("US coin denominations, canonical system, minimum coins.") == "coin_change"


def test_no_match_returns_none():
    assert detect_shape("Compute an optimal value using dynamic programming.") is None


def test_every_shape_maps_to_a_taxonomy_paradigm():
    from src.classifier import load_taxonomy

    taxonomy = load_taxonomy()
    known_ids = {p["id"] for p in taxonomy["paradigms"]}
    for shape, paradigm_id in SHAPE_PARADIGM.items():
        assert paradigm_id in known_ids, f"{shape} maps to unknown paradigm {paradigm_id!r}"


# --- regression: phrasings that used to fall through in one file but not another ---

def test_activity_shape_matches_on_finish_time_alone():
    """explainer.py's old keyword list was missing 'finish time' (classifier/instantiator had it)."""
    assert detect_shape("Problems involving finish time ordering.") == "activity"


def test_mergesort_shape_matches_on_divide_and_conquer_without_the_word_sort():
    """explainer.py's old rule required 'sort' AND 'divide-and-conquer' together."""
    assert detect_shape("Solve this using a divide-and-conquer approach.") == "mergesort"


def test_koko_shape_matches_on_capacity_to_ship_alone():
    """explainer.py's old keyword list was missing 'capacity to ship'."""
    assert detect_shape("Find the minimum capacity to ship packages within d days.") == "koko"


def test_two_sum_shape_unifies_classifier_and_instantiator_phrasings():
    """classifier.py used 'pair that sums'; instantiator/explainer used 'sum to the target' --
    both must resolve to the same shape now."""
    assert detect_shape("Find a pair that sums to the target.") == "two_sum"
    assert detect_shape("Determine two elements whose values sum to the target.") == "two_sum"
