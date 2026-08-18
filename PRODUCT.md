# PRODUCT.md — Algorithm Oracle

## One-sentence job
A local tool that takes a natural-language algorithmic problem and returns a structured advisory: profile → paradigm (with explicit rejections) → pseudocode + executable candidate → differential verification → textbook “why”.

## Design thesis
Plausible-looking algorithms are not enough. Classification must be explicit, implementations must be checked against a reference when feasible, and explanations must follow argument templates — not free-form confidence.

## In scope (v1)

### Epic 1 — Verification harness (FIRST)
1. Restricted compilation of Python `solve` sources
2. Differential testing (candidate vs brute-force reference)
3. Input generators: arrays, intervals, digraphs, (piles, h), LCS pairs, knapsack tuples, tree+extra-edge graphs, weighted digraphs, stair counts, N-Queens counts, flow networks
4. Adversarial edge cases + clear pass/fail report
5. Proven against hand-written toys: ≥1 correct + ≥1 deliberately buggy algorithm

### Epic 2 — Pipeline stages (each stage testable)
1. Profiler (+ clarification gate)
2. Classifier (ranked paradigm + rejections + precondition answers)
3. Instantiator (invariant → pseudocode → python_candidate + brute_force_reference)
4. Explainer (template-bound why + contrastive rejections)
5. Orchestrator wiring stages with structured schemas

### Epic 3 — Surfaces
1. CLI / Streamlit UI: pseudocode primary, toggle to Python
2. Offline templates for all 11 taxonomy paradigms: activity selection, LIS, directed cycle, coin change (stubbed by design), mergesort, Koko binary search, two-sum, LCS, 0/1 knapsack, topo sort, redundant connection (union-find), network delay time (shortest path), climbing stairs (math formula), N-Queens count (backtracking), max-flow value (network flow)
3. Eval corpus regression (labeled paradigms)

## Out of scope (v1)
- Remote/cloud sandbox execution of untrusted code
- Training or fine-tuning models inside this repo
- Web deployment / multi-user auth
- Claiming correctness when verification is outside_verifiable_range without saying so

## Stack
- Python 3.11+
- Pydantic schemas between stages
- Streamlit UI (optional entry)
- pytest for regression
- Local-first; optional OPENAI_API_KEY/ANTHROPIC_API_KEY or a local OLLAMA_MODEL for LLM stages (offline templates required regardless)

## Success criteria (teeth, not vibes)
- [x] `run_checks.sh` (or `run_checks.ps1`) exits 0 after pytest + LIS smoke
- [x] Classifier regression: all labeled examples in `examples/test_problems.json` match expected paradigm
- [x] Differential tester flags a known-buggy LIS (or similar) as **failed** with concrete counter-examples
- [x] Differential tester passes a known-correct LIS / activity-selection / directed-cycle path
- [x] No pipeline stage marked done without tests that would fail if the stage were deleted
- [x] `run_oracle` runs Profile → Classify → Instantiate → Verify → Explain on all 11 taxonomy paradigms (Greedy, DP, Divide & Conquer, Graph Traversal, Shortest Path, Network Flow, Backtracking, Two Pointers, Binary Search, Union-Find, Math Formula)
- [x] When verification is not applicable, status is `outside_verifiable_range` (never silent “passed”)
- [x] Every paradigm's real candidate — not just its structure — actually runs through differential verification and passes (`test_every_template_candidate_actually_verifies`)

## Sample demos
- LIS length
- Activity selection (intervals)
- Directed cycle detection
- Two-sum (sort + two pointers)
- Underspecified graph path (must hit clarification gate)
- Redundant connection (Union-Find)
- Network delay time (Dijkstra shortest path)
- Climbing stairs (linear-recurrence math formula)
- N-Queens solution count (backtracking with pruning)
- Maximum flow value (Edmonds-Karp)

## Non-goals for agent sessions
Do not rebuild the whole app in one shot. Do not mark stages complete because output “looks right.”
