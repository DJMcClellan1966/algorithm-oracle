"""Smoke/demo isolation from ambient LLM credentials."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_isolate_from_llm_env_drops_keys(monkeypatch):
    from src.offline_env import isolate_from_llm_env

    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5-coder:14B")
    isolate_from_llm_env()
    assert "OPENAI_API_KEY" not in __import__("os").environ
    assert "ANTHROPIC_API_KEY" not in __import__("os").environ
    assert "OLLAMA_MODEL" not in __import__("os").environ


def test_smoke_and_demos_call_isolate():
    smoke = (ROOT / "scripts" / "gatekeeper_smoke.py").read_text(encoding="utf-8")
    assert "isolate_from_llm_env" in smoke
    for name in (
        "demo_full.py",
        "demo_classifier.py",
        "demo_instantiate.py",
        "demo_verification.py",
    ):
        text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert "isolate_from_llm_env" in text, name
