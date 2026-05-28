from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app


@dataclass
class FakeRAG:
    def ingest(self, documents: list[str]) -> int:
        return len([doc for doc in documents if doc.strip()])

    def query(self, question: str, top_k: int | None = None):
        return type(
            "FakeRetrieval",
            (),
            {
                "answer": f"stub-answer for: {question}",
                "contexts": ["context-a", "context-b"],
                "generation_provider": "fake",
            },
        )()


def build_test_client(**settings_kwargs) -> TestClient:
    cfg = Settings(**settings_kwargs)
    app = create_app(app_settings=cfg, rag_pipeline=FakeRAG())
    return TestClient(app)


def test_health_endpoint_is_public() -> None:
    client = build_test_client(api_key="")
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_ingest_requires_api_key_when_configured() -> None:
    client = build_test_client(api_key="secret")
    unauthorized = client.post("/rag/ingest", json={"documents": ["one"]})
    assert unauthorized.status_code == 401

    authorized = client.post(
        "/rag/ingest",
        headers={"x-api-key": "secret"},
        json={"documents": ["one", "two"]},
    )
    assert authorized.status_code == 200
    assert authorized.json()["indexed_documents"] == 2


def test_query_returns_provider_metadata() -> None:
    client = build_test_client(api_key="")
    response = client.post("/rag/query", json={"question": "hello"})
    assert response.status_code == 200
    body = response.json()
    assert body["generation_provider"] == "fake"
    assert len(body["contexts"]) == 2


def test_rate_limit_is_enforced() -> None:
    client = build_test_client(api_key="", rate_limit_per_minute=2)

    first = client.post("/rag/query", json={"question": "q1"})
    second = client.post("/rag/query", json={"question": "q2"})
    third = client.post("/rag/query", json={"question": "q3"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429


def test_metrics_endpoint_exposes_counters() -> None:
    client = build_test_client(api_key="", metrics_enabled=True)
    _ = client.get("/health")

    response = client.get("/metrics")
    assert response.status_code == 200
    payload = response.text
    assert "sword_requests_total" in payload
    assert "sword_requests_by_status" in payload
