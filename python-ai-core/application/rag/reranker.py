"""
FinAgentX — Reranker + Context Compression (Fix #5, #12)

- Fix #5:  Context compression + token budgeting
- Fix #12: Two-stage retrieval with neural reranking
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from domain.interfaces import Reranker
from domain.schemas import RetrievalResult

logger = logging.getLogger(__name__)


class RerankerPipeline:
    """
    Reranking + context compression pipeline.

    Stage 1: Neural reranking (cross-encoder) narrows candidates
    Stage 2: Context compression ensures token budget compliance
    Stage 3: Token budgeting enforces hard limit
    """

    def __init__(
        self,
        reranker: Reranker,
        llm: BaseChatModel,
        *,
        token_budget: int = 4096,
        rerank_top_k: int = 8,
    ):
        self.reranker = reranker
        self.llm = llm
        self.token_budget = token_budget
        self.rerank_top_k = rerank_top_k

    async def process(
        self,
        query: str,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """
        Full reranking + compression pipeline.

        1. Rerank top candidates
        2. Check token budget
        3. Compress if over budget
        """
        # Step 1: Neural reranking
        reranked = await self.reranker.rerank(
            query, results, top_k=self.rerank_top_k
        )

        # Step 2: Token budget check
        total_tokens = sum(
            self._estimate_tokens(r.chunk.text) for r in reranked
        )

        if total_tokens <= self.token_budget:
            logger.info(
                f"Context within budget: {total_tokens}/{self.token_budget} tokens"
            )
            return reranked

        # Step 3: Compress chunks that push over budget
        logger.info(
            f"Context over budget: {total_tokens}/{self.token_budget} tokens, compressing..."
        )
        compressed = await self._compress_context(query, reranked)

        return compressed

    async def _compress_context(
        self,
        query: str,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        """
        Fix #5: Context compression — summarize chunks that exceed token budget.

        Keeps high-relevance chunks intact, compresses lower-relevance ones.
        """
        compressed: list[RetrievalResult] = []
        running_tokens = 0

        for i, result in enumerate(results):
            chunk_tokens = self._estimate_tokens(result.chunk.text)

            if running_tokens + chunk_tokens <= self.token_budget:
                # Fits in budget — keep as-is
                compressed.append(result)
                running_tokens += chunk_tokens
            elif running_tokens < self.token_budget * 0.9:
                # Over budget but have room — compress this chunk
                remaining_budget = self.token_budget - running_tokens
                compressed_text = await self._summarize_chunk(
                    query, result.chunk.text, max_tokens=remaining_budget
                )
                result.chunk.text = compressed_text
                compressed.append(result)
                running_tokens += self._estimate_tokens(compressed_text)
            else:
                # Budget exhausted — skip remaining
                logger.info(
                    f"Budget exhausted at chunk {i+1}/{len(results)}, "
                    f"dropping {len(results) - i} chunks"
                )
                break

        return compressed

    async def _summarize_chunk(
        self,
        query: str,
        text: str,
        *,
        max_tokens: int = 200,
    ) -> str:
        """Summarize a chunk to fit within token budget."""
        messages = [
            SystemMessage(content=(
                "Compress the following financial text while preserving all facts, "
                "numbers, and data relevant to the query. "
                "Remove redundant narrative but keep all quantitative information."
            )),
            HumanMessage(content=f"Query: {query}\n\nText to compress:\n{text}"),
        ]

        try:
            result = self.llm.invoke(messages, max_tokens=max_tokens)
            return result.content.strip()
        except Exception as e:
            logger.warning(f"Chunk compression failed: {e}, truncating instead")
            return text[: max_tokens * 4]  # Rough truncation fallback

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Approximate token count (4 chars ≈ 1 token for LLaMA-family)."""
        return len(text) // 4
