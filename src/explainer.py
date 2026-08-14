"""
Phase 4 – Explanation Synthesizer

Produces a textbook-style “why” constrained by the paradigm’s argument template,
plus a contrastive section drawn from Phase 2 rejections.

Only intended to run after verification (or an explicit outside-verifiable-range status).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml

from schemas.models import (
    ProblemProfile,
    ClassificationResult,
    ConcreteAlgorithm,
    VerificationReport,
    Explanation,
)

TAXONOMY_PATH = Path(__file__).parent.parent / "taxonomy" / "paradigms.yaml"
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_taxonomy() -> dict:
    with open(TAXONOMY_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _argument_template_key(paradigm_id: str, taxonomy: dict) -> str:
    for p in taxonomy.get("paradigms", []):
        if p["id"] == paradigm_id:
            return p.get("argument_template") or "general_correctness"
    return "general_correctness"


def _argument_template_for(paradigm_id: str, taxonomy: dict) -> str:
    key = _argument_template_key(paradigm_id, taxonomy)
    templates = taxonomy.get("argument_templates", {})
    return templates.get(key, key)


def _contrastive_from_rejections(classification: ClassificationResult) -> list[str]:
    lines = []
    for r in classification.rejected:
        lines.append(f"{r.paradigm_id}: {r.reason}")
    return lines


def _verification_note(verification: VerificationReport) -> str:
    if verification.status == "passed":
        return (
            f"The candidate implementation was differentially tested against a brute-force "
            f"reference and passed {verification.passed_count} tests "
            f"({verification.num_random_tests} random + {verification.num_adversarial_tests} adversarial)."
        )
    if verification.status == "failed":
        return (
            f"Verification failed on {len(verification.failed_cases)} cases. "
            f"The explanation below describes the intended argument; treat correctness as provisional."
        )
    if verification.status == "outside_verifiable_range":
        return (
            "Automatic differential testing was not applicable for this input shape "
            f"({verification.message}). The argument below is structural, not empirically checked here."
        )
    return verification.message or ""


# ---------------------------------------------------------------------------
# Hand-written textbook explanations (offline templates)
# ---------------------------------------------------------------------------

def _explain_activity(
    profile: ProblemProfile,
    classification: ClassificationResult,
    algorithm: ConcreteAlgorithm,
    verification: VerificationReport,
) -> Explanation:
    why = """\
The key insight is that it is always safe to select the activity that finishes earliest.

Consider any optimal solution. If its first activity is not the earliest-finishing one, replace that first activity with the earliest-finishing activity. The new set remains feasible (the earliest-finishing activity ends no later than the original first activity) and has the same size, so it is still optimal. After making this choice, the remaining problem is an identical smaller instance on the activities that start after the chosen finish time. By induction the greedy algorithm is optimal.

Sorting by finish time is essential. Sorting by start time or duration can produce suboptimal selections.
"""
    edges = [
        "Empty input → empty selection.",
        "Single activity → select it.",
        "All activities overlap → select the one that finishes earliest.",
    ]
    return Explanation(
        paradigm_id="greedy_exchange",
        argument_template_used="exchange_argument",
        textbook_why=why.strip() + "\n\n" + _verification_note(verification),
        why_alternatives_fail=_contrastive_from_rejections(classification),
        formal_proof_sketch=None,
        edge_cases_discussed=edges,
    )


def _explain_lis(
    profile: ProblemProfile,
    classification: ClassificationResult,
    algorithm: ConcreteAlgorithm,
    verification: VerificationReport,
) -> Explanation:
    why = """\
Define dp[i] as the length of the longest increasing subsequence that ends at index i.

Any increasing subsequence ending at i must be formed by extending a previously computed increasing subsequence that ends with a value strictly smaller than A[i]. Therefore:

  dp[i] = 1 + max{ dp[j] : j < i and A[j] < A[i] },
  or 1 if no such j exists.

Base case: every single element is an increasing subsequence of length 1, so dp[i] starts at 1. The dependencies form a DAG ordered by index: when we process i, every j < i is already solved. The global answer is the maximum value in dp, because every increasing subsequence ends at some index.

This is optimal substructure with overlapping subproblems; a pure divide-and-conquer approach without memoization would recompute the same prefixes repeatedly.
"""
    edges = [
        "Empty array → 0.",
        "Strictly decreasing array → 1.",
        "Strictly increasing array → n.",
        "Duplicates: strict inequality means equal elements do not extend the subsequence.",
    ]
    return Explanation(
        paradigm_id="dp_optimal_substructure",
        argument_template_used="subproblem_recurrence",
        textbook_why=why.strip() + "\n\n" + _verification_note(verification),
        why_alternatives_fail=_contrastive_from_rejections(classification),
        formal_proof_sketch=None,
        edge_cases_discussed=edges,
    )


def _explain_cycle(
    profile: ProblemProfile,
    classification: ClassificationResult,
    algorithm: ConcreteAlgorithm,
    verification: VerificationReport,
) -> Explanation:
    why = """\
Maintain a three-coloring of the nodes during depth-first search:
  white = unvisited, gray = on the current recursion stack, black = finished.

Invariant: the gray nodes always form a simple path from the root of the current DFS tree to the node being expanded. Consequently, an edge from the current node to a gray node is a back edge that closes a directed cycle.

Initialization: all nodes are white, so the invariant holds vacuously. Each step either paints a node gray when it is entered (extending the path) or black when it is finished (removing it from the path). If a back edge to a gray node is ever found, a cycle exists. If the search completes with no such edge, every reachable edge was examined and none closed a cycle, so the graph is acyclic.

Union-Find is the wrong tool here: it tracks undirected connectivity and cannot distinguish the directed back edges that define directed cycles.
"""
    edges = [
        "Empty graph or single node → no cycle.",
        "Self-loop → cycle.",
        "Mutual edges u→v, v→u → cycle.",
        "DAG with long paths → no cycle.",
    ]
    return Explanation(
        paradigm_id="graph_traversal",
        argument_template_used="invariant_or_coloring",
        textbook_why=why.strip() + "\n\n" + _verification_note(verification),
        why_alternatives_fail=_contrastive_from_rejections(classification),
        formal_proof_sketch=None,
        edge_cases_discussed=edges,
    )


def _explain_mergesort(
    profile: ProblemProfile,
    classification: ClassificationResult,
    algorithm: ConcreteAlgorithm,
    verification: VerificationReport,
) -> Explanation:
    why = """\
Mergesort divides the array into two halves, sorts each half recursively, then merges the two sorted halves into one sorted array.

Correctness follows by strong induction on n. Base case: n ≤ 1, the array is already sorted. Inductive step: the two recursive calls return sorted halves (induction hypothesis). The merge step always appends the smaller of the two heads, so the output is sorted and contains exactly the elements of the two halves. Therefore the whole array is sorted.

The recurrence is T(n) = 2T(n/2) + O(n), which solves to O(n log n) by the Master Theorem (case 2). Subproblems are independent (no overlapping subproblems), so dynamic programming is unnecessary.
"""
    edges = [
        "Empty or single-element array → already sorted.",
        "Already sorted input → still O(n log n), stable merge preserves order.",
        "Reverse-sorted input → same asymptotic cost.",
    ]
    return Explanation(
        paradigm_id="divide_and_conquer",
        argument_template_used="master_theorem_or_induction",
        textbook_why=why.strip() + "\n\n" + _verification_note(verification),
        why_alternatives_fail=_contrastive_from_rejections(classification),
        formal_proof_sketch=None,
        edge_cases_discussed=edges,
    )


def _explain_binary_search_answer(
    profile: ProblemProfile,
    classification: ClassificationResult,
    algorithm: ConcreteAlgorithm,
    verification: VerificationReport,
) -> Explanation:
    why = """\
The feasibility predicate P(k) = “speed k finishes all piles within h hours” is monotonic: if P(k) is true then P(k′) is true for every k′ ≥ k. Therefore the minimum feasible k can be found by binary search on the answer space.

Invariant: the minimum feasible speed always lies in the closed interval [lo, hi]. If mid is feasible, the minimum is at most mid, so the search continues on [lo, mid]. If mid is not feasible, the minimum is at least mid+1, so the search continues on [mid+1, hi]. When lo = hi the interval is a single feasible value — the answer.

A linear scan from k = 1 upward is also correct but slower; dynamic programming is unnecessary because the decision space is totally ordered by the monotonic predicate.
"""
    edges = [
        "Empty piles → 0.",
        "h large enough for k = 1 → answer 1.",
        "h equal to number of piles and max pile size forces k = max(piles).",
    ]
    return Explanation(
        paradigm_id="binary_search",
        argument_template_used="monotonicity",
        textbook_why=why.strip() + "\n\n" + _verification_note(verification),
        why_alternatives_fail=_contrastive_from_rejections(classification),
        formal_proof_sketch=None,
        edge_cases_discussed=edges,
    )



def _explain_two_sum(profile, classification, algorithm, verification):
    why = """After sorting, place two indices at the ends of the array. If their sum is too small, every pair that still uses the left index with a smaller right index is even smaller, so the left index must move right. If the sum is too large, the right index must move left. Each step discards an index that cannot participate in a solution with the remaining side, so a missed pair is impossible if one exists.

A nested double loop is correct but slower; dynamic programming is unnecessary for existence of a pair with a given sum once sorting is allowed."""
    return Explanation(
        paradigm_id="two_pointers_sliding",
        argument_template_used="invariant_maintenance",
        textbook_why=why.strip() + "\n\n" + _verification_note(verification),
        why_alternatives_fail=_contrastive_from_rejections(classification),
        edge_cases_discussed=["Empty or single-element array → false.", "Target requiring the same element twice is rejected when indices must be distinct."],
    )


def _explain_lcs(profile, classification, algorithm, verification):
    why = """Define dp[i][j] as the LCS length of prefixes A[0..i) and B[0..j). If A[i-1] == B[j-1], both characters are taken and the answer is 1 + dp[i-1][j-1]. Otherwise the answer is the better of dropping the last character of A or of B. Base cases are empty prefixes (length 0). Every cell depends only on strictly smaller prefixes, so a row-by-row fill is valid. The answer is dp[n][m].

Greedy left-to-right matching fails on standard counter-examples; two pointers alone cannot jump over choices that must be reconsidered."""
    return Explanation(
        paradigm_id="dp_optimal_substructure",
        argument_template_used="subproblem_recurrence",
        textbook_why=why.strip() + "\n\n" + _verification_note(verification),
        why_alternatives_fail=_contrastive_from_rejections(classification),
        edge_cases_discussed=["Either string empty → 0.", "Identical strings → n.", "No characters in common → 0."],
    )


def _explain_knapsack(profile, classification, algorithm, verification):
    why = """For each item decide include or exclude. dp[w] after processing an item is the best value for capacity w. Updating the one-dimensional table from high capacity to low ensures each item is used at most once. Optimal substructure: an optimal pack either excludes the item or includes it on top of an optimal pack for the residual capacity.

Greedy by value/weight density is optimal for fractional knapsack but not for 0/1."""
    return Explanation(
        paradigm_id="dp_optimal_substructure",
        argument_template_used="subproblem_recurrence",
        textbook_why=why.strip() + "\n\n" + _verification_note(verification),
        why_alternatives_fail=_contrastive_from_rejections(classification),
        edge_cases_discussed=["W = 0 → 0.", "All items heavier than W → 0.", "Single item that fits → its value."],
    )


def _explain_topo(profile, classification, algorithm, verification):
    why = """Kahn's algorithm maintains the in-degree of every remaining node. Nodes in the queue have in-degree 0 relative to the residual graph, so every predecessor has already been emitted. Emitting a node subtracts one from each successor's in-degree and may unlock that successor. If a directed cycle exists, at least one node never reaches in-degree 0, so fewer than |V| nodes are emitted.

DFS three-coloring also works for cycle detection, but Union-Find cannot produce a linear order of directed dependencies."""
    return Explanation(
        paradigm_id="graph_traversal",
        argument_template_used="invariant_or_coloring",
        textbook_why=why.strip() + "\n\n" + _verification_note(verification),
        why_alternatives_fail=_contrastive_from_rejections(classification),
        edge_cases_discussed=[
            "Empty graph → empty order.",
            "Single node → that node.",
            "A cycle → None (fewer than |V| nodes emitted).",
        ],
    )


def _match_explainer(
    profile: ProblemProfile,
    classification: ClassificationResult,
    algorithm: ConcreteAlgorithm,
    verification: VerificationReport,
) -> Optional[Explanation]:
    text = profile.summary.lower()
    if any(w in text for w in ["activity", "activities", "interval", "intervals", "non-overlapping"]):
        return _explain_activity(profile, classification, algorithm, verification)
    if any(w in text for w in ["longest increasing", "lis", "increasing subsequence"]):
        return _explain_lis(profile, classification, algorithm, verification)
    if any(w in text for w in ["topological", "topo sort", "topo-sort"]):
        return _explain_topo(profile, classification, algorithm, verification)
    if any(w in text for w in ["cycle", "directed graph"]) and "topo" not in text:
        return _explain_cycle(profile, classification, algorithm, verification)
    if any(w in text for w in ["merge sort", "mergesort"]) or (
        "sort" in text and ("divide-and-conquer" in text or "divide and conquer" in text)
    ):
        return _explain_mergesort(profile, classification, algorithm, verification)
    if any(w in text for w in ["koko", "eating bananas", "speed k"]):
        return _explain_binary_search_answer(profile, classification, algorithm, verification)
    if any(w in text for w in ["two sum", "two-sum", "two pointers", "pair sum", "two elements sum", "sum to the target"]):
        return _explain_two_sum(profile, classification, algorithm, verification)
    if any(w in text for w in ["longest common subsequence", "lcs"]):
        return _explain_lcs(profile, classification, algorithm, verification)
    if any(w in text for w in ["knapsack", "0/1"]):
        return _explain_knapsack(profile, classification, algorithm, verification)
    return None


# ---------------------------------------------------------------------------
# LLM path
# ---------------------------------------------------------------------------

def _llm_explain(
    profile: ProblemProfile,
    classification: ClassificationResult,
    algorithm: ConcreteAlgorithm,
    verification: VerificationReport,
    model: str = "gpt-4o",
) -> Explanation:
    import instructor
    from openai import OpenAI

    taxonomy = load_taxonomy()
    template = _argument_template_for(classification.primary_paradigm_id, taxonomy)
    system = (PROMPTS_DIR / "explainer_system.txt").read_text(encoding="utf-8")
    system += f"\n\nArgument template you MUST follow:\n{template}\n"

    user = f"""Problem profile:
{profile.model_dump_json(indent=2)}

Classification:
{classification.model_dump_json(indent=2)}

Algorithm:
{algorithm.model_dump_json(indent=2)}

Verification:
{verification.model_dump_json(indent=2)}

Produce an Explanation JSON object. paradigm_id must match the classification.
argument_template_used should name the template you followed.
"""

    client = instructor.from_openai(OpenAI())
    result = client.chat.completions.create(
        model=model,
        response_model=Explanation,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
    )
    result.paradigm_id = classification.primary_paradigm_id
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def explain(
    profile: ProblemProfile,
    classification: ClassificationResult,
    algorithm: ConcreteAlgorithm,
    verification: VerificationReport,
    *,
    model: str = "gpt-4o",
    use_mock_if_no_key: bool = True,
) -> Explanation:
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            return _llm_explain(profile, classification, algorithm, verification, model=model)
        except Exception as e:
            if not use_mock_if_no_key:
                raise
            print(f"[explainer] LLM call failed ({e}); falling back to template")

    templated = _match_explainer(profile, classification, algorithm, verification)
    if templated is not None:
        return templated

    # Minimal fallback
    return Explanation(
        paradigm_id=classification.primary_paradigm_id,
        argument_template_used=_argument_template_key(
            classification.primary_paradigm_id, load_taxonomy()
        ),
        textbook_why=(
            algorithm.loop_invariant_or_key_insight
            + "\n\n"
            + _verification_note(verification)
            + "\n\n(No specialized explanation template matched; real LLM recommended.)"
        ),
        why_alternatives_fail=_contrastive_from_rejections(classification),
        formal_proof_sketch=None,
        edge_cases_discussed=[],
    )
