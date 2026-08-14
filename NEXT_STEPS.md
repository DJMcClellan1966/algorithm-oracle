# Next Steps

## Agent-ready scaffolding (done)
- [x] PRODUCT.md — scope, harness-first success criteria
- [x] AGENTS.md — plan/one-leaf/git/silent-mutation/no-secrets rules
- [x] BUILD_PLAN.md — Epic 1 harness → Epic 2 pipeline → Epic 3 surfaces
- [x] .grokignore — secrets/caches out of agent context
- [x] run_checks.sh — human gatekeeper (pytest + pipeline smoke)

## Use with Grok CLI
cd artifacts/algorithm-oracle
grok
# Read PRODUCT.md, AGENTS.md, BUILD_PLAN.md. State next task. No code.

Then: Plan only for next task ID → implement one leaf → run ./run_checks.sh yourself → commit → next.

## Already in-repo
Pipeline, offline templates, verification generators, Streamlit UI, classifier regression (11 passed).
