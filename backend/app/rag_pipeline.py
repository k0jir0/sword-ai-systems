from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

from .config import Settings, settings
from .llm_clients import LLMClient, build_llm_client

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    answer: str
    contexts: list[str]
    generation_provider: str


class RAGPipeline:
    def __init__(self, runtime_settings: Settings | None = None, llm_client: LLMClient | None = None) -> None:
        self.settings = runtime_settings or settings
        self.embedder = SentenceTransformer(self.settings.embedding_model)
        self.client = chromadb.PersistentClient(path=self.settings.vector_store_dir)
        self.collection = self.client.get_or_create_collection(name="sword_docs")
        self.llm_client = llm_client or build_llm_client(self.settings)

    def ingest(
        self,
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
    ) -> int:
        cleaned: list[str] = []
        cleaned_metadatas: list[dict[str, Any]] = []

        for index, doc in enumerate(documents):
            normalized = (doc or "").strip()
            if not normalized:
                continue
            cleaned.append(normalized)
            if metadatas and index < len(metadatas):
                cleaned_metadatas.append(metadatas[index])

        if not cleaned:
            return 0

        embeddings = self.embedder.encode(cleaned).tolist()

        if ids is None:
            base_count = self.collection.count()
            ids = [f"doc_{base_count}_{index}" for index in range(len(cleaned))]

        add_kwargs: dict[str, Any] = {
            "ids": ids,
            "documents": cleaned,
            "embeddings": embeddings,
        }
        if cleaned_metadatas and len(cleaned_metadatas) == len(cleaned):
            add_kwargs["metadatas"] = cleaned_metadatas

        self.collection.add(**add_kwargs)
        return len(cleaned)

    def query(self, question: str, top_k: int | None = None) -> RetrievalResult:
        retrieval_k = top_k or self.settings.default_top_k
        question_embedding = self.embedder.encode([question]).tolist()
        result = self.collection.query(query_embeddings=question_embedding, n_results=retrieval_k)

        contexts = result.get("documents", [[]])[0]
        if not contexts:
            return RetrievalResult(
                answer="No indexed context found yet. Ingest documents first.",
                contexts=[],
                generation_provider=self.llm_client.provider_name,
            )

        answer = self._build_grounded_answer(question, contexts)
        return RetrievalResult(
            answer=answer,
            contexts=contexts,
            generation_provider=self.llm_client.provider_name,
        )

    def _build_grounded_answer(self, question: str, contexts: list[str]) -> str:
        try:
            return self.llm_client.generate(question, contexts)
        except Exception as error:  # pylint: disable=broad-except
            logger.warning(
                "LLM generation failed, using deterministic fallback",
                exc_info=False,
                extra={"provider": self.llm_client.provider_name, "error": str(error)},
            )
            joined_context = "\n".join(f"- {ctx}" for ctx in contexts)
            return (
                f"Question: {question}\n\n"
                "Grounded summary from retrieved context:\n"
                f"{joined_context}\n\n"
                f"Generation fallback reason: {error}"
            )
