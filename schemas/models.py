"""
Pydantic models for every stage of the Algorithm Oracle pipeline.
These enforce structure and make stage outputs machine-checkable.
"""

from __future__ import annotations
from typing import List, Optional, Literal, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Phase 1 – Problem Profile
# ---------------------------------------------------------------------------

class ProblemProfile(BaseModel):
    summary: str = Field(..., description="One-sentence restatement of the core problem")
    input_type: str = Field(..., description="e.g. array, graph, string, intervals, matrix")
    size_regime: Optional[str] = Field(None, description="e.g. n <= 10^5, n <= 20, etc.")
    exact: bool = Field(True, description="Whether an exact answer is required")
    online: bool = Field(False, description="Whether the input arrives online")
    special_structure: List[str] = Field(default_factory=list, description="matroid, DAG, bipartite, monotone, ...")
    constraints_notes: Optional[str] = None
    missing_constraints: List[str] = Field(
        default_factory=list,
        description="Critical information the user still needs to supply"
    )
    ambiguities: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 2 – Classification / Paradigm Tournament
# ---------------------------------------------------------------------------

class RejectedParadigm(BaseModel):
    paradigm_id: str
    reason: str = Field(..., description="Concrete reason or small counter-example why it fails")


class ClassificationResult(BaseModel):
    primary_paradigm_id: str
    primary_paradigm_name: str
    confidence: Literal["high", "medium", "low"]
    precondition_answers: dict[str, str] = Field(
        ..., description="Answers to the checklist questions for the chosen paradigm"
    )
    rejected: List[RejectedParadigm] = Field(default_factory=list)
    ambiguities_noted: List[str] = Field(default_factory=list)
    unverified_because: Optional[str] = Field(
        None, description="If the classification itself is tentative"
    )
    rationale_summary: str = Field(..., description="Short overall justification for the ranking")


# ---------------------------------------------------------------------------
# Phase 3 – Concrete Algorithm
# ---------------------------------------------------------------------------

class ConcreteAlgorithm(BaseModel):
    paradigm_id: str
    loop_invariant_or_key_insight: str = Field(
        ..., description="Must be stated before the pseudocode"
    )
    pseudocode: str = Field(..., description="Clean, language-agnostic pseudocode")
    time_complexity: str
    space_complexity: str
    brute_force_reference: Optional[str] = Field(
        None, description="Simple correct (possibly exponential) reference implementation as Python source with def solve(...)"
    )
    python_candidate: Optional[str] = Field(
        None, description="Executable Python implementation (def solve(...)) for verification and the UI toggle"
    )
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Phase 3.5 – Verification Report
# ---------------------------------------------------------------------------

class TestCaseResult(BaseModel):
    input_desc: str
    expected: Any
    actual: Any
    passed: bool


class VerificationReport(BaseModel):
    status: Literal["passed", "failed", "outside_verifiable_range", "skipped"]
    num_random_tests: int = 0
    num_adversarial_tests: int = 0
    passed_count: int = 0
    failed_cases: List[TestCaseResult] = Field(default_factory=list)
    empirical_complexity_note: Optional[str] = None
    message: str = ""


# ---------------------------------------------------------------------------
# Phase 4 – Explanation
# ---------------------------------------------------------------------------

class Explanation(BaseModel):
    paradigm_id: str
    argument_template_used: str
    textbook_why: str = Field(..., description="Main book-style explanation")
    why_alternatives_fail: List[str] = Field(
        default_factory=list,
        description="Contrastive section pulled from Phase 2 rejections"
    )
    formal_proof_sketch: Optional[str] = Field(
        None, description="Only present when user requests higher formality"
    )
    edge_cases_discussed: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Full Oracle Response (assembled)
# ---------------------------------------------------------------------------

class OracleResponse(BaseModel):
    profile: ProblemProfile
    classification: ClassificationResult
    algorithm: ConcreteAlgorithm
    verification: VerificationReport
    explanation: Explanation
    # Real code is generated on demand / as a separate mechanical step
    python_implementation: Optional[str] = None
