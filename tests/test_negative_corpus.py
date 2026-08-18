"""
Negative eval corpus: phrases that must not become a verified classic.

A green classifier on labeled hits is not enough — 'list of' used to become
LIS and then false-pass verification. These cases would fail if that
regression returned.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.pipeline import run_oracle
from src.problem_shapes import detect_shape

NEGATIVE_PATH = ROOT / "examples" / "negative_problems.json"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)


def _cases():
    with open(NEGATIVE_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("case", _cases(), ids=lambda c: c["id"])
def test_negative_shape_constraints(case):
    shape = detect_shape(case["problem"])
    for banned in case.get("must_not_shape", []):
        assert shape != banned, f"[{case['id']}] {shape!r} is banned"
    if "expected_shape" in case:
        assert shape == case["expected_shape"]


@pytest.mark.parametrize(
    "case",
    [c for c in _cases() if c.get("must_not_claim_passed")],
    ids=lambda c: c["id"],
)
def test_negative_pipeline_does_not_claim_passed(case):
    result = run_oracle(case["problem"])
    if result.needs_clarification:
        return
    assert result.verification is not None
    assert result.verification.status != "passed", (
        f"[{case['id']}] verification claimed passed for a negative example"
    )
