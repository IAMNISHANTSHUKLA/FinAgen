"""
FinAgentX — RAG Cache Layer (Fix #9)

- Embedding cache: hash(query) → cached vector
- Response cache: hash(query + context) → cached answer
- Async pipeline support
"""

from __future__ import annotations

import hashlib
import logging

from domain.interfaces import Cache
from infrastructure.observability.metrics import CACHE_HITS, CACHE_MISSES

logger = logging.getLogger(__name__)


class RAGCache:
    """
    Caching layer for the RAG pipeline.

    Prevents redundant LLM/embedding calls for repeated queries.
    Uses content-based hashing for deterministic cache keys.
    """

    def __init__(self, cache: Cache):
        self.cache = cache

    @staticmethod
    def _hash(content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def get_cached_response(
        self, query: str, context_hash: str
    ) -> str | None:
        """Check if a response is cached for this query + context."""
        key = f"rag:resp:{self._hash(f'{query}|{context_hash}')}"
        result = await self.cache.get(key)
        if result:
            CACHE_HITS.labels(cache_type="response").inc()
            logger.info("RAG response cache hit")
        else:
            CACHE_MISSES.labels(cache_type="response").inc()
        return result

    async def cache_response(
        self,
        query: str,
        context_hash: str,
        response: str,
        *,
        ttl_seconds: int = 1800,
    ) -> None:
        """Cache a response for a query + context combination."""
        key = f"rag:resp:{self._hash(f'{query}|{context_hash}')}"
        await self.cache.set(key, response, ttl_seconds=ttl_seconds)

    async def get_cached_retrieval(self, query: str) -> list[dict] | None:
        """Check if retrieval results are cached for this query."""
        key = f"rag:ret:{self._hash(query)}"
        result = await self.cache.get(key)
        if result:
            CACHE_HITS.labels(cache_type="retrieval").inc()
        else:
            CACHE_MISSES.labels(cache_type="retrieval").inc()
        return result

    async def cache_retrieval(
        self,
        query: str,
        results: list[dict],
        *,
        ttl_seconds: int = 3600,
    ) -> None:
        """Cache retrieval results for a query."""
        key = f"rag:ret:{self._hash(query)}"
        await self.cache.set(key, results, ttl_seconds=ttl_seconds)

    @staticmethod
    def compute_context_hash(chunks: list[str]) -> str:
        """Compute a hash of the retrieved context for cache keying."""
        combined = "|".join(sorted(chunks))
        return hashlib.sha256(combined.encode()).hexdigest()[:16]
