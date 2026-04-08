"""
FinAgentX — Cross-Encoder Reranker (Fix #5, #12)

Two-stage retrieval: fast sparse/dense retrieval → precise neural reranking.
Uses cross-encoder models (BGE, ms-marco) for fine-grained relevance scoring.
"""

from __future__ import annotations

import logging
from typing import Any

from sentence_transformers import CrossEncoder

from domain.interfaces import Reranker
from domain.schemas import RetrievalResult

logger = logging.getLogger(__name__)


class CrossEncoderReranker(Reranker):
    """
    Neural reranker using cross-encoder model.

    Two-stage retrieval (Fix #12):
    Stage 1: Fast retrieval (BM25 + dense) → top 20 candidates
    Stage 2: Cross-encoder reranks → top 8 for LLM context
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device: str = "cpu",
    ):
        self.model = CrossEncoder(model_name, device=device)
        self.model_name = model_name
        logger.info(f"Cross-encoder reranker loaded: {model_name}")

    async def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        *,
        top_k: int = 8,
    ) -> list[RetrievalResult]:
        """Rerank retrieval results using cross-encoder scoring."""
        if not results:
            return []

        # Prepare query-document pairs for cross-encoder
        pairs = [(query, r.chunk.text) for r in results]

        # Score all pairs
        scores = self.model.predict(pairs)

        # Assign rerank scores
        for result, score in zip(results, scores):
            result.rerank_score = float(score)

        # Sort by rerank score (descending) and take top_k
        reranked = sorted(results, key=lambda r: r.rerank_score or 0, reverse=True)
        top_results = reranked[:top_k]

        logger.info(
            f"Reranked {len(results)} → {len(top_results)} results",
            extra={
                "input_count": len(results),
                "output_count": len(top_results),
                "top_score": top_results[0].rerank_score if top_results else 0,
            },
        )

        return top_results
