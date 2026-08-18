# Next Steps

v1 + P0/P1/P2 are in-repo: 11 paradigms, template-first LLM, word-boundary
shapes, real topo/activity checks, call timeouts, US coin-change template,
negative eval corpus.

## Use with Grok CLI
From this repository root:

```text
grok
# Read PRODUCT.md, AGENTS.md, NEXT_STEPS.md. State next task. No code.
```

Then: Plan only for next leaf → implement one leaf → run `.\run_checks.ps1` (or `./run_checks.sh`) yourself → commit → next.

## Next leaves (do not start until the previous is accepted)

### P3 — surfaces and typed response
- `run_oracle` returns a typed model (optional classification/algorithm when gated)
- Tiny CLI (`python -m src` or `scripts/oracle.py`) matching PRODUCT’s “CLI / Streamlit”
- Streamlit: template-vs-LLM badge; add missing dropdown examples (two-sum, LCS, knapsack, topo) if still absent
- Isolate `gatekeeper_smoke.py` / demos from ambient `OPENAI_API_KEY` / `OLLAMA_MODEL`

### Later
- Persist `shape` from the profile into every stage’s logs in the UI
- More labeled negatives as new false-match bugs are found
- Do not weaken Epic 1 to greenwash any of the above
