# Next Steps

## Agent-ready scaffolding (done)
- [x] PRODUCT.md — scope, harness-first success criteria
- [x] AGENTS.md — plan/one-leaf/git/silent-mutation/no-secrets rules
- [x] BUILD_PLAN.md — Epic 1 harness → Epic 2 pipeline → Epic 3 surfaces
- [x] .grokignore — secrets/caches out of agent context
- [x] run_checks.sh / run_checks.ps1 — human gatekeeper (pytest + LIS smoke)

## Use with Grok CLI
From this repository root:

```text
grok
# Read PRODUCT.md, AGENTS.md, BUILD_PLAN.md. State next task. No code.
```

Then: Plan only for next task ID → implement one leaf → run `./run_checks.sh` or `.\run_checks.ps1` yourself → commit → next.

## Already in-repo
Epics 1–3: pipeline, offline templates, verification generators, Streamlit UI,
classifier regression, instantiator/explainer tests, `run_oracle` end-to-end.
Unmatched problems stub with `outside_verifiable_range`.
