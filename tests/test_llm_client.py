"""
Local Ollama support alongside the real OpenAI/Anthropic API path.

Resolution logic only -- constructing an instructor/OpenAI client does not
itself make a network call, so these tests stay offline-safe regardless of
whether Ollama is actually running on the machine executing them.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.llm_client import (
    DEFAULT_ANTHROPIC_MODEL,
    active_provider,
    complete_structured,
    get_llm_client_and_model,
    has_llm_backend,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)


def test_no_backend_configured():
    assert has_llm_backend() is False


def test_ollama_model_alone_is_a_backend(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5-coder:14B")
    assert has_llm_backend() is True


def test_openai_key_alone_is_a_backend(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    assert has_llm_backend() is True


def test_anthropic_key_alone_is_a_backend(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
    assert has_llm_backend() is True


def test_ollama_takes_priority_over_a_real_api_key(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5-coder:14B")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    _client, model = get_llm_client_and_model("gpt-4o")
    assert model == "qwen2.5-coder:14B"


def test_openai_path_keeps_the_caller_supplied_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    _client, model = get_llm_client_and_model("gpt-4o")
    assert model == "gpt-4o"


def test_ollama_base_url_is_configurable(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5-coder:14B")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://example:9999/v1")
    client, _model = get_llm_client_and_model("gpt-4o")
    assert str(client.base_url).rstrip("/") == "http://example:9999/v1"


def test_ollama_base_url_defaults_to_localhost(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5-coder:14B")
    client, _model = get_llm_client_and_model("gpt-4o")
    assert str(client.base_url).rstrip("/") == "http://localhost:11434/v1"


def test_anthropic_only_selects_a_claude_model(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
    assert active_provider() == "anthropic"
    _client, model = get_llm_client_and_model("gpt-4o")
    assert model == DEFAULT_ANTHROPIC_MODEL
    assert model.startswith("claude")


def test_anthropic_model_env_overrides_default(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    _client, model = get_llm_client_and_model("gpt-4o")
    assert model == "claude-3-5-sonnet-latest"


def test_explicit_claude_model_is_kept(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
    _client, model = get_llm_client_and_model("claude-opus-4-0")
    assert model == "claude-opus-4-0"


def test_openai_key_wins_over_anthropic_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
    assert active_provider() == "openai"
    _client, model = get_llm_client_and_model("gpt-4o")
    assert model == "gpt-4o"


def test_complete_structured_uses_anthropic_messages_api(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake")
    captured = {}

    class _Messages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return "ok"

    class _Client:
        messages = _Messages()

    monkeypatch.setattr(
        "src.llm_client.get_llm_client_and_model",
        lambda default_model: (_Client(), "claude-sonnet-4-5"),
    )
    result = complete_structured(
        response_model=object,
        messages=[{"role": "user", "content": "hi"}],
        default_model="gpt-4o",
    )
    assert result == "ok"
    assert captured["max_tokens"] == 4096
    assert captured["model"] == "claude-sonnet-4-5"
