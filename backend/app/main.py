from __future__ import annotations

import logging
import time
import uuid

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from .config import Settings, settings
from .llm_clients import build_llm_client
from .observability import MetricsStore
from .rag_pipeline import RAGPipeline
from .security import SlidingWindowRateLimiter
from .schemas import (
    HealthResponse,
    IngestRequest,
    IngestResponse,
    ProviderHealthResponse,
    QueryRequest,
    QueryResponse,
)

logger = logging.getLogger(__name__)


def create_app(
    app_settings: Settings | None = None,
    rag_pipeline: RAGPipeline | None = None,
) -> FastAPI:
    runtime_settings = app_settings or settings
    metrics = MetricsStore()
    limiter = SlidingWindowRateLimiter(limit=max(1, runtime_settings.rate_limit_per_minute), window_seconds=60)
    rag_instance = rag_pipeline

    app = FastAPI(title="Sword AI Systems API", version="0.2.0")

    def get_rag() -> RAGPipeline:
        nonlocal rag_instance
        if rag_instance is None:
            rag_instance = RAGPipeline(runtime_settings)
        return rag_instance

    def require_api_key(request: Request) -> None:
        configured_key = runtime_settings.api_key.strip()
        if not configured_key:
            return

        provided_key = request.headers.get("x-api-key", "").strip()
        if provided_key != configured_key:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

    def enforce_rate_limit(request: Request) -> None:
        client_host = request.client.host if request.client else "unknown"
        route_key = request.url.path
        if not limiter.allow(f"{client_host}:{route_key}"):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):  # type: ignore[override]
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_seconds = time.perf_counter() - start_time
            metrics.observe(500, request.url.path, duration_seconds)
            logger.exception("Unhandled request failure", extra={"request_id": request_id, "path": request.url.path})
            raise

        duration_seconds = time.perf_counter() - start_time
        response.headers["X-Request-ID"] = request_id

        metrics.observe(response.status_code, request.url.path, duration_seconds)
        logger.info(
            "request.complete",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration_seconds * 1000, 2),
            },
        )
        return response

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", environment=runtime_settings.app_env)

    @app.get("/health/provider", response_model=ProviderHealthResponse)
    def provider_health() -> ProviderHealthResponse:
        provider = runtime_settings.rag_llm_provider
        try:
            _ = build_llm_client(runtime_settings)
        except Exception as error:  # pylint: disable=broad-except
            return ProviderHealthResponse(provider=provider, status="degraded", detail=str(error))

        if provider == "ollama":
            try:
                with httpx.Client(timeout=max(2, runtime_settings.request_timeout_seconds // 2)) as client:
                    response = client.get(f"{runtime_settings.ollama_base_url}/api/tags")
                    response.raise_for_status()
            except Exception as error:  # pylint: disable=broad-except
                return ProviderHealthResponse(
                    provider=provider,
                    status="degraded",
                    detail=f"Ollama connectivity check failed: {error}",
                )

        return ProviderHealthResponse(provider=provider, status="ok", detail="Provider configuration is valid")

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics_endpoint() -> str:
        if not runtime_settings.metrics_enabled:
            raise HTTPException(status_code=404, detail="Metrics are disabled")
        return metrics.render_prometheus()

    @app.post(
        "/rag/ingest",
        response_model=IngestResponse,
        dependencies=[Depends(require_api_key), Depends(enforce_rate_limit)],
    )
    def ingest(payload: IngestRequest) -> IngestResponse:
        indexed = get_rag().ingest(payload.documents)
        return IngestResponse(indexed_documents=indexed)

    @app.post(
        "/rag/query",
        response_model=QueryResponse,
        dependencies=[Depends(require_api_key), Depends(enforce_rate_limit)],
    )
    def query(payload: QueryRequest) -> QueryResponse:
        result = get_rag().query(payload.question, payload.top_k)
        return QueryResponse(
            answer=result.answer,
            contexts=result.contexts,
            generation_provider=result.generation_provider,
        )

    return app

app = create_app()
