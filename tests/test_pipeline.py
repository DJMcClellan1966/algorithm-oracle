"""
Epic 2.6: run_oracle returns a full stage dict; force=True bypasses the gate.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from schemas.models import (
    ClassificationResult,
    ConcreteAlgorithm,
    Explanation,
    ProblemProfile,
    VerificationReport,
)
from src.pipeline import run_oracle

FULL_KEYS = {
    "profile",
    "needs_clarification",
    "classification",
    "algorithm",
    "verification",
    "explanation",
}

UNDER_SPECIFIED_GRAPH = "Find the shortest path between two nodes in a graph."

END_TO_END = [
    (
        "Given an array of integers, return the length of the longest "
        "strictly increasing subsequence.",
        "dp_optimal_substructure",
        "passed",
    ),
    (
        "You are given a list of activities, each with a start time and a finish time. "
        "Select the largest possible set of activities so that no two overlap.",
        "greedy_exchange",
        "passed",
    ),
    (
        "Determine whether a directed graph contains a cycle.",
        "graph_traversal",
        "passed",
    ),
]


@pytest.fixture(autouse=True)
def offline_pipeline(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def _assert_full_dict(result: dict, *, gated: bool) -> None:
    assert set(result) == FULL_KEYS
    assert isinstance(result["profile"], ProblemProfile)
    if gated:
        assert result["needs_clarification"] is True
        assert result["classification"] is None
        assert result["algorithm"] is None
        assert result["verification"] is None
        assert result["explanation"] is None
        return
    assert result["needs_clarification"] is False
    assert isinstance(result["classification"], ClassificationResult)
    assert isinstance(result["algorithm"], ConcreteAlgorithm)
    assert isinstance(result["verification"], VerificationReport)
    assert isinstance(result["explanation"], Explanation)


@pytest.mark.parametrize("problem, paradigm_id, verify_status", END_TO_END)
def test_run_oracle_full_dict_end_to_end(problem, paradigm_id, verify_status):
    result = run_oracle(problem)
    _assert_full_dict(result, gated=False)
    assert result["classification"].primary_paradigm_id == paradigm_id
    assert result["algorithm"].python_candidate and "def solve" in result["algorithm"].python_candidate
    assert result["algorithm"].brute_force_reference and "def solve" in result["algorithm"].brute_force_reference
    assert result["verification"].status == verify_status
    assert result["explanation"].argument_template_used
    assert result["explanation"].why_alternatives_fail


def test_force_true_bypasses_clarification_gate():
    gated = run_oracle(UNDER_SPECIFIED_GRAPH, force=False)
    _assert_full_dict(gated, gated=True)

    forced = run_oracle(UNDER_SPECIFIED_GRAPH, force=True)
    _assert_full_dict(forced, gated=False)
    assert forced["profile"].missing_constraints
    assert forced["classification"] is not None
    assert forced["verification"].status in {
        "passed",
        "failed",
        "outside_verifiable_range",
        "skipped",
    }


def test_unmatched_problem_does_not_claim_passed():
    result = run_oracle(
        "Given US coin denominations (1, 5, 10, 25) and a target amount, "
        "find the minimum number of coins that sum to the amount."
    )
    _assert_full_dict(result, gated=False)
    assert result["classification"].primary_paradigm_id == "greedy_exchange"
    assert result["algorithm"].python_candidate is None
    assert result["verification"].status == "outside_verifiable_range"
