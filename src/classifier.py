"""
Phase 2 – Paradigm Classifier / Tournament

Takes a ProblemProfile (or raw text) + taxonomy and returns a ClassificationResult
with ranked primary choice, explicit rejections, precondition answers, and uncertainty fields.

Uses instructor + OpenAI-compatible client for structured output.
Falls back to a deterministic mock when no API key is present (useful for testing structure).
"""

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Optional

import yaml
from pydantic import ValidationError

from schemas.models import ProblemProfile, ClassificationResult, RejectedParadigm
from src.problem_shapes import detect_shape, SHAPE_PARADIGM

TAXONOMY_PATH = Path(__file__).parent.parent / "taxonomy" / "paradigms.yaml"
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_taxonomy() -> dict:
    with open(TAXONOMY_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_taxonomy_prompt_section(taxonomy: dict) -> str:
    """Render the taxonomy into a compact, checklist-focused text block for the LLM."""
    lines = ["Available paradigms (you MUST choose from these ids):\n"]
    for p in taxonomy.get("paradigms", []):
        lines.append(f"### {p['id']} — {p['name']}")
        lines.append(p.get("description", "").strip())
        lines.append("Precondition checklist (answer each before claiming this paradigm):")
        for q in p.get("precondition_checklist", []):
            lines.append(f"  - {q}")
        lines.append(f"Canonical examples: {', '.join(p.get('canonical_problems', []))}")
        lines.append("")
    return "\n".join(lines)


def build_classifier_prompt(profile: ProblemProfile, taxonomy: dict) -> str:
    system = (PROMPTS_DIR / "classifier_system.txt").read_text(encoding="utf-8")

    taxonomy_text = build_taxonomy_prompt_section(taxonomy)

    user = f"""Problem profile (JSON):
{profile.model_dump_json(indent=2)}

{taxonomy_text}

Produce a ClassificationResult.
- primary_paradigm_id must be one of the ids above.
- Answer every precondition question for the chosen paradigm in precondition_answers.
- Provide at least two rejected paradigms with concrete reasons.
- Fill confidence, ambiguities_noted, and unverified_because (use null only if truly none).
"""
    return system, user


_SHAPE_DETAILS: dict[str, dict] = {
    "redundant_connection": {
        "rejected": [
            RejectedParadigm(paradigm_id="graph_traversal", reason="No full DFS/BFS traversal or ordering is needed; only whether two nodes are already connected."),
            RejectedParadigm(paradigm_id="dp_optimal_substructure", reason="No overlapping subproblems; each edge is processed once with near-constant-time set operations."),
        ],
        "answers": {
            "track connected components under unions": "Yes – exactly what Union-Find maintains as edges are added.",
            "online or offline": "Online – edges are processed one at a time in the given order.",
        },
    },
    "activity": {
        "rejected": [
            RejectedParadigm(paradigm_id="dp_optimal_substructure", reason="No overlapping subproblems; greedy choice property holds via exchange argument."),
            RejectedParadigm(paradigm_id="graph_traversal", reason="The input is a set of intervals, not an explicit graph."),
        ],
        "answers": {
            "greedy choice property": "Yes – earliest finish time can always be part of an optimal solution.",
            "exchange argument": "Yes – any optimal solution that starts later can swap in the earliest-finishing activity.",
        },
    },
    "lis": {
        "rejected": [
            RejectedParadigm(paradigm_id="greedy_exchange", reason="Greedy (e.g. always take next larger) fails; classic counter-examples exist."),
            RejectedParadigm(paradigm_id="divide_and_conquer", reason="Subproblems overlap heavily; memoization/DP is required."),
        ],
        "answers": {
            "overlapping subproblems": "Yes – many prefixes share the same best ending values.",
            "optimal substructure": "Yes – LIS ending at i is built from earlier LIS endings.",
        },
    },
    "cycle": {
        "rejected": [
            RejectedParadigm(paradigm_id="union_find", reason="Union-Find is for undirected connectivity; directed cycles need DFS coloring or similar."),
            RejectedParadigm(paradigm_id="shortest_path", reason="We only need existence of a cycle, not distances."),
        ],
        "answers": {
            "graph structure": "Yes – explicit directed graph.",
            "need reachability/ordering": "Yes – back edges to the recursion stack detect cycles.",
        },
    },
    "coin_change": {
        "rejected": [
            RejectedParadigm(
                paradigm_id="dp_optimal_substructure",
                reason="For the canonical US denominations the greedy choice property holds; DP is unnecessary.",
            ),
            RejectedParadigm(
                paradigm_id="math_formula",
                reason="Still requires a selection process, not a closed formula.",
            ),
        ],
        "answers": {
            "greedy choice property": "Yes – for canonical coin systems the largest feasible coin is always safe.",
            "exchange argument": "Yes – standard for canonical denominations.",
        },
    },
    "mergesort": {
        "rejected": [
            RejectedParadigm(
                paradigm_id="dp_optimal_substructure",
                reason="Subproblems are independent; no overlapping subproblems that need memoization.",
            ),
            RejectedParadigm(
                paradigm_id="greedy_exchange",
                reason="Sorting requires global ordering, not a local greedy choice.",
            ),
        ],
        "answers": {
            "independent subproblems": "Yes – left and right halves are independent.",
            "combine step": "Yes – the merge step combines sorted halves.",
        },
    },
    "koko": {
        "rejected": [
            RejectedParadigm(
                paradigm_id="dp_optimal_substructure",
                reason="The feasibility predicate is monotonic in k; binary search on the answer is sufficient and faster.",
            ),
            RejectedParadigm(
                paradigm_id="greedy_exchange",
                reason="We are searching for a threshold, not making a sequence of irreversible greedy choices.",
            ),
        ],
        "answers": {
            "monotonic property": "Yes – if speed k works, any larger speed also works.",
            "search on answer": "Yes – classic binary search on the answer space.",
        },
    },
    "two_sum": {
        "rejected": [
            RejectedParadigm(paradigm_id="dp_optimal_substructure", reason="Sorted two-pointer scan is enough; no overlapping subproblems need a table."),
            RejectedParadigm(paradigm_id="binary_search", reason="We need a pair, not a threshold search on a monotonic predicate alone."),
        ],
        "answers": {"window/pair invariant": "Yes – sorted array allows monotonic two-pointer movement."},
    },
    "lcs": {
        "rejected": [
            RejectedParadigm(paradigm_id="greedy_exchange", reason="Greedy character matching fails on classic LCS counter-examples."),
            RejectedParadigm(paradigm_id="two_pointers_sliding", reason="LCS is not a contiguous window problem."),
        ],
        "answers": {"overlapping subproblems": "Yes – shared prefixes of both strings."},
    },
    "knapsack": {
        "rejected": [
            RejectedParadigm(paradigm_id="greedy_exchange", reason="0/1 knapsack is not fractional; greedy by density can be suboptimal."),
            RejectedParadigm(paradigm_id="math_formula", reason="No closed form for general weights/values."),
        ],
        "answers": {"optimal substructure": "Yes – include/exclude last item recurrence."},
    },
    "topo": {
        "rejected": [
            RejectedParadigm(paradigm_id="union_find", reason="Union-Find does not produce a linear order of dependencies."),
            RejectedParadigm(paradigm_id="shortest_path", reason="We need a valid order, not distances."),
        ],
        "answers": {"graph structure": "Yes – directed dependency graph."},
    },
}


def _mock_classify(profile: ProblemProfile, taxonomy: dict) -> ClassificationResult:
    """
    Deterministic fallback used when no API key is available.
    Simple keyword heuristics so the rest of the pipeline can be exercised.
    """
    text = profile.summary + " " + profile.input_type
    shape = detect_shape(text)
    details = _SHAPE_DETAILS.get(shape)

    if details is not None:
        primary = SHAPE_PARADIGM[shape]
        rejected = details["rejected"]
        answers = details["answers"]
    else:
        primary = "dp_optimal_substructure"
        rejected = [
            RejectedParadigm(
                paradigm_id="greedy_exchange",
                reason="No clear greedy choice property identified from the profile.",
            ),
            RejectedParadigm(
                paradigm_id="divide_and_conquer",
                reason="Likely overlapping subproblems.",
            ),
        ]
        answers = {"note": "Fallback heuristic – real LLM required for reliable classification."}

    # Look up display name
    name = primary
    for p in taxonomy.get("paradigms", []):
        if p["id"] == primary:
            name = p["name"]
            break

    return ClassificationResult(
        primary_paradigm_id=primary,
        primary_paradigm_name=name,
        confidence="medium" if "Fallback" not in str(answers) else "low",
        precondition_answers=answers,
        rejected=rejected,
        ambiguities_noted=profile.ambiguities or [],
        unverified_because="Mock classifier (no API key) – replace with real LLM call for production.",
        rationale_summary=f"Heuristic match on keywords → {primary}",
    )


def classify(
    profile: ProblemProfile,
    taxonomy: Optional[dict] = None,
    *,
    model: str = "gpt-4o",
    use_mock_if_no_key: bool = True,
) -> ClassificationResult:
    """
    Main entry point for Phase 2.

    If OPENAI_API_KEY (or compatible) is set, uses instructor for structured output.
    Otherwise falls back to the mock classifier so the rest of the system remains testable.
    """
    if taxonomy is None:
        taxonomy = load_taxonomy()

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key and use_mock_if_no_key:
        return _mock_classify(profile, taxonomy)

    # Real structured call via instructor
    try:
        import instructor
        from openai import OpenAI

        client = instructor.from_openai(OpenAI())
        system, user = build_classifier_prompt(profile, taxonomy)

        result = client.chat.completions.create(
            model=model,
            response_model=ClassificationResult,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.1,  # low temperature for classification consistency
        )
        return result
    except Exception as e:
        if use_mock_if_no_key:
            print(f"[classifier] LLM call failed ({e}); falling back to mock")
            return _mock_classify(profile, taxonomy)
        raise


# ---------------------------------------------------------------------------
# Convenience: classify from raw text (runs a minimal profiler first)
# ---------------------------------------------------------------------------

def classify_from_text(problem_text: str, **kwargs) -> ClassificationResult:
    """Quick path when you only have free text. Builds a minimal profile."""
    profile = ProblemProfile(
        summary=problem_text.strip()[:500],
        input_type="unknown",
        exact=True,
        online=False,
        special_structure=[],
        missing_constraints=[],
        ambiguities=[],
    )
    return classify(profile, **kwargs)


if __name__ == "__main__":
    # Smoke test with the mock path
    examples = [
        "Given a list of activities with start and finish times, select the maximum number of non-overlapping activities.",
        "Find the length of the longest strictly increasing subsequence in an array.",
        "Determine whether a directed graph contains a cycle.",
    ]
    tax = load_taxonomy()
    for ex in examples:
        print("=" * 60)
        print(ex)
        result = classify_from_text(ex)
        print(result.model_dump_json(indent=2))
