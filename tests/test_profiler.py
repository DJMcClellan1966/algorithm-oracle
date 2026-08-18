"""
Epic 2.2: profiler + clarification gate.
Underspecified graphs must pause the pipeline before classification.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.pipeline import run_oracle
from src.profiler import needs_clarification, profile_problem

UNDER_SPECIFIED_GRAPH = "Find the shortest path between two nodes in a graph."
SPECIFIED_CYCLE = "Determine whether a directed graph contains a cycle."
SPECIFIED_LIS = (
    "Given an array of integers, return the length of the longest "
    "strictly increasing subsequence."
)


@pytest.fixture(autouse=True)
def offline_profiler(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)


def test_underspecified_graph_profile_flags_missing_constraints():
    profile = profile_problem(UNDER_SPECIFIED_GRAPH)
    assert profile.input_type == "graph"
    assert needs_clarification(profile)
    missing = " ".join(profile.missing_constraints).lower()
    assert "directed" in missing or "undirected" in missing
    assert "weight" in missing


def test_underspecified_graph_gates_run_oracle():
    result = run_oracle(UNDER_SPECIFIED_GRAPH)
    assert result["needs_clarification"] is True
    assert result["classification"] is None
    assert result["algorithm"] is None
    assert result["verification"] is None
    assert result["explanation"] is None
    assert result["profile"].missing_constraints


def test_specified_directed_cycle_does_not_gate():
    profile = profile_problem(SPECIFIED_CYCLE)
    assert profile.input_type == "graph"
    assert "directed" in profile.special_structure
    assert needs_clarification(profile) is False
    result = run_oracle(SPECIFIED_CYCLE)
    assert result["needs_clarification"] is False
    assert result["classification"] is not None


def test_specified_array_problem_does_not_gate():
    profile = profile_problem(SPECIFIED_LIS)
    assert profile.input_type == "array"
    assert needs_clarification(profile) is False


def test_empty_problem_requires_clarification():
    profile = profile_problem("   ")
    assert needs_clarification(profile)
    assert profile.missing_constraints
    result = run_oracle("")
    assert result["needs_clarification"] is True
    assert result["classification"] is None
