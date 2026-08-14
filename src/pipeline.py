"""
Core orchestration for Algorithm Oracle.

Each stage returns structured Pydantic models.
Phases 1–3.5 are wired (profiler light, classifier, instantiator, verification).
Phase 4 (explainer) is still a stub.
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
    from verification.harness import run_verification_for_paradigm

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

    # Problem-specific shapes that share a paradigm id (e.g. LCS/knapsack under DP)
    notes = (algorithm.notes or "").lower()
    from verification.harness import (
        run_verification_for_paradigm,
        run_verification_from_source,
        compile_function,
        differential_test,
        VerificationReport,
        generate_random_digraph,
    )
    import random as _rnd

    if "lcs" in notes or "longest common subsequence" in notes:
        from verification.harness import compile_function, differential_test
        from schemas.models import VerificationReport, TestCaseResult
        try:
            cand = compile_function(candidate_src)
            ref = compile_function(algorithm.brute_force_reference)
        except ValueError as e:
            return VerificationReport(status="failed", message=f"Compilation error: {e}")
        inputs, descs = [], []
        for _ in range(15):
            n, m = _rnd.randint(0, 6), _rnd.randint(0, 6)
            A = [_rnd.randint(0, 4) for _ in range(n)]
            B = [_rnd.randint(0, 4) for _ in range(m)]
            inputs.append((A, B))
            descs.append(repr((A, B))[:50])
        adv = [([], []), ([1], [1]), ([1, 2, 3], [1, 3]), ([3, 2, 1], [1, 2, 3])]
        for a in adv:
            inputs.append(a)
            descs.append(repr(a))
        passed, failed = differential_test(cand, ref, inputs, descs)
        total = len(inputs)
        if failed:
            return VerificationReport(status="failed", num_random_tests=15, num_adversarial_tests=len(adv),
                                      passed_count=passed, failed_cases=failed,
                                      message=f"Failed {len(failed)} / {total} tests")
        return VerificationReport(status="passed", num_random_tests=15, num_adversarial_tests=len(adv),
                                  passed_count=passed, message=f"Passed all {total} tests (random + adversarial)")

    if "0/1 knapsack" in notes or "knapsack" in notes:
        from verification.harness import compile_function, differential_test
        from schemas.models import VerificationReport
        try:
            cand = compile_function(candidate_src)
            ref = compile_function(algorithm.brute_force_reference)
        except ValueError as e:
            return VerificationReport(status="failed", message=f"Compilation error: {e}")
        inputs, descs = [], []
        for _ in range(15):
            n = _rnd.randint(0, 5)
            weights = [_rnd.randint(1, 8) for _ in range(n)]
            values = [_rnd.randint(1, 10) for _ in range(n)]
            W = _rnd.randint(0, 15)
            inputs.append((weights, values, W))
            descs.append(f"n={n},W={W}")
        adv = [([], [], 0), ([1], [5], 0), ([2, 3], [3, 4], 5), ([5], [10], 4)]
        for a in adv:
            inputs.append(a)
            descs.append(repr(a)[:40])
        passed, failed = differential_test(cand, ref, inputs, descs)
        total = len(inputs)
        if failed:
            return VerificationReport(status="failed", num_random_tests=15, num_adversarial_tests=len(adv),
                                      passed_count=passed, failed_cases=failed,
                                      message=f"Failed {len(failed)} / {total} tests")
        return VerificationReport(status="passed", num_random_tests=15, num_adversarial_tests=len(adv),
                                  passed_count=passed, message=f"Passed all {total} tests (random + adversarial)")

    return run_verification_for_paradigm(
        candidate_src,
        algorithm.brute_force_reference,
        algorithm.paradigm_id,
        function_name=function_name,
        num_random=20,
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
# Phase 4 – explainer (stub)
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

def run_oracle(user_text: str, *, force: bool = False) -> dict:
    """
    Runs Profile → Classify → Instantiate → Verify → Explain.

    If the profiler reports missing_constraints and force=False, returns early with
    needs_clarification=True so the UI can ask the user before continuing.
    Pass force=True (or an empty missing list after the user answers) to proceed.
    """
    taxonomy = load_taxonomy_local()
    profile = profile_problem(user_text)

    if needs_clarification(profile) and not force:
        return {
            "profile": profile,
            "needs_clarification": True,
            "classification": None,
            "algorithm": None,
            "verification": None,
            "explanation": None,
        }

    classification = classify(profile, taxonomy)
    algorithm = instantiate(profile, classification)
    verification = verify(algorithm)
    explanation = explain(profile, classification, algorithm, verification)

    return {
        "profile": profile,
        "needs_clarification": False,
        "classification": classification,
        "algorithm": algorithm,
        "verification": verification,
        "explanation": explanation,
    }
