# MINI_DECOMP — Algorithm Oracle × Grok CLI (PC)

Share this file. Drop it in the project root. Paste the **Session start** block into Grok CLI first.

---

## Goal
Local Algorithm Oracle: problem → profile → classify (+ rejections) → pseudocode/code → verify → textbook why.  
Build with **plan → one leaf → check → commit**. Never “looks right = done.”

## Stack
Python 3 · Pydantic · pytest · Streamlit (optional UI) · offline templates + optional `OPENAI_API_KEY`

## Commands (PC)
```bash
cd <project-root>
pip install -r requirements.txt
PYTHONPATH=. python -m pytest tests/ -v
PYTHONPATH=. python scripts/demo_full.py
PYTHONPATH=. streamlit run app/streamlit_app.py
./run_checks.sh          # you run this, not only the agent
```

---

## Hierarchy (build order)

### Epic 1 — Verification harness (FIRST)
| ID | Task | Done when |
|----|------|-----------|
| 1.1 | Compile `solve` safely | Restricted exec works |
| 1.2 | Differential test | Mismatch → failed cases |
| 1.3 | Array + adversarial generators | Edge cases covered |
| 1.4 | Correct toy vs reference | status `passed` |
| 1.5 | Buggy toy vs reference | status `failed` + counter-example |
| 1.6 | Generators: intervals, graphs, koko, pairs | Paradigm-aware runner |
| 1.7 | `run_verification_for_paradigm` | Routes by paradigm |

### Epic 2 — Pipeline stages
| ID | Task | Done when |
|----|------|-----------|
| 2.1 | Schemas stable | Pydantic round-trip |
| 2.2 | Profiler + clarification gate | Underspecified → gate |
| 2.3 | Classifier + labeled regression | `test_problems.json` green |
| 2.4 | Instantiator (invariant → code) | Candidate + reference |
| 2.5 | Explainer (templates + contrast) | Why + rejections |
| 2.6 | `run_oracle` wiring | Full dict end-to-end |

### Epic 3 — Surface
| ID | Task | Done when |
|----|------|-----------|
| 3.1 | UI/CLI: pseudocode first | Toggle to Python |
| 3.2 | Gatekeeper script | `./run_checks.sh` → 0 |
| 3.3 | Docs aligned | PRODUCT / AGENTS / README |

**Rule:** No Epic 2 stage is “done” without tests that fail if that stage is broken. Do not weaken Epic 1 to greenwash Epic 2.

---

## Session start (paste into Grok)

```text
Read MINI_DECOMP.md (and PRODUCT.md / AGENTS.md if present).

Rules:
1. Plan before code if >2 files.
2. One task ID per implement turn, then stop.
3. List files before editing; revert out-of-scope changes.
4. Never mark done from plausible output alone.
5. After success: suggest commit message "[ID] short description". Do not commit unless asked.
6. No secrets in repo.

Orient only: ≤5 bullets on current state + next task ID. No code.
```

---

## Micro-prompts

**Plan**
```text
Plan only task [ID]: goal, exclusive file list, acceptance, risks. No code.
```

**Implement**
```text
Implement ONLY task [ID]. Exclusive files only. Run:
PYTHONPATH=. python -m pytest tests/ -v --maxfail=5
Report: files, result, manual check. Stop.
```

**Verify**
```text
Run pytest as above. First failure only. No refactors.
```

**Fix**
```text
Smallest fix for this traceback only. Retest. No scope creep.
```

**Next**
```text
Task [ID] accepted. Name next ID. Plan only. No code.
```

---

## Human checkpoint (every leaf)
```bash
./run_checks.sh
git add -p && git commit -m "[ID] ..."
```

## Success (v1 teeth)
- [ ] Labeled classifier regression green  
- [ ] Buggy toy algorithm → verification **failed** with example  
- [ ] Correct toy → **passed**  
- [ ] Full pipeline on DP + Greedy + Graph samples  
- [ ] Clarification gate on underspecified graph  

---

## Out of scope (v1)
Remote sandbox · training models in-repo · “passed” when outside verifiable range without saying so
