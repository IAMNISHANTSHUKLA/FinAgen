"""
FinAgentX — Domain Interfaces (Abstract Base Classes)

All interfaces that infrastructure layer must implement.
Follows Dependency Inversion Principle — application/domain depend on these
abstractions, not on concrete implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from domain.schemas import (
    Chunk,
    Citation,
    EmbeddingVersion,
    EvalResult,
    FeedbackEntry,
    FeedbackStats,
    RetrievalResult,
    UserContext,
)


class LLMClient(ABC):
    """Abstract LLM client — Cerebras, Ollama, or any provider."""

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> str:
        """Generate a completion from messages."""
        ...

    @abstractmethod
    async def generate_structured(
        self,
        messages: list[dict[str, str]],
        *,
        schema: dict[str, Any],
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        """Generate a structured (JSON) completion validated against schema."""
        ...

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in text for budget management."""
        ...


class VectorStore(ABC):
    """Abstract vector store — Weaviate, Pinecone, or any provider."""

    @abstractmethod
    async def create_collection(
        self,
        name: str,
        *,
        embedding_dim: int = 384,
        metadata_schema: dict[str, str] | None = None,
    ) -> None:
        """Create a new collection/class."""
        ...

    @abstractmethod
    async def upsert(
        self,
        collection: str,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        """Insert or update chunks with their embeddings."""
        ...

    @abstractmethod
    async def hybrid_search(
        self,
        collection: str,
        query: str,
        *,
        alpha: float = 0.75,
        top_k: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        """Hybrid search: dense + BM25 with RRF fusion."""
        ...

    @abstractmethod
    async def delete_collection(self, name: str) -> None:
        """Delete a collection."""
        ...

    @abstractmethod
    async def get_collection_info(self, name: str) -> dict[str, Any]:
        """Get collection metadata (count, schema, etc.)."""
        ...


class Embedder(ABC):
    """Abstract embedder — sentence-transformers, OpenAI, etc."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts into vectors."""
        ...

    @abstractmethod
    def get_model_info(self) -> EmbeddingVersion:
        """Return current embedding model version info."""
        ...


class Reranker(ABC):
    """Abstract reranker — cross-encoder, ColBERT, etc."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        *,
        top_k: int = 8,
    ) -> list[RetrievalResult]:
        """Rerank retrieval results using cross-encoder scoring."""
        ...


class Cache(ABC):
    """Abstract cache — Redis, in-memory, etc."""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Get a cached value by key."""
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, *, ttl_seconds: int = 3600) -> None:
        """Set a cached value with TTL."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a cached value."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        ...


class PIIMasker(ABC):
    """Abstract PII masker — Presidio, regex, etc."""

    @abstractmethod
    def mask(self, text: str) -> tuple[str, dict[str, str]]:
        """Mask PII in text. Returns (masked_text, reverse_map)."""
        ...

    @abstractmethod
    def unmask(self, text: str, reverse_map: dict[str, str]) -> str:
        """Restore original PII from masked text using reverse map."""
        ...


class Authorizer(ABC):
    """Abstract retrieval-time authorizer (Fix #13)."""

    @abstractmethod
    def filter_results(
        self,
        results: list[RetrievalResult],
        user_context: UserContext,
    ) -> list[RetrievalResult]:
        """Filter retrieval results based on user permissions."""
        ...

    @abstractmethod
    def check_tool_access(
        self,
        tool_name: str,
        user_context: UserContext,
    ) -> bool:
        """Check if user has permission to use a specific tool."""
        ...


class FeedbackStore(ABC):
    """Abstract feedback storage (Fix #15)."""

    @abstractmethod
    async def store_feedback(self, entry: FeedbackEntry) -> str:
        """Store a feedback entry. Returns feedback_id."""
        ...

    @abstractmethod
    async def get_feedback_stats(self, time_range: str = "7d") -> FeedbackStats:
        """Get aggregate feedback statistics."""
        ...

    @abstractmethod
    async def get_low_confidence_queries(self, threshold: float = 0.5) -> list[dict]:
        """Get queries flagged for human review (active learning)."""
        ...


class AuditLogger(ABC):
    """Abstract audit logger — S3, local file, etc."""

    @abstractmethod
    async def log(
        self,
        session_id: str,
        action: str,
        *,
        tool_name: str = "",
        input_data: str = "",
        output_data: str = "",
        confidence: float = 0.0,
        user_id: str = "",
    ) -> None:
        """Log an auditable action."""
        ...
