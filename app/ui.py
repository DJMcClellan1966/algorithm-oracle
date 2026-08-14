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
