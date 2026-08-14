#!/usr/bin/env bash
# Deterministic gatekeeper — run in YOUR terminal, do not trust agent self-reports alone.
set -euo pipefail
cd "$(dirname "$0")"

echo "== git status =="
git status --short || true

echo "== pytest =="
PYTHONPATH=. python -m pytest tests/ -v --maxfail=5

echo "== demo smoke (pipeline import + LIS must pass) =="
PYTHONPATH=. python scripts/gatekeeper_smoke.py

echo "== checks passed =="
