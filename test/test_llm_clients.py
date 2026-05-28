from __future__ import annotations

import pytest

from backend.app.config import Settings
from backend.app.llm_clients import DeterministicLLMClient, build_llm_client


def test_build_llm_client_defaults_to_deterministic() -> None:
    cfg = Settings(rag_llm_provider="deterministic")
    client = build_llm_client(cfg)
    assert isinstance(client, DeterministicLLMClient)


def test_build_llm_client_openai_requires_api_key() -> None:
    cfg = Settings(rag_llm_provider="openai", openai_api_key="")
    with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
        build_llm_client(cfg)
