# Tech Stack Rationale

## Why this stack

- `FastAPI` is lightweight and production-friendly for AI APIs.
- `SentenceTransformers` + `ChromaDB` gives a local RAG baseline with no external infra.
- Pluggable generation clients (`deterministic`, `ollama`, `openai`) provide prototype-to-production continuity.
- `PyTorch` and `Transformers` cover core deep learning and modern LLM architecture workflows.
- `Typer` and scripted entry points keep data/ML operations reproducible.
- API key auth, rate limiting, and request metrics provide essential production safety controls.

## Architecture

1. Data ingestion script reads local docs and stores chunks in ChromaDB.
2. API embeds user queries with the same embedding model.
3. Retriever fetches top-k chunks.
4. LLM adapter generates grounded answer from retrieved context.
5. Training scripts provide progression from MLP fundamentals to transformer fine-tuning.
6. Metrics and tests verify runtime behavior and deployment readiness.

## Next upgrades

- Add async task queue for ingestion and model jobs.
- Expand eval suite with labeled retrieval and grounding datasets.
- Add distributed tracing exporters and centralized logging sink.
- Add stronger authN/authZ strategy (JWT/OAuth2) for multi-user deployments.
