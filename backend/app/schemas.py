from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    environment: str


class IngestRequest(BaseModel):
    documents: list[str] = Field(default_factory=list)


class IngestResponse(BaseModel):
    indexed_documents: int


class QueryRequest(BaseModel):
    question: str
    top_k: int | None = None


class QueryResponse(BaseModel):
    answer: str
    contexts: list[str]
    generation_provider: str
