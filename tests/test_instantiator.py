"""
Epic 2.4: instantiator templates emit candidate + reference for known problems.
Unmatched problems must stub, not silently reuse another template.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from schemas.models import ClassificationResult, ConcreteAlgorithm
from src.instantiator import _strip_code_fence, instantiate
from src.pipeline import verify
from src.problem_shapes import detect_shape
from src.profiler import profile_problem
from verification.harness import generate_adversarial_lcs_pairs

EXAMPLES_PATH = ROOT / "examples" / "test_problems.json"

# Labeled problems that have a dedicated offline template.
TEMPLATE_MARKERS = {
    "coin_change_canonical": "canonical US coin change",
    "activity_selection": "activity selection",
    "lis": "Classic LIS",
    "directed_cycle": "cycle detection",
    "merge_sort": "mergesort",
    "binary_search_answer": "Koko",
    "two_sum_sorted": "Two-sum",
    "lcs": "Longest Common Subsequence",
    "knapsack_01": "0/1 knapsack",
    "topo_sort": "topological sort",
    "redundant_connection": "Union-Find",
    "network_delay": "Dijkstra",
    "climbing_stairs": "Climbing Stairs",
    "n_queens_count": "N-Queens",
    "max_flow": "Edmonds-Karp",
}


@pytest.fixture(autouse=True)
def offline_instantiator(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)


def _examples():
    with open(EXAMPLES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _by_id():
    return {e["id"]: e for e in _examples()}


def _classify(paradigm_id: str) -> ClassificationResult:
    return ClassificationResult(
        primary_paradigm_id=paradigm_id,
        primary_paradigm_name=paradigm_id,
        confidence="medium",
        precondition_answers={"test": "yes"},
        rationale_summary="2.4 instantiator test",
    )


def _instantiate_example(example: dict):
    profile = profile_problem(example["problem"])
    return instantiate(profile, _classify(example["expected_paradigm_id"]))


@pytest.mark.parametrize("example_id, marker", TEMPLATE_MARKERS.items())
def test_known_template_emits_candidate_and_reference(example_id, marker):
    example = _by_id()[example_id]
    algo = _instantiate_example(example)
    assert algo.paradigm_id == example["expected_paradigm_id"]
    assert algo.loop_invariant_or_key_insight
    assert "No template matched" not in algo.loop_invariant_or_key_insight
    assert algo.python_candidate and "def solve" in algo.python_candidate
    assert algo.brute_force_reference and "def solve" in algo.brute_force_reference
    assert marker.lower() in (algo.notes or "").lower()


@pytest.mark.parametrize("example_id", TEMPLATE_MARKERS.keys())
def test_every_template_candidate_actually_verifies(example_id):
    """Structural checks (has 'def solve', right notes marker) are not enough --
    a candidate can look right and still crash the moment it's actually run
    (e.g. topo_sort's old candidate/reference both used `import`, which the
    sandbox's restricted builtins deliberately reject). Run every real
    template through the real verification harness, not a stand-in."""
    example = _by_id()[example_id]
    algo = _instantiate_example(example)
    report = verify(algo)
    assert report.status == "passed", f"[{example_id}] {report.message}"


def test_redundant_connection_candidate_verifies_against_reference():
    """The real union-find candidate must differentially pass against the
    brute-force reachability reference, not just have matching structure."""
    example = _by_id()["redundant_connection"]
    algo = _instantiate_example(example)
    report = verify(algo)
    assert report.status == "passed", report.message


def test_strip_code_fence_removes_python_tagged_fence():
    fenced = "```python\ndef solve(x):\n    return x\n```"
    assert _strip_code_fence(fenced) == "def solve(x):\n    return x"


def test_strip_code_fence_removes_bare_fence():
    fenced = "```\ndef solve(x):\n    return x\n```"
    assert _strip_code_fence(fenced) == "def solve(x):\n    return x"


def test_strip_code_fence_leaves_unfenced_code_untouched():
    bare = "def solve(x):\n    return x"
    assert _strip_code_fence(bare) == bare


def test_strip_code_fence_passes_through_none():
    assert _strip_code_fence(None) is None


def test_coin_change_does_not_reuse_activity_template():
    example = _by_id()["coin_change_canonical"]
    algo = _instantiate_example(example)
    assert algo.paradigm_id == "greedy_exchange"
    assert algo.shape == "coin_change"
    assert algo.python_candidate and "def solve" in algo.python_candidate
    notes = (algo.notes or "").lower()
    assert "activity" not in notes
    assert "interval" not in notes
    assert "canonical" in notes
    report = verify(algo)
    assert report.status == "passed", report.message


def test_paradigm_alone_does_not_select_a_default_problem():
    """A generic DP statement must not silently become LIS."""
    profile = profile_problem("Compute an optimal value using dynamic programming.")
    algo = instantiate(profile, _classify("dp_optimal_substructure"))
    assert algo.python_candidate is None
    assert algo.brute_force_reference is None
    assert "LIS" not in (algo.notes or "")


@pytest.mark.parametrize("example_id", TEMPLATE_MARKERS.keys())
def test_known_template_records_shape(example_id):
    example = _by_id()[example_id]
    algo = _instantiate_example(example)
    assert algo.shape == detect_shape(example["problem"])
    assert algo.shape is not None
    assert algo.source == "template"


def test_verify_uses_persisted_shape_when_notes_have_no_keywords():
    """verify() used to re-parse algorithm.notes; LLM-style notes must not
    send LCS down the generic array generator."""
    example = _by_id()["lcs"]
    algo = _instantiate_example(example)
    algo.notes = "generic efficient implementation"
    assert detect_shape(algo.notes or "") is None
    assert algo.shape == "lcs"
    report = verify(algo)
    assert report.status == "passed", report.message
    assert report.num_adversarial_tests == len(generate_adversarial_lcs_pairs())


def test_templated_shape_does_not_call_llm(monkeypatch):
    monkeypatch.setattr("src.llm_client.has_llm_backend", lambda: True)

    def boom(*_a, **_k):
        raise AssertionError("LLM must not run for a templated shape")

    monkeypatch.setattr("src.instantiator._llm_instantiate", boom)
    example = _by_id()["lis"]
    algo = _instantiate_example(example)
    assert "Classic LIS" in (algo.notes or "")
    assert algo.shape == "lis"


def test_unmatched_problem_calls_llm_when_backend_present(monkeypatch):
    called = {}

    def fake(profile, classification, model="gpt-4o"):
        called["yes"] = True
        return ConcreteAlgorithm(
            paradigm_id=classification.primary_paradigm_id,
            loop_invariant_or_key_insight="from llm",
            pseudocode="pass",
            time_complexity="unknown",
            space_complexity="unknown",
            notes="from llm",
        )

    monkeypatch.setattr("src.llm_client.has_llm_backend", lambda: True)
    monkeypatch.setattr("src.instantiator._llm_instantiate", fake)
    profile = profile_problem("Compute an optimal value using dynamic programming.")
    algo = instantiate(profile, _classify("dp_optimal_substructure"))
    assert called.get("yes")
    assert algo.loop_invariant_or_key_insight == "from llm"
