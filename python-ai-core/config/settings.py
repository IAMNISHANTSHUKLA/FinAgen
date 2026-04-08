"""
FinAgentX — Pydantic Settings Configuration

DI-ready configuration loaded from environment variables.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Service
    service_name: str = "finagentx-ai-core"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # Cerebras LLM
    cerebras_api_key: str = ""
    cerebras_model: str = "llama-4-scout-17b-16e-instruct"
    cerebras_base_url: str = "https://api.cerebras.ai/v1"
    cerebras_cheap_model: str = "llama-4-scout-17b-16e-instruct"

    # Judge model (separate from agent — Fix #4)
    judge_model: str = "llama-4-scout-17b-16e-instruct"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Weaviate
    weaviate_url: str = "http://localhost:8081"
    weaviate_collection: str = "FinancialDocuments"

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "finagentx"
    minio_secret_key: str = "finagentx-secret"

    # JWT Auth
    jwt_public_key: str = ""

    # RAG Pipeline
    rag_alpha: float = 0.75
    rag_initial_top_k: int = 20
    rag_rerank_top_k: int = 8
    rag_token_budget: int = 4096
    cascade_confidence_threshold: float = 0.7

    # Agent Guardrails
    agent_max_steps: int = 10
    agent_timeout_seconds: float = 60.0
    agent_per_tool_timeout: float = 10.0

    # Embedding
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_version: str = "1.0.0"
    embedding_dim: int = 384

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
