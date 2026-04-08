"""
FinAgentX — Hybrid Retriever (Fix #1, #2)

- Fix #1: Hybrid BM25 + dense search with RRF α=0.75
- Fix #2: Dynamic top-k (start high, reduce after rerank)
"""

from __future__ import annotations

import logging
from typing import Any

from domain.interfaces import VectorStore
from domain.schemas import RetrievalResult

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Hybrid retrieval: dense + BM25 via Weaviate with RRF.

    Two-stage approach:
    Stage 1: Cast wide net — retrieve top_k=20 with hybrid search
    Stage 2: Reranker narrows to top 8 (done by reranker module)
    """

    def __init__(
        self,
        vector_store: VectorStore,
        *,
        collection_name: str = "FinancialDocuments",
        default_alpha: float = 0.75,
        initial_top_k: int = 20,
    ):
        self.vector_store = vector_store
        self.collection_name = collection_name
        self.default_alpha = default_alpha
        self.initial_top_k = initial_top_k

    async def retrieve(
        self,
        query: str,
        *,
        alpha: float | None = None,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        """
        Execute hybrid retrieval.

        alpha=0.75 leans on dense for semantic matching,
        BM25 catches exact amounts/merchants/tickers.
        """
        actual_alpha = alpha or self.default_alpha
        actual_top_k = top_k or self.initial_top_k

        results = await self.vector_store.hybrid_search(
            self.collection_name,
            query,
            alpha=actual_alpha,
            top_k=actual_top_k,
            filters=filters,
        )

        logger.info(
            f"Retrieved {len(results)} results",
            extra={
                "query_preview": query[:80],
                "alpha": actual_alpha,
                "top_k": actual_top_k,
                "result_count": len(results),
            },
        )

        return results

    async def multi_query_retrieve(
        self,
        queries: list[str],
        *,
        alpha: float | None = None,
        top_k_per_query: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        """
        Fix #2: Multi-query retrieval — union results from all query variations.

        Deduplicates by chunk_id and keeps the highest score per chunk.
        """
        seen: dict[str, RetrievalResult] = {}

        for query in queries:
            results = await self.retrieve(
                query,
                alpha=alpha,
                top_k=top_k_per_query,
                filters=filters,
            )

            for result in results:
                cid = result.chunk.chunk_id
                if cid not in seen or result.score > seen[cid].score:
                    seen[cid] = result

        # Sort by score descending
        merged = sorted(seen.values(), key=lambda r: r.score, reverse=True)

        logger.info(
            f"Multi-query retrieval: {len(queries)} queries → "
            f"{len(merged)} unique results (deduped from {sum(1 for _ in queries) * top_k_per_query} max)",
        )

        return merged
