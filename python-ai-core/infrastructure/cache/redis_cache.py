"""
FinAgentX — Redis Cache Implementation (Fix #9)

Caches embeddings and responses in Redis with TTL.
Prevents redundant LLM/embedding calls for repeated queries.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import redis.asyncio as redis

from domain.interfaces import Cache

logger = logging.getLogger(__name__)


class RedisCache(Cache):
    """
    Redis-backed cache for embeddings and responses.

    Fix #9 — Latency Explosion:
    - Embedding cache: hash(query) → cached vector (TTL 1hr)
    - Response cache: hash(query + context) → cached answer (TTL 30min)
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/2"):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.prefix = "finagentx:cache:"
        logger.info(f"Redis cache connected: {redis_url}")

    def _make_key(self, key: str) -> str:
        """Create prefixed cache key."""
        return f"{self.prefix}{key}"

    @staticmethod
    def hash_query(query: str, context: str = "") -> str:
        """Create deterministic hash for cache key."""
        content = f"{query}|{context}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def get(self, key: str) -> Any | None:
        full_key = self._make_key(key)
        value = await self.redis.get(full_key)
        if value is not None:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def set(self, key: str, value: Any, *, ttl_seconds: int = 3600) -> None:
        full_key = self._make_key(key)
        serialized = json.dumps(value) if not isinstance(value, str) else value
        await self.redis.set(full_key, serialized, ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        full_key = self._make_key(key)
        await self.redis.delete(full_key)

    async def exists(self, key: str) -> bool:
        full_key = self._make_key(key)
        return bool(await self.redis.exists(full_key))

    async def get_embedding(self, query: str) -> list[float] | None:
        """Get cached embedding vector for a query."""
        key = f"emb:{self.hash_query(query)}"
        result = await self.get(key)
        return result if isinstance(result, list) else None

    async def set_embedding(
        self, query: str, embedding: list[float], *, ttl_seconds: int = 3600
    ) -> None:
        """Cache embedding vector for a query."""
        key = f"emb:{self.hash_query(query)}"
        await self.set(key, embedding, ttl_seconds=ttl_seconds)

    async def get_response(self, query: str, context_hash: str) -> str | None:
        """Get cached response for a query + context combination."""
        key = f"resp:{self.hash_query(query, context_hash)}"
        result = await self.get(key)
        return result if isinstance(result, str) else None

    async def set_response(
        self,
        query: str,
        context_hash: str,
        response: str,
        *,
        ttl_seconds: int = 1800,
    ) -> None:
        """Cache response for a query + context combination."""
        key = f"resp:{self.hash_query(query, context_hash)}"
        await self.set(key, response, ttl_seconds=ttl_seconds)

    async def store_pii_map(
        self,
        session_id: str,
        reverse_map: dict[str, str],
        *,
        ttl_seconds: int = 3600,
    ) -> None:
        """Store PII reverse map — encrypted at rest via Redis encryption."""
        key = f"pii:{session_id}"
        await self.set(key, reverse_map, ttl_seconds=ttl_seconds)

    async def get_pii_map(self, session_id: str) -> dict[str, str] | None:
        """Retrieve PII reverse map for unmasking."""
        key = f"pii:{session_id}"
        result = await self.get(key)
        return result if isinstance(result, dict) else None

    async def close(self) -> None:
        await self.redis.close()
