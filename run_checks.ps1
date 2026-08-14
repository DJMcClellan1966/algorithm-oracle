# Deterministic gatekeeper (Windows). Same steps as run_checks.sh.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "== git status =="
git status --short
if ($LASTEXITCODE -ne 0) { Write-Host "(git status skipped)" }

Write-Host "== pytest =="
$env:PYTHONPATH = "."
python -m pytest tests/ -v --maxfail=5
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== demo smoke (pipeline import + LIS must pass) =="
python scripts/gatekeeper_smoke.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "== checks passed =="
