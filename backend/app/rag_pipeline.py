from __future__ import annotations

from dataclasses import dataclass
import logging

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

    def ingest(self, documents: list[str]) -> int:
        cleaned = [doc.strip() for doc in documents if doc and doc.strip()]
        if not cleaned:
            return 0

        embeddings = self.embedder.encode(cleaned).tolist()
        ids = [f"doc_{self.collection.count()}_{index}" for index in range(len(cleaned))]
        self.collection.add(ids=ids, documents=cleaned, embeddings=embeddings)
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
