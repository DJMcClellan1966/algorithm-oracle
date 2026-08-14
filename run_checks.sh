#!/usr/bin/env bash
# Deterministic gatekeeper — run in YOUR terminal, do not trust agent self-reports alone.
set -euo pipefail
cd "$(dirname "$0")"

echo "== git status =="
git status --short || true

echo "== pytest =="
PYTHONPATH=. python -m pytest tests/ -v --maxfail=5

echo "== demo smoke (pipeline import + one problem) =="
PYTHONPATH=. python -c "
from src.pipeline import run_oracle
r = run_oracle('Given an array of integers, return the length of the longest strictly increasing subsequence.')
assert r.get('classification') is not None
assert r['verification'].status in ('passed', 'failed', 'outside_verifiable_range', 'skipped')
print('pipeline smoke ok:', r['classification'].primary_paradigm_id, r['verification'].status)
"

echo "== checks passed =="
