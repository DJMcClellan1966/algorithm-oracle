"""
Single source of truth for "what classic-problem shape does this text describe."

The classifier, instantiator, and explainer each used to maintain their own
keyword list for the same set of canonical problems. The lists had drifted
apart: some phrasings correctly identified a paradigm but then matched no
instantiator/explainer template, silently falling back to a generic stub
instead of the classic template that should have applied. This module is the
one place that keyword-to-shape mapping lives; callers still decide what text
to feed it and what to do with the shape they get back.
"""

from __future__ import annotations

from typing import Optional

# Order matters only where one shape's keywords are a subset of another's
# context (topo-sort problems also mention "directed graph", so topo must be
# checked before the more general cycle-detection shape).
_SHAPES: list[tuple[str, tuple[str, ...]]] = [
    ("topo", ("topological", "topo sort", "topo-sort")),
    ("cycle", ("cycle", "directed graph", "detect cycle")),
    ("activity", ("activity", "activities", "interval", "intervals", "non-overlapping", "finish time")),
    ("lis", ("longest increasing", "lis", "increasing subsequence")),
    ("lcs", ("longest common subsequence", "lcs")),
    ("knapsack", ("knapsack", "0/1", "capacity w")),
    ("two_sum", ("two sum", "two-sum", "pair sum", "pair that sums", "two pointers", "two elements sum", "sum to the target")),
    ("koko", ("koko", "eating bananas", "speed k", "minimum integer k", "capacity to ship")),
    ("mergesort", ("merge sort", "mergesort", "divide-and-conquer", "divide and conquer")),
]

# coin_change needs both a currency cue and a canonical-system cue -- kept
# separate from _SHAPES since it's a compound (AND) rule, not a plain OR list.
_COIN_CHANGE_KEYWORDS = ("coin", "denominations")
_COIN_CHANGE_CANONICAL_CUES = ("us ", "1, 5, 10, 25", "canonical")

# Paradigm each shape belongs to -- used by the classifier's offline mock.
SHAPE_PARADIGM = {
    "topo": "graph_traversal",
    "cycle": "graph_traversal",
    "activity": "greedy_exchange",
    "lis": "dp_optimal_substructure",
    "lcs": "dp_optimal_substructure",
    "knapsack": "dp_optimal_substructure",
    "two_sum": "two_pointers_sliding",
    "koko": "binary_search",
    "mergesort": "divide_and_conquer",
    "coin_change": "greedy_exchange",
}


def detect_shape(text: str) -> Optional[str]:
    """Return the canonical shape id for a text blob, or None if nothing matches."""
    lower = text.lower()

    for shape_id, keywords in _SHAPES:
        if any(w in lower for w in keywords):
            return shape_id

    if any(w in lower for w in _COIN_CHANGE_KEYWORDS) and any(
        w in lower for w in _COIN_CHANGE_CANONICAL_CUES
    ):
        return "coin_change"

    return None
