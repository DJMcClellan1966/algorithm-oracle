"""
Core orchestration for Algorithm Oracle.

Each stage returns structured Pydantic models. All phases are fully wired --
profiler, classifier, instantiator, verification, and explainer -- across
all 11 taxonomy paradigms.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

import yaml

from schemas.models import (
    ProblemProfile,
    ClassificationResult,
    ConcreteAlgorithm,
    VerificationReport,
    Explanation,
    OracleResponse,
)
from src.classifier import classify as classify_impl

TAXONOMY_PATH = Path(__file__).parent.parent / "taxonomy" / "paradigms.yaml"


def load_taxonomy_local() -> dict:
    with open(TAXONOMY_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Phase 1 – profiler + clarification gate
# ---------------------------------------------------------------------------

def profile_problem(user_text: str) -> ProblemProfile:
    """Structured profile; may populate missing_constraints for the clarification gate."""
    from src.profiler import profile_problem as profile_impl
    return profile_impl(user_text)


def needs_clarification(profile: ProblemProfile) -> bool:
    from src.profiler import needs_clarification as nc
    return nc(profile)


# ---------------------------------------------------------------------------
# Phase 2 – classifier
# ---------------------------------------------------------------------------

def classify(profile: ProblemProfile, taxonomy: Optional[dict] = None) -> ClassificationResult:
    return classify_impl(profile, taxonomy)


# ---------------------------------------------------------------------------
# Phase 3 – instantiator
# ---------------------------------------------------------------------------

def instantiate(profile: ProblemProfile, classification: ClassificationResult) -> ConcreteAlgorithm:
    """Invariant → pseudocode + brute-force reference + python candidate."""
    from src.instantiator import instantiate as instantiate_impl
    return instantiate_impl(profile, classification)


# ---------------------------------------------------------------------------
# Phase 3.5 – verification
# ---------------------------------------------------------------------------

def verify(algorithm: ConcreteAlgorithm, *, function_name: str = "solve") -> VerificationReport:
    """Differential testing using python_candidate vs brute_force_reference."""
    if not algorithm.brute_force_reference:
        return VerificationReport(
            status="outside_verifiable_range",
            message="No brute-force reference supplied — cannot differentially test.",
        )

    candidate_src = algorithm.python_candidate
    if not candidate_src or "def solve" not in candidate_src:
        return VerificationReport(
            status="skipped",
            message="No executable candidate source available (python_candidate missing).",
        )

    from src.problem_shapes import detect_shape
    from verification.harness import run_verification_for_shape

    shape = algorithm.shape or detect_shape(algorithm.notes or "")
    return run_verification_for_shape(
        candidate_src,
        algorithm.brute_force_reference,
        shape,
        algorithm.paradigm_id,
        function_name=function_name,
        num_random=15 if shape in ("lcs", "knapsack", "coin_change") else 20,
    )


def verify_sources(
    candidate_source: str,
    reference_source: str,
    *,
    function_name: str = "solve",
    **kwargs,
) -> VerificationReport:
    from verification.harness import run_verification_from_source
    return run_verification_from_source(
        candidate_source, reference_source, function_name=function_name, **kwargs
    )


# ---------------------------------------------------------------------------
# Phase 4 – explainer
# ---------------------------------------------------------------------------

def explain(
    profile: ProblemProfile,
    classification: ClassificationResult,
    algorithm: ConcreteAlgorithm,
    verification: VerificationReport,
) -> Explanation:
    """Phase 4: Template-constrained textbook explanation."""
    from src.explainer import explain as explain_impl
    return explain_impl(profile, classification, algorithm, verification)


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def run_oracle(user_text: str, *, force: bool = False) -> OracleResponse:
    """
    Runs Profile → Classify → Instantiate → Verify → Explain.

    If the profiler reports missing_constraints and force=False, returns early with
    needs_clarification=True so the UI can ask the user before continuing.
    Pass force=True (or an empty missing list after the user answers) to proceed.
    """
    taxonomy = load_taxonomy_local()
    profile = profile_problem(user_text)

    if needs_clarification(profile) and not force:
        return OracleResponse(
            profile=profile,
            needs_clarification=True,
            source_path="gated",
        )

    classification = classify(profile, taxonomy)
    algorithm = instantiate(profile, classification)
    verification = verify(algorithm)
    explanation = explain(profile, classification, algorithm, verification)

    return OracleResponse(
        profile=profile,
        needs_clarification=False,
        classification=classification,
        algorithm=algorithm,
        verification=verification,
        explanation=explanation,
        source_path=algorithm.source or "stub",
    )
