"""
FinAgentX — RAG Query Engine (Fix #1, #2, #11)

Handles query understanding before retrieval:
- Fix #1:  LLM-based query rewriting for better retrieval
- Fix #2:  Multi-query retrieval (generate query variations)
- Fix #11: Query classifier + intent detection
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from domain.schemas import QueryIntent

logger = logging.getLogger(__name__)


class QueryEngine:
    """
    Pre-retrieval query processing engine.

    Pipeline: raw query → classify intent → rewrite for retrieval → generate variations
    """

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def classify_intent(self, query: str) -> QueryIntent:
        """
        Fix #11: Classify query intent for routing and filtering.

        Intents:
        - spend_analysis: revenue, costs, margins, ratios
        - anomaly: spikes, crashes, unusual activity
        - comparison: compare tickers/periods
        - report: comprehensive analysis/summary
        """
        messages = [
            SystemMessage(content=(
                "You are a financial query classifier. Classify the query into exactly one category.\n"
                "Categories: spend_analysis, anomaly, comparison, report\n"
                "Respond with ONLY the category name, nothing else."
            )),
            HumanMessage(content=query),
        ]

        try:
            result = self.llm.invoke(messages)
            intent_str = result.content.strip().lower()

            intent_map = {
                "spend_analysis": QueryIntent.SPEND_ANALYSIS,
                "anomaly": QueryIntent.ANOMALY,
                "comparison": QueryIntent.COMPARISON,
                "report": QueryIntent.REPORT,
            }
            intent = intent_map.get(intent_str, QueryIntent.UNKNOWN)
            logger.info(f"Query classified as: {intent.value}", extra={"intent": intent.value})
            return intent
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}, defaulting to UNKNOWN")
            return QueryIntent.UNKNOWN

    def rewrite_query(self, query: str, intent: QueryIntent) -> str:
        """
        Fix #1: LLM-based query rewriting for improved retrieval.

        Transforms user query into a retrieval-optimized version that
        captures the core information need with precise financial terminology.
        """
        messages = [
            SystemMessage(content=(
                "You are a financial search query optimizer. "
                "Rewrite the user's query to be more effective for retrieving relevant financial documents.\n"
                "Rules:\n"
                "1. Use precise financial terminology\n"
                "2. Include relevant ticker symbols, dates, and metrics\n"
                "3. Keep it concise (1-2 sentences)\n"
                "4. Preserve the original intent\n"
                "Respond with ONLY the rewritten query."
            )),
            HumanMessage(content=f"Intent: {intent.value}\nOriginal query: {query}"),
        ]

        try:
            result = self.llm.invoke(messages)
            rewritten = result.content.strip()
            logger.info(
                "Query rewritten",
                extra={"original": query, "rewritten": rewritten},
            )
            return rewritten
        except Exception as e:
            logger.warning(f"Query rewriting failed: {e}, using original query")
            return query

    def generate_query_variations(self, query: str, n: int = 3) -> list[str]:
        """
        Fix #2: Multi-query retrieval — generate N variations of the query.

        Each variation captures a different aspect of the information need.
        Results from all variations are unioned before reranking.
        """
        messages = [
            SystemMessage(content=(
                f"Generate {n} alternative versions of the following financial query. "
                "Each version should approach the question from a different angle "
                "while preserving the core information need.\n"
                "Return as a JSON array of strings. Example: [\"query1\", \"query2\", \"query3\"]"
            )),
            HumanMessage(content=query),
        ]

        try:
            result = self.llm.invoke(
                messages,
                response_format={"type": "json_object"},
            )
            # Parse JSON array from response
            content = result.content.strip()
            # Handle both direct array and wrapped object
            parsed = json.loads(content)
            if isinstance(parsed, list):
                variations = parsed
            elif isinstance(parsed, dict):
                # Find the array value
                for value in parsed.values():
                    if isinstance(value, list):
                        variations = value
                        break
                else:
                    variations = []
            else:
                variations = []

            # Always include original query
            all_queries = [query] + variations[:n]
            logger.info(
                f"Generated {len(all_queries)} query variations",
                extra={"variations": all_queries},
            )
            return all_queries

        except Exception as e:
            logger.warning(f"Query variation generation failed: {e}")
            return [query]

    async def process_query(
        self,
        query: str,
        *,
        enable_rewrite: bool = True,
        enable_multi_query: bool = True,
    ) -> dict[str, Any]:
        """
        Full query processing pipeline.

        Returns:
            {
                "original_query": str,
                "intent": QueryIntent,
                "rewritten_query": str,
                "query_variations": list[str],
            }
        """
        intent = self.classify_intent(query)

        rewritten = self.rewrite_query(query, intent) if enable_rewrite else query

        variations = (
            self.generate_query_variations(rewritten)
            if enable_multi_query
            else [rewritten]
        )

        return {
            "original_query": query,
            "intent": intent,
            "rewritten_query": rewritten,
            "query_variations": variations,
        }
