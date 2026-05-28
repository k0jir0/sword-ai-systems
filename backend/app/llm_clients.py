from __future__ import annotations

from dataclasses import dataclass

import httpx
from openai import OpenAI

from .config import Settings


def _build_prompt(question: str, contexts: list[str]) -> str:
    context_block = "\n".join(f"[{index + 1}] {context}" for index, context in enumerate(contexts))
    return (
        "You are a grounded AI assistant. Answer only from the provided contexts. "
        "If the contexts are insufficient, explicitly say so.\n\n"
        f"Question:\n{question}\n\n"
        f"Contexts:\n{context_block}\n\n"
        "Return a concise answer and cite context ids like [1], [2]."
    )


class LLMClient:
    provider_name = "deterministic"

    def generate(self, question: str, contexts: list[str]) -> str:
        raise NotImplementedError


class DeterministicLLMClient(LLMClient):
    provider_name = "deterministic"

    def generate(self, question: str, contexts: list[str]) -> str:
        joined_context = "\n".join(f"[{index + 1}] {context}" for index, context in enumerate(contexts))
        return (
            f"Question: {question}\n\n"
            "Grounded summary from retrieved context:\n"
            f"{joined_context}\n\n"
            "Note: deterministic mode is active; configure RAG_LLM_PROVIDER for generative responses."
        )


@dataclass
class OllamaLLMClient(LLMClient):
    model: str
    base_url: str
    timeout_seconds: int
    provider_name: str = "ollama"

    def generate(self, question: str, contexts: list[str]) -> str:
        prompt = _build_prompt(question, contexts)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            body = response.json()

        generated = body.get("response", "").strip()
        if not generated:
            raise RuntimeError("Ollama returned an empty response.")

        return generated


@dataclass
class OpenAILLMClient(LLMClient):
    model: str
    api_key: str
    base_url: str
    timeout_seconds: int
    provider_name: str = "openai"

    def __post_init__(self) -> None:
        client_kwargs: dict[str, str | int] = {
            "api_key": self.api_key,
            "timeout": self.timeout_seconds,
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = OpenAI(**client_kwargs)

    def generate(self, question: str, contexts: list[str]) -> str:
        prompt = _build_prompt(question, contexts)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You answer with grounded, cited summaries only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )

        content = (response.choices[0].message.content or "").strip()
        if not content:
            raise RuntimeError("OpenAI returned an empty response.")

        return content


def build_llm_client(settings: Settings) -> LLMClient:
    if settings.rag_llm_provider == "ollama":
        return OllamaLLMClient(
            model=settings.rag_llm_model,
            base_url=settings.ollama_base_url,
            timeout_seconds=settings.request_timeout_seconds,
        )

    if settings.rag_llm_provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when RAG_LLM_PROVIDER=openai")

        return OpenAILLMClient(
            model=settings.rag_llm_model,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout_seconds=settings.request_timeout_seconds,
        )

    return DeterministicLLMClient()
