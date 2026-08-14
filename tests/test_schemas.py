"""
Epic 2.1: Pydantic stage models import and survive JSON round-trip.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from schemas import models as schema_models

STAGE_MODELS = (
    schema_models.ProblemProfile,
    schema_models.RejectedParadigm,
    schema_models.ClassificationResult,
    schema_models.ConcreteAlgorithm,
    schema_models.TestCaseResult,
    schema_models.VerificationReport,
    schema_models.Explanation,
    schema_models.OracleResponse,
)


def _profile() -> schema_models.ProblemProfile:
    return schema_models.ProblemProfile(
        summary="Find the length of the longest increasing subsequence.",
        input_type="array",
        size_regime="n <= 10^3",
        exact=True,
        online=False,
        special_structure=["sorted"],
        constraints_notes="strictly increasing",
        missing_constraints=[],
        ambiguities=[],
    )


def _classification() -> schema_models.ClassificationResult:
    return schema_models.ClassificationResult(
        primary_paradigm_id="dp_optimal_substructure",
        primary_paradigm_name="Dynamic Programming",
        confidence="medium",
        precondition_answers={"overlapping subproblems": "yes"},
        rejected=[
            schema_models.RejectedParadigm(
                paradigm_id="greedy_exchange",
                reason="Greedy next-larger fails on classic counter-examples.",
            )
        ],
        ambiguities_noted=[],
        unverified_because="heuristic classifier",
        rationale_summary="Overlapping prefixes require DP.",
    )


def _algorithm() -> schema_models.ConcreteAlgorithm:
    return schema_models.ConcreteAlgorithm(
        paradigm_id="dp_optimal_substructure",
        loop_invariant_or_key_insight="dp[i] is LIS ending at i.",
        pseudocode="dp[i] = 1 + max of earlier smaller endings",
        time_complexity="O(n^2)",
        space_complexity="O(n)",
        brute_force_reference="def solve(A): ...",
        python_candidate="def solve(A): ...",
        notes="LIS length",
    )


def _verification() -> schema_models.VerificationReport:
    return schema_models.VerificationReport(
        status="failed",
        num_random_tests=10,
        num_adversarial_tests=2,
        passed_count=11,
        failed_cases=[
            schema_models.TestCaseResult(
                input_desc="[3, 1, 2]",
                expected=2,
                actual=3,
                passed=False,
            )
        ],
        empirical_complexity_note=None,
        message="Failed 1 / 12 tests",
    )


def _explanation() -> schema_models.Explanation:
    return schema_models.Explanation(
        paradigm_id="dp_optimal_substructure",
        argument_template_used="subproblem_recurrence",
        textbook_why="Optimal substructure with overlapping prefixes.",
        why_alternatives_fail=["greedy_exchange: classic counter-example"],
        formal_proof_sketch=None,
        edge_cases_discussed=["empty array -> 0"],
    )


def _oracle_response() -> schema_models.OracleResponse:
    return schema_models.OracleResponse(
        profile=_profile(),
        classification=_classification(),
        algorithm=_algorithm(),
        verification=_verification(),
        explanation=_explanation(),
        python_implementation="def solve(A): return 0",
    )


SAMPLES = {
    schema_models.ProblemProfile: _profile,
    schema_models.RejectedParadigm: lambda: schema_models.RejectedParadigm(
        paradigm_id="greedy_exchange", reason="No exchange argument."
    ),
    schema_models.ClassificationResult: _classification,
    schema_models.ConcreteAlgorithm: _algorithm,
    schema_models.TestCaseResult: lambda: schema_models.TestCaseResult(
        input_desc="[]", expected=0, actual=0, passed=True
    ),
    schema_models.VerificationReport: _verification,
    schema_models.Explanation: _explanation,
    schema_models.OracleResponse: _oracle_response,
}


def test_all_stage_models_import():
    assert all(issubclass(m, object) and m.__name__ for m in STAGE_MODELS)
    assert {m.__name__ for m in STAGE_MODELS} == {
        "ProblemProfile",
        "RejectedParadigm",
        "ClassificationResult",
        "ConcreteAlgorithm",
        "TestCaseResult",
        "VerificationReport",
        "Explanation",
        "OracleResponse",
    }


@pytest.mark.parametrize("model", STAGE_MODELS, ids=lambda m: m.__name__)
def test_model_json_round_trip(model):
    original = SAMPLES[model]()
    payload = original.model_dump_json()
    restored = model.model_validate_json(payload)
    assert json.loads(payload) == restored.model_dump(mode="json")
    assert restored == original


def test_classification_rejects_invalid_confidence():
    data = _classification().model_dump()
    data["confidence"] = "maybe"
    with pytest.raises(ValidationError):
        schema_models.ClassificationResult.model_validate(data)


def test_verification_rejects_invalid_status():
    data = _verification().model_dump()
    data["status"] = "ok"
    with pytest.raises(ValidationError):
        schema_models.VerificationReport.model_validate(data)


def test_profile_requires_summary_and_input_type():
    with pytest.raises(ValidationError):
        schema_models.ProblemProfile()
