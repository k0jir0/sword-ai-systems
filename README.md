# Sword AI Systems Tech Stack

## About

Sword is a learning-first AI systems project that connects theory and production in one codebase. It is designed to help learners move from core deep learning concepts to deployable, observable, and secure AI services.

The project combines a modern RAG application stack with practical ML training workflows. You can study model fundamentals, run retrieval experiments, and expose everything through a production-style API surface that includes authentication, rate limiting, and metrics.

### Purpose

- Bridge the gap between AI theory and software delivery.
- Provide a practical reference architecture for end-to-end AI systems.
- Make experimentation reproducible with test coverage and CI.

### Tech Stack Summary

- API and serving: FastAPI, Uvicorn
- Configuration: Pydantic Settings, .env
- Retrieval and vector store: SentenceTransformers, ChromaDB
- Generation backends: deterministic mode, Ollama, OpenAI
- ML workflows: PyTorch, scikit-learn, Hugging Face Transformers and Datasets
- Operations and quality: pytest, GitHub Actions CI, Prometheus-style metrics

### Learning Intentions

- Understand neural network and optimization fundamentals through runnable scripts.
- Learn transformer-based NLP workflows and model adaptation patterns.
- Build and evaluate Retrieval-Augmented Generation pipelines.
- Practice production concerns such as API contracts, security controls, throttling, and observability.
- Develop confidence shipping AI systems with repeatable tests and deployment-ready structure.

This project bootstraps a practical stack for the learning goals in `index.txt`:

- Neural network and deep learning fundamentals
- Transformer-based NLP workflows
- Production-oriented Retrieval-Augmented Generation (RAG)

## Included Stack

- API layer: FastAPI + Uvicorn
- Configuration: Pydantic Settings + `.env`
- Embeddings: SentenceTransformers
- Vector database: ChromaDB (persistent local store)
- Generation providers: deterministic, Ollama, OpenAI
- ML training: PyTorch + scikit-learn + Hugging Face Transformers/Datasets
- CLI tooling: Typer + Rich (starter scripts)
- Security controls: API key auth + per-route rate limiting
- Observability: request IDs + Prometheus-style metrics endpoint
- Quality checks: pytest test suite + retrieval evaluation script
- Container option: Docker Compose

## Project Layout

```text
Sword/
  backend/app/
    main.py              # FastAPI service
    config.py            # App settings
    schemas.py           # Request/response models
    rag_pipeline.py      # Retrieval and lightweight response generation
    llm_clients.py       # Provider adapters for answer generation
    security.py          # Sliding-window rate limiter
    observability.py     # Metrics store and rendering
  scripts/
    ingest_docs.py       # Ingest local text/markdown docs into ChromaDB
    train_mlp_demo.py    # Deep learning fundamentals demo (MLP)
    train_transformer_demo.py  # Transformer fine-tuning starter
    eval_retrieval.py    # Baseline retrieval quality probe
  test/
    test_api.py
  .github/workflows/
    ci.yml
  docs/
    techstack.md
```

## Quick Start (Local)

```bash
cd McGillSoftware/Sword
python -m venv .venv
.venv\Scripts\activate
copy .env.example .env
pip install -e .
uvicorn backend.app.main:app --host 127.0.0.1 --port 8080 --reload
```

API docs will be at `http://127.0.0.1:8080/docs`.

## Production Controls

Set these in `.env` when moving beyond local demos:

- `API_KEY` to require `x-api-key` on RAG endpoints
- `RATE_LIMIT_PER_MINUTE` for per-client per-route throttling
- `RAG_LLM_PROVIDER` with one of `deterministic`, `ollama`, `openai`
- `RAG_LLM_MODEL` for the selected provider
- `OLLAMA_BASE_URL` when using Ollama
- `OPENAI_API_KEY` (and optional `OPENAI_BASE_URL`) when using OpenAI

Metrics are exposed at `GET /metrics` when `METRICS_ENABLED=true`.

## Quick Start (Docker)

```bash
cd McGillSoftware/Sword
copy .env.example .env
docker compose up --build
```

## Example Flow

1. Ingest local docs:

```bash
python scripts/ingest_docs.py --path . --glob "**/*.txt"
```

2. Query the RAG endpoint:

```bash
curl -X POST http://127.0.0.1:8080/rag/query ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"What are the core learning outcomes?\",\"top_k\":4}"
```

3. Run learning scripts:

```bash
python scripts/train_mlp_demo.py
python scripts/train_transformer_demo.py
```

4. Run retrieval quality probe:

```bash
python scripts/eval_retrieval.py --path . --glob "**/*.txt" --top-k 4
```

5. Run tests:

```bash
pytest -q
```

## Notes

- The default RAG provider is deterministic for reproducibility.
- Switch to Ollama or OpenAI via `.env` without changing code.
- API request responses include `generation_provider` for traceability.
