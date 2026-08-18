# Algorithm Oracle

A structured algorithmic advisor that forces explicit classification, verification, and textbook-style justification.

## Pipeline

1. **Problem Profiler** – structured profile + clarification gate
2. **Paradigm Tournament / Classifier** – ranked candidates + explicit rejections + precondition checks
3. **Concrete Instantiation** – loop invariant first → pseudocode + brute-force reference
4. **Verification Harness** – differential testing vs reference + adversarial cases
5. **Explanation Synthesizer** – paradigm-specific proof template + contrastive section

UI default: **Pseudocode first**, with toggle to real implementation (Python).

## Design Principles

- Classification is the highest-risk stage → multi-candidate + explicit rejections
- No explanation without verification when verification is feasible
- Argument templates, not free-form “book voice”
- Uncertainty is a required field
- Strict structured JSON between stages
- Taxonomy is the single source of truth

## Project Layout

```
algorithm-oracle/
├── taxonomy/          # Paradigm definitions, precondition checklists, argument templates
├── schemas/           # Pydantic / JSON schemas for every stage
├── prompts/           # System prompts per stage
├── verification/      # Brute-force generator + differential tester
├── app/               # Streamlit UI (pseudocode primary)
├── src/               # Core pipeline orchestration
├── examples/          # Test problems + expected classifications
├── scripts/           # Demos + gatekeeper smoke
└── tests/             # Regression for harness, pipeline stages, UI contract
```

## Quick Start

From this repository root (not `artifacts/algorithm-oracle`):

```bash
pip install -r requirements.txt
PYTHONPATH=. python -m pytest tests/ -v
PYTHONPATH=. streamlit run app/streamlit_app.py
```

Gatekeeper (human-run; do not trust agent self-reports alone) — creates and installs its own `.venv` automatically if one doesn't exist yet:

```bash
./run_checks.sh          # Unix / Git Bash
# or
.\run_checks.ps1         # Windows PowerShell
```

Offline demos (no API key required):

```bash
PYTHONPATH=. python scripts/demo_full.py
PYTHONPATH=. python scripts/demo_classifier.py
PYTHONPATH=. python scripts/demo_verification.py
```

Set `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`) to use the real LLM path instead of offline templates. To use a local Ollama model instead, set `OLLAMA_MODEL` (e.g. `qwen2.5-coder:14B`) — no API key needed. `OLLAMA_BASE_URL` defaults to `http://localhost:11434/v1`. If both are set, `OLLAMA_MODEL` takes priority.

## Status

v1 pipeline is wired and test-backed: Profile → Classify → Instantiate → Verify → Explain — across **all 11 taxonomy paradigms** (greedy, DP, divide & conquer, graph traversal, shortest path, network flow, backtracking, two pointers, binary search, union-find, math formula). 162 tests passing.

- Labeled classics (LIS, activity selection, directed cycle, redundant connection, network delay time, climbing stairs, N-Queens count, max-flow value, …) verify **passed**.
- Every paradigm's real candidate — not just its structure — is checked by differential testing against its own reference, not a stand-in (`test_every_template_candidate_actually_verifies`).
- Unmatched problems (for example US coin change) **stub** and report `outside_verifiable_range` — they do not steal another template and false-pass.
- Underspecified graphs hit the clarification gate; `force=True` bypasses it.
- Streamlit shows **pseudocode first**, with a toggle to Python when a `def solve` candidate exists.
