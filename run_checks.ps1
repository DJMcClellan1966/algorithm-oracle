# Deterministic gatekeeper (Windows). Same steps as run_checks.sh.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "== creating .venv =="
    python -m venv .venv
    & ".\.venv\Scripts\python.exe" -m pip install -q -r requirements.txt
}
$PY = ".\.venv\Scripts\python.exe"

Write-Host "== git status =="
git status --short
if ($LASTEXITCODE -ne 0) { Write-Host "(git status skipped)" }

Write-Host "== pytest =="
$env:PYTHONPATH = "."
& $PY -m pytest tests/ -v --maxfail=5
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== demo smoke (pipeline import + LIS must pass) =="
& $PY scripts/gatekeeper_smoke.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== checks passed =="
