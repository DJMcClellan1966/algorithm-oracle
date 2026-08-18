"""
Single source of truth for which LLM backend Algorithm Oracle's optional
real-model path should use. Offline templates remain the default for
every stage; this only matters once a real model is actually invoked.

Priority: OLLAMA_MODEL (local, free, no API key) is checked first if
set. OPENAI_API_KEY / ANTHROPIC_API_KEY are the fallback for a real
hosted API.

Ollama's OpenAI-compatible endpoint does not reliably return real
tool_calls for structured output -- confirmed empirically: instructor's
default TOOLS mode gets a tool-call-shaped JSON string back inside
`message.content` instead of a proper `tool_calls` object, which
instructor cannot parse. Mode.JSON (ask for raw JSON, skip tool-calling
machinery entirely) works reliably against qwen2.5-coder:14B and was
verified against this project's actual ClassificationResult and
ConcreteAlgorithm schemas, not just a toy example.
"""

from __future__ import annotations

import os
from typing import Any, Optional


def has_llm_backend() -> bool:
    """True if either a local Ollama model or a real API key is configured."""
    return bool(
        os.getenv("OLLAMA_MODEL")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
    )


def get_llm_client_and_model(default_model: str) -> tuple[Any, str]:
    """
    Returns (instructor_client, model_name) for whichever backend is
    configured. Only call this after has_llm_backend() is True.
    """
    import instructor
    from openai import OpenAI

    ollama_model = os.getenv("OLLAMA_MODEL")
    if ollama_model:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        client = instructor.from_openai(
            OpenAI(base_url=base_url, api_key="ollama"),
            mode=instructor.Mode.JSON,
        )
        return client, ollama_model

    return instructor.from_openai(OpenAI()), default_model
