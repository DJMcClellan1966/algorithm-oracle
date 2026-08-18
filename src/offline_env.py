"""Clear hosted/local LLM env so smoke tests and demos stay offline-deterministic."""

from __future__ import annotations

import os

LLM_ENV_VARS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_MODEL")


def isolate_from_llm_env() -> None:
    """Drop ambient API keys / Ollama model so offline templates are used."""
    for name in LLM_ENV_VARS:
        os.environ.pop(name, None)
