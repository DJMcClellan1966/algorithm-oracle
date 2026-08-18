"""CLI: PYTHONPATH=. python -m src \"problem\"."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import pytest

from schemas.models import OracleResponse
from src.cli import format_result, main
from src.pipeline import run_oracle


@pytest.fixture(autouse=True)
def offline_cli(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)


def test_format_result_includes_source_and_paradigm():
    result = run_oracle(
        "Given an array of integers, return the length of the longest "
        "strictly increasing subsequence."
    )
    text = format_result(result)
    assert "source: template" in text
    assert "dp_optimal_substructure" in text
    assert "verification: passed" in text
    assert "def solve" not in text


def test_format_result_gated():
    result = run_oracle("Find the shortest path between two nodes in a graph.")
    text = format_result(result)
    assert "source: gated" in text
    assert "needs clarification" in text


def test_cli_main_prints_lis(capsys):
    code = main(
        [
            "Given an array of integers, return the length of the longest "
            "strictly increasing subsequence."
        ]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "dp_optimal_substructure" in out
    assert "source: template" in out


def test_cli_json_is_oracle_response(capsys):
    code = main(
        [
            "--json",
            "Given an array of integers, return the length of the longest "
            "strictly increasing subsequence.",
        ]
    )
    assert code == 0
    payload = capsys.readouterr().out
    parsed = OracleResponse.model_validate_json(payload)
    assert parsed.source_path == "template"
    assert parsed.classification is not None
    assert parsed.classification.primary_paradigm_id == "dp_optimal_substructure"


def test_module_entrypoint_runs():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_MODEL"):
        env.pop(key, None)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "src",
            "Determine whether a directed graph contains a cycle.",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "graph_traversal" in completed.stdout
    assert "source: template" in completed.stdout
