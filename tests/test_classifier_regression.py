"""
Regression suite: classifier must map labeled examples to expected paradigm ids.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.classifier import classify_from_text

EXAMPLES_PATH = ROOT / "examples" / "test_problems.json"


@pytest.fixture(autouse=True)
def offline_classifier(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)


def load_examples():
    with open(EXAMPLES_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("example", load_examples(), ids=lambda e: e["id"])
def test_classifier_expected_paradigm(example):
    result = classify_from_text(example["problem"])
    assert result.primary_paradigm_id == example["expected_paradigm_id"], (
        f"[{example['id']}] expected {example['expected_paradigm_id']}, "
        f"got {result.primary_paradigm_id}"
    )


def test_all_examples_have_rejections():
    for example in load_examples():
        result = classify_from_text(example["problem"])
        assert len(result.rejected) >= 1, f"[{example['id']}] expected at least one rejection"


def test_known_shape_does_not_call_llm_classifier(monkeypatch):
    monkeypatch.setattr("src.llm_client.has_llm_backend", lambda: True)

    def boom(*_a, **_k):
        raise AssertionError("LLM must not run for a known shape")

    monkeypatch.setattr("src.llm_client.complete_structured", boom)
    result = classify_from_text(
        "Given an array of integers, return the length of the longest "
        "strictly increasing subsequence."
    )
    assert result.primary_paradigm_id == "dp_optimal_substructure"
    assert "Mock" in (result.unverified_because or "")
