# Deployment Topologies

## Topology A: Local Learning Mode

Use case:
- Individual learning and debugging on a single machine.

Components:
- FastAPI app process
- Local ChromaDB persistence (`vector_store/`)
- Deterministic or Ollama provider

Pros:
- Minimal setup
- Fast iteration cycle

Trade-offs:
- No horizontal scaling
- Shared local state only

## Topology B: Team Staging Mode

Use case:
- Small team validation before production release.

Components:
- API container (Docker Compose)
- Shared persistent volume for vector store
- Hosted provider (OpenAI) or managed Ollama host
- CI pipeline for test gating

Pros:
- Repeatable environment
- Better release confidence

Trade-offs:
- Still limited isolation and tenancy controls

## Topology C: Production Service Mode

Use case:
- Multi-user deployment with operational SLOs.

Components:
- Replicated API instances behind load balancer
- Externalized vector DB/storage
- Secret manager for API keys/provider credentials
- Centralized metrics/log aggregation
- CI/CD with promotion gates (tests, retrieval thresholds)

Pros:
- Scalable and observable
- Supports release governance

Trade-offs:
- Higher operational complexity

## Recommended Progression

1. Start in Topology A for model and retrieval iteration.
2. Move to Topology B for team-level validation and reproducibility.
3. Promote to Topology C when usage, reliability, and compliance requirements justify it.
