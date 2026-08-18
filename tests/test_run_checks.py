"""
Epic 3.2: gatekeeper scripts must keep pytest + LIS smoke.
Do not exec run_checks.sh from pytest — that would recurse.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def test_run_checks_sh_contains_required_steps():
    script = (ROOT / "run_checks.sh").read_text(encoding="utf-8")
    assert "set -euo pipefail" in script
    assert "-m pytest tests/" in script
    assert "scripts/gatekeeper_smoke.py" in script
    assert "checks passed" in script
    assert ".venv" in script, "gatekeeper must use the project's own venv, not a bare `python`"


def test_run_checks_ps1_contains_required_steps():
    script = (ROOT / "run_checks.ps1").read_text(encoding="utf-8")
    assert "-m pytest tests/" in script
    assert "scripts/gatekeeper_smoke.py" in script
    assert "checks passed" in script
    assert ".venv" in script, "gatekeeper must use the project's own venv, not a bare `python`"


def test_gatekeeper_smoke_requires_lis_passed():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["OPENAI_API_KEY"] = "sk-must-not-be-used"
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "gatekeeper_smoke.py")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "pipeline smoke ok" in completed.stdout
    assert "dp_optimal_substructure" in completed.stdout
    assert "passed" in completed.stdout
