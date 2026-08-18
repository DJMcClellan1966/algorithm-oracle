# BUILD_PLAN.md — Hierarchical decomposition (Grok CLI loop)

## Ordering override (Oracle-specific)
**Epic 1 = verification harness**, not UI.  
A stage is not done until tests exist that catch its failure.  
Do not build classifier/instantiator “demo quality” before the harness can reject a buggy `solve`.

---

## Epic 1 — Verification harness
**Goal:** Tell correct algorithms from broken ones on small instances.

| ID | Task | Acceptance |
|----|------|------------|
| 1.1 | Restricted `compile_function` + safe builtins | Compiles `def solve`; rejects empty/missing |
| 1.2 | Differential tester | Equal outputs → pass; mismatch → failed case recorded |
| 1.3 | Array generators + adversarial | Empty, single, sorted, duplicates, negatives |
| 1.4 | Toy correct LIS vs brute force | Report status `passed` |
| 1.5 | Toy buggy LIS vs brute force | Report status `failed` with ≥1 concrete counter-example |
| 1.6 | Generators: intervals, digraphs, koko, two-sum pairs | Used by paradigm-aware runner |
| 1.7 | `run_verification_for_paradigm` | Routes by paradigm_id |

**Exit Epic 1 when:** 1.4 and 1.5 both true under `pytest` / demo_verification.

---

## Epic 2 — Pipeline stages
Each stage: schema → implementation → unit/regression tests → only then wire.

| ID | Task | Acceptance |
|----|------|------------|
| 2.1 | Pydantic models stable | Import + round-trip JSON |
| 2.2 | Profiler + clarification gate | Underspecified graph sets `needs_clarification` |
| 2.3 | Classifier + labeled regression | `tests/test_classifier_regression.py` green |
| 2.4 | Instantiator templates | LIS/activity/cycle/… emit candidate + reference (all 11 paradigms as of Epic 4) |
| 2.5 | Explainer templates | Argument template + contrastive rejections |
| 2.6 | `run_oracle` orchestration | Full dict; force=True bypasses gate |

---

## Epic 3 — Surfaces & packaging
| ID | Task | Acceptance |
|----|------|------------|
| 3.1 | Streamlit: pseudocode first, Python toggle | Manual |
| 3.2 | `run_checks.sh` gatekeeper | Exits 0 on clean tree |
| 3.3 | README / PRODUCT / AGENTS aligned | Human review |

---

---

## Epic 4 — Full paradigm coverage — **done**

**Goal:** Every paradigm in `taxonomy/paradigms.yaml` gets a real instantiator template, verification generator, and explainer template — not just the original 6 shipped in Epics 1–3.

| ID | Task | Acceptance |
|----|------|------------|
| 4.1 | Shared shape detection (`src/problem_shapes.py`) | Classifier/instantiator/explainer keyword-matching consolidated into one module; fixed 3 real cross-stage drift bugs found in the process (explainer missing keywords the other two had, classifier checking cycle before topo) |
| 4.2 | Fix `topo_sort` candidate/reference | Both used `import` inside the sandboxed `solve` (`_SAFE_BUILTINS` has no `__import__`, so it crashed on every real call); replaced with import-free equivalents. No prior test had ever run the real candidate |
| 4.3 | `union_find` — Redundant Connection | Union-Find with path compression, verified against a BFS-reachability reference |
| 4.4 | `shortest_path` — Network Delay Time | Array-based Dijkstra, verified against Bellman-Ford |
| 4.5 | `math_formula` — Climbing Stairs | O(1)-space linear recurrence, verified against exponential recursion |
| 4.6 | `backtracking` — N-Queens count | Pruned backtracking, verified against a brute-force permutation reference; counting variant used since a specific board isn't unique across two correct search algorithms, but the count is |
| 4.7 | `network_flow` — max-flow value | Edmonds-Karp (BFS augmenting paths), verified against naive Ford-Fulkerson (DFS augmenting paths); same "canonical scalar" reasoning as 4.6 |
| 4.8 | `run_checks.sh` / `run_checks.ps1` venv-aware | Gatekeeper finds or creates `.venv` automatically instead of depending on a bare `python` on PATH |

**Exit Epic 4 when:** all 11 taxonomy paradigms have a working instantiator + verification generator + explainer template + labeled `examples/test_problems.json` entry, and `test_every_template_candidate_actually_verifies` passes for every one of them — true as of 162 passing tests.

---

## Grok prompt micro-steps (copy/paste)

**Orient**
```text
Read PRODUCT.md, AGENTS.md, BUILD_PLAN.md. State which Epic/Task is next. No code.
```

**Plan only**
```text
Plan only for task [ID]: goal, files to touch, acceptance, risks. No code.
```

**Implement one leaf**
```text
Using PRODUCT.md scope and AGENTS.md rules, implement ONLY task [ID].
List files before editing. Run tests. Show diff summary.
If any file outside scope changed, revert it.
Do not start another task.
```

**Verify (agent)**
```text
Run: PYTHONPATH=. python -m pytest tests/ -v --maxfail=5
Report pass/fail and first failure only.
```

**Verify (human gatekeeper)**
```bash
./run_checks.sh
```

**Commit checkpoint**
```text
Review diff. If tests pass and task complete, suggest a one-line commit message for this task only. Do not commit unless I ask.
```

---

## Session rule of thumb
Orient → Plan (approve) → Implement one ID → Human `./run_checks.sh` → Commit → Next ID.
