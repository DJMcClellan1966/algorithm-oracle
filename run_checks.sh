#!/usr/bin/env bash
# Deterministic gatekeeper — run in YOUR terminal, do not trust agent self-reports alone.
set -euo pipefail
cd "$(dirname "$0")"

if [ -f .venv/Scripts/python.exe ]; then
    PY=.venv/Scripts/python.exe
elif [ -f .venv/bin/python ]; then
    PY=.venv/bin/python
else
    echo "== creating .venv =="
    python -m venv .venv
    if [ -f .venv/Scripts/python.exe ]; then
        PY=.venv/Scripts/python.exe
    else
        PY=.venv/bin/python
    fi
    "$PY" -m pip install -q -r requirements.txt
fi

echo "== git status =="
git status --short || true

echo "== pytest =="
PYTHONPATH=. "$PY" -m pytest tests/ -v --maxfail=5

echo "== demo smoke (pipeline import + LIS must pass) =="
PYTHONPATH=. "$PY" scripts/gatekeeper_smoke.py

echo "== checks passed =="
