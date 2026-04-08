"""
FinAgentX — Synthetic Test Set Generator (Fix #14)

Generates evaluation test sets from existing documents.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


class SyntheticTestGenerator:
    """Generate synthetic QA pairs from financial documents for evaluation."""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def generate_test_cases(
        self,
        documents: list[str],
        n_per_document: int = 3,
    ) -> list[dict[str, Any]]:
        """Generate test QA pairs from document texts."""
        test_cases = []

        for doc_text in documents:
            messages = [
                SystemMessage(content=(
                    f"Generate {n_per_document} question-answer pairs from the following financial document.\n"
                    "Each pair should test understanding of specific financial data.\n"
                    "Return JSON: {\"pairs\": [{\"question\": \"...\", \"answer\": \"...\", \"difficulty\": \"easy|medium|hard\"}]}"
                )),
                HumanMessage(content=doc_text[:3000]),
            ]

            try:
                result = self.llm.invoke(
                    messages,
                    response_format={"type": "json_object"},
                )
                parsed = json.loads(result.content)
                pairs = parsed.get("pairs", [])

                for pair in pairs:
                    test_cases.append({
                        "test_id": uuid.uuid4().hex[:8],
                        "query": pair["question"],
                        "expected_answer": pair["answer"],
                        "difficulty": pair.get("difficulty", "medium"),
                        "source_document": doc_text[:200],
                    })
            except Exception as e:
                logger.warning(f"Failed to generate test cases: {e}")

        logger.info(f"Generated {len(test_cases)} synthetic test cases")
        return test_cases
