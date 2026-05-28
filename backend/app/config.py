from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"
    app_host: str = "127.0.0.1"
    app_port: int = 8080

    vector_store_dir: str = "./vector_store"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    default_top_k: int = 4

    api_key: str = ""
    rate_limit_per_minute: int = 60

    rag_llm_provider: Literal["deterministic", "ollama", "openai"] = "deterministic"
    rag_llm_model: str = "llama3.1:8b"
    ollama_base_url: str = "http://127.0.0.1:11434"
    openai_api_key: str = ""
    openai_base_url: str = ""
    request_timeout_seconds: int = 45

    metrics_enabled: bool = True


settings = Settings()
