"""
Epic 2.5: explainer uses a named argument template and contrastive rejections.
Problem-specific why text must not be reused across unmatched problems.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from schemas.models import ClassificationResult, RejectedParadigm, VerificationReport
from src.explainer import explain
from src.instantiator import instantiate
from src.profiler import profile_problem

EXAMPLES_PATH = ROOT / "examples" / "test_problems.json"

# example_id -> (argument_template_used, distinctive why fragment)
EXPLAINER_EXPECTATIONS = {
    "activity_selection": ("exchange_argument", "earliest"),
    "lis": ("subproblem_recurrence", "dp[i]"),
    "directed_cycle": ("invariant_or_coloring", "gray"),
    "merge_sort": ("master_theorem_or_induction", "induction"),
    "binary_search_answer": ("monotonicity", "monotonic"),
    "two_sum_sorted": ("invariant_maintenance", "sort"),
    "lcs": ("subproblem_recurrence", "dp[i][j]"),
    "knapsack_01": ("subproblem_recurrence", "include or exclude"),
    "topo_sort": ("invariant_or_coloring", "in-degree"),
}


@pytest.fixture(autouse=True)
def offline_explainer(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def _examples():
    with open(EXAMPLES_PATH, encoding="utf-8") as f:
        return json.load(f)


def _by_id():
    return {e["id"]: e for e in _examples()}


def _classification(paradigm_id: str) -> ClassificationResult:
    return ClassificationResult(
        primary_paradigm_id=paradigm_id,
        primary_paradigm_name=paradigm_id,
        confidence="medium",
        precondition_answers={"test": "yes"},
        rejected=[
            RejectedParadigm(paradigm_id="greedy_exchange", reason="No safe greedy choice."),
            RejectedParadigm(paradigm_id="math_formula", reason="No closed form."),
        ],
        rationale_summary="2.5 explainer test",
    )


def _passed_report() -> VerificationReport:
    return VerificationReport(
        status="passed",
        num_random_tests=4,
        num_adversarial_tests=2,
        passed_count=6,
        message="Passed all 6 tests (random + adversarial)",
    )


def _explain_example(example: dict):
    profile = profile_problem(example["problem"])
    classification = _classification(example["expected_paradigm_id"])
    algorithm = instantiate(profile, classification)
    return explain(profile, classification, algorithm, _passed_report())


@pytest.mark.parametrize("example_id, expected", EXPLAINER_EXPECTATIONS.items())
def test_known_explainer_uses_template_and_rejections(example_id, expected):
    template_name, why_marker = expected
    example = _by_id()[example_id]
    explanation = _explain_example(example)
    assert explanation.paradigm_id == example["expected_paradigm_id"]
    assert explanation.argument_template_used == template_name
    assert why_marker.lower() in explanation.textbook_why.lower()
    assert explanation.why_alternatives_fail
    assert any("greedy_exchange" in line for line in explanation.why_alternatives_fail)
    assert any("math_formula" in line for line in explanation.why_alternatives_fail)
    assert "No specialized explanation template" not in explanation.textbook_why


def test_coin_change_does_not_reuse_activity_explanation():
    example = _by_id()["coin_change_canonical"]
    explanation = _explain_example(example)
    assert explanation.paradigm_id == "greedy_exchange"
    assert explanation.argument_template_used == "exchange_argument"
    assert explanation.why_alternatives_fail
    why = explanation.textbook_why.lower()
    assert "earliest" not in why
    assert "activity" not in why
    assert "no specialized explanation template" in why


def test_topo_does_not_reuse_cycle_coloring_explanation():
    explanation = _explain_example(_by_id()["topo_sort"])
    why = explanation.textbook_why.lower()
    assert "in-degree" in why
    assert "gray" not in why


def test_paradigm_id_tracks_classification_not_hardcoded_template():
    """Explanation.paradigm_id must come from the classifier's decision, not a
    literal baked into whichever template matched on keywords -- these can
    disagree (e.g. a real LLM classifier vs. this file's own keyword matcher).
    Deliberately inject a paradigm the activity template does not itself assume.
    """
    example = _by_id()["activity_selection"]
    profile = profile_problem(example["problem"])
    classification = _classification("binary_search")
    algorithm = instantiate(profile, classification)
    explanation = explain(profile, classification, algorithm, _passed_report())
    assert explanation.paradigm_id == "binary_search"
    assert explanation.argument_template_used == "monotonicity"


def test_paradigm_alone_does_not_select_lis_explanation():
    profile = profile_problem("Compute an optimal value using dynamic programming.")
    classification = _classification("dp_optimal_substructure")
    algorithm = instantiate(profile, classification)
    explanation = explain(profile, classification, algorithm, _passed_report())
    why = explanation.textbook_why.lower()
    assert "longest increasing" not in why
    assert explanation.why_alternatives_fail
