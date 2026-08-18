"""
Streamlit-free view helpers for Algorithm Oracle (Epic 3.1).

Pseudocode is the primary pane. Python is shown only after an explicit toggle
and only when a candidate exists.
"""

from __future__ import annotations

from typing import Optional

EXAMPLES = {
    "Longest Increasing Subsequence": (
        "Given an array of integers, return the length of the longest "
        "strictly increasing subsequence."
    ),
    "Activity selection": (
        "You are given a list of activities, each with a start time and a finish time. "
        "Select the largest possible set of activities so that no two overlap."
    ),
    "US coin change (canonical greedy)": (
        "Given US coin denominations (1, 5, 10, 25) and a target amount, "
        "find the minimum number of coins that sum to the amount."
    ),
    "Directed cycle detection": (
        "Determine whether a directed graph contains a cycle."
    ),
    "Underspecified graph (triggers gate)": (
        "Find the shortest path between two nodes in a graph."
    ),
    "Mergesort": (
        "Sort an array of n integers in O(n log n) time using a divide-and-conquer approach."
    ),
    "Koko eating bananas": (
        "Koko can eat bananas at speed k. Given piles and hours h, find the minimum "
        "integer k such that she can finish all piles in at most h hours."
    ),
    "Redundant connection (Union-Find)": (
        "You are given a list of edges added one at a time to build a graph on n nodes "
        "that started as a tree; exactly one extra edge was added, creating a single "
        "cycle. Using Union-Find, identify the redundant edge that can be removed to "
        "restore a tree."
    ),
    "Network delay time (Dijkstra)": (
        "You are given n network nodes, a list of directed weighted edges (u, v, w) "
        "representing travel times, and a starting node k. Using the shortest path "
        "from k, return the minimum time for a signal sent from node k to reach every "
        "node, or -1 if some node is unreachable."
    ),
    "Climbing stairs": (
        "You are climbing a staircase with n steps. Each time you can climb either 1 "
        "or 2 steps. Return the number of distinct ways to climb to the top."
    ),
    "N-Queens count": (
        "The n-queens puzzle asks you to place n queens on an n x n chessboard so that "
        "no two queens attack each other (same row, column, or diagonal). Return the "
        "number of distinct solutions for a given n."
    ),
    "Maximum flow": (
        "You are given a flow network: n nodes, a list of directed edges with "
        "capacities, a source node, and a sink node. Return the maximum flow that can "
        "be sent from the source to the sink."
    ),
}

DEFAULT_SHOW_PYTHON = False


def visible_code(
    *,
    pseudocode: str,
    python_candidate: Optional[str],
    show_python: bool,
) -> tuple[str, str]:
    """Return (heading, source) for the algorithm pane."""
    if show_python and python_candidate:
        return "Python implementation", python_candidate
    return "Pseudocode", pseudocode


def toggle_label(show_python: bool) -> str:
    return "Show Pseudocode" if show_python else "Show Python"


def can_toggle_python(python_candidate: Optional[str]) -> bool:
    return bool(python_candidate and "def solve" in python_candidate)
