"""
Phase 1 – Problem Profiler

Turns free text into a structured ProblemProfile.
Flags missing_constraints so the pipeline can pause and ask the user
before classification (clarification gate).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional

from schemas.models import ProblemProfile

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


# Heuristic offline profiler – good enough for demos without an API key
def _heuristic_profile(user_text: str) -> ProblemProfile:
    text = user_text.strip()
    lower = text.lower()

    input_type = "unknown"
    if any(w in lower for w in ["interval", "activity", "start time", "finish time", "non-overlapping"]):
        input_type = "intervals"
    elif any(w in lower for w in ["graph", "node", "edge", "vertex", "directed", "undirected", "cycle"]):
        input_type = "graph"
    elif any(w in lower for w in ["string", "substring", "palindrome", "character"]):
        input_type = "string"
    elif any(w in lower for w in ["matrix", "grid", "2d"]):
        input_type = "matrix"
    elif any(w in lower for w in ["array", "list of", "subsequence", "subarray", "piles", "nums"]):
        input_type = "array"
    elif any(w in lower for w in ["integer", "number", "denominations", "coins"]):
        input_type = "numbers"

    # Size regime from common patterns
    size_regime = None
    m = re.search(r"n\s*<=?\s*10\^?(\d+)", lower)
    if m:
        size_regime = f"n <= 10^{m.group(1)}"
    elif re.search(r"n\s*<=?\s*(\d+)", lower):
        m2 = re.search(r"n\s*<=?\s*(\d+)", lower)
        size_regime = f"n <= {m2.group(1)}"

    special: List[str] = []
    if "directed" in lower:
        special.append("directed")
    if "undirected" in lower:
        special.append("undirected")
    if "dag" in lower or "acyclic" in lower:
        special.append("DAG")
    if "bipartite" in lower:
        special.append("bipartite")
    if "sorted" in lower:
        special.append("sorted")
    if "monotone" in lower or "monotonic" in lower:
        special.append("monotone")
    if "tree" in lower:
        special.append("tree")

    missing: List[str] = []
    ambiguities: List[str] = []

    # Clarification heuristics – only when they really affect the paradigm
    if input_type == "graph":
        if "directed" not in lower and "undirected" not in lower:
            missing.append("Is the graph directed or undirected?")
        if any(w in lower for w in ["shortest", "path", "distance", "weight"]) and "weight" not in lower and "unweighted" not in lower:
            missing.append("Are edges weighted? Non-negative only?")
    if input_type == "intervals" and "start" not in lower and "finish" not in lower and "end" not in lower:
        missing.append("Are intervals given as (start, finish) pairs?")
    if "approximate" in lower or "approx" in lower:
        ambiguities.append("Exact vs approximate solution requirement is unclear.")
    if not size_regime and any(w in lower for w in ["efficient", "large n", "optimize"]):
        missing.append("What is the expected input size bound (n)?")

    exact = "approximat" not in lower
    online = any(w in lower for w in ["online", "stream", "arriving"])

    # Prefer a full short summary (up to ~500 chars) so downstream matchers see keywords
    summary = text[:500].strip()
    if not summary.endswith("."):
        summary += "."

    return ProblemProfile(
        summary=summary[:600],
        input_type=input_type,
        size_regime=size_regime,
        exact=exact,
        online=online,
        special_structure=special,
        constraints_notes=None,
        missing_constraints=missing,
        ambiguities=ambiguities,
    )


def _llm_profile(user_text: str, model: str = "gpt-4o") -> ProblemProfile:
    import instructor
    from openai import OpenAI

    system = (PROMPTS_DIR / "profiler_system.txt").read_text(encoding="utf-8")
    client = instructor.from_openai(OpenAI())
    return client.chat.completions.create(
        model=model,
        response_model=ProblemProfile,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Problem statement:\n\n{user_text.strip()}"},
        ],
        temperature=0.1,
    )


def profile_problem(
    user_text: str,
    *,
    model: str = "gpt-4o",
    use_mock_if_no_key: bool = True,
) -> ProblemProfile:
    """
    Main entry point for Phase 1.
    Prefer LLM when OPENAI_API_KEY is set; otherwise heuristic offline profiler.
    """
    if not user_text or not user_text.strip():
        return ProblemProfile(
            summary="(empty problem statement)",
            input_type="unknown",
            exact=True,
            online=False,
            missing_constraints=["A non-empty problem description is required."],
        )

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            return _llm_profile(user_text, model=model)
        except Exception as e:
            if not use_mock_if_no_key:
                raise
            print(f"[profiler] LLM call failed ({e}); falling back to heuristic")

    return _heuristic_profile(user_text)


def needs_clarification(profile: ProblemProfile, *, max_missing: int = 0) -> bool:
    """
    Clarification gate: True if the pipeline should pause and ask the user
    before proceeding to classification.
    """
    return len(profile.missing_constraints) > max_missing
