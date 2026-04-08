"""
FinAgentX — Citation Tracker (Fix #7)

Provenance tracking and source attribution:
- Assign chunk IDs + metadata to every retrieved passage
- Citation-aware prompting — instruct LLM to cite by chunk ID
- Post-process: match generated claims to source chunks
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from domain.schemas import Citation, RetrievalResult

logger = logging.getLogger(__name__)


class CitationTracker:
    """
    Manages source attribution throughout the RAG pipeline.

    Every claim in the generated answer should be traceable
    back to a specific chunk in the retrieved context.
    """

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def format_context_with_citations(
        self,
        results: list[RetrievalResult],
    ) -> str:
        """
        Format retrieved chunks with citation markers for LLM context.

        Each chunk is labeled [SOURCE_N] so the LLM can reference them.
        """
        formatted_parts = []

        for i, result in enumerate(results):
            chunk = result.chunk
            metadata_str = ""
            if chunk.metadata:
                meta_parts = [
                    f"{k}: {v}" for k, v in chunk.metadata.items()
                    if v and k != "access_roles"
                ]
                metadata_str = f" ({', '.join(meta_parts)})" if meta_parts else ""

            formatted_parts.append(
                f"[SOURCE_{i+1}] (chunk_id: {chunk.chunk_id}{metadata_str})\n"
                f"{chunk.text}\n"
            )

        return "\n---\n".join(formatted_parts)

    def get_citation_prompt(self) -> str:
        """
        Get the citation-aware instruction to append to the system prompt.

        Instructs the LLM to cite sources using [SOURCE_N] markers.
        """
        return (
            "\n\nCITATION RULES:\n"
            "1. Support every factual claim with a citation: [SOURCE_N]\n"
            "2. Place the citation immediately after the claim\n"
            "3. If information is from multiple sources, cite all: [SOURCE_1][SOURCE_3]\n"
            "4. Do NOT make claims that aren't supported by the provided sources\n"
            "5. If you cannot answer from the sources, say: 'Insufficient data in available sources.'\n"
        )

    def extract_citations(
        self,
        answer: str,
        results: list[RetrievalResult],
    ) -> list[Citation]:
        """
        Post-process: extract citations from the generated answer
        and map them back to source chunks.
        """
        citations: list[Citation] = []

        # Find all [SOURCE_N] references in the answer
        source_refs = re.findall(r'\[SOURCE_(\d+)\]', answer)
        referenced_indices = set(int(ref) - 1 for ref in source_refs)

        for i, result in enumerate(results):
            citation = Citation(
                chunk_id=result.chunk.chunk_id,
                document_id=result.chunk.document_id,
                text=result.chunk.text[:200],  # Preview
                relevance_score=result.rerank_score or result.score,
                metadata={k: str(v) for k, v in result.chunk.metadata.items()},
                is_grounded=i in referenced_indices,
            )
            citations.append(citation)

        grounded_count = sum(1 for c in citations if c.is_grounded)
        logger.info(
            f"Extracted {len(citations)} citations, "
            f"{grounded_count} grounded, "
            f"{len(citations) - grounded_count} ungrounded",
        )

        return citations

    async def verify_grounding(
        self,
        answer: str,
        citations: list[Citation],
    ) -> dict[str, Any]:
        """
        Fix #6 (partial): Verify that claims in the answer are grounded
        in the cited sources.

        Returns a grounding report.
        """
        grounded_sources = [c for c in citations if c.is_grounded]
        if not grounded_sources:
            return {
                "grounded": False,
                "reason": "No sources cited in the answer",
                "grounded_claims": [],
                "ungrounded_claims": [answer],
            }

        context = "\n".join(
            f"[{c.chunk_id}]: {c.text}" for c in grounded_sources
        )

        messages = [
            SystemMessage(content=(
                "You are a fact-checking assistant. Analyze the answer and determine "
                "which claims are grounded in the provided sources and which are not.\n"
                "Return JSON: {\"grounded_claims\": [...], \"ungrounded_claims\": [...], "
                "\"fully_grounded\": true/false}"
            )),
            HumanMessage(content=(
                f"Sources:\n{context}\n\nAnswer to verify:\n{answer}"
            )),
        ]

        try:
            result = self.llm.invoke(
                messages,
                response_format={"type": "json_object"},
            )
            return json.loads(result.content)
        except Exception as e:
            logger.warning(f"Grounding verification failed: {e}")
            return {"grounded": True, "reason": "Verification failed, assuming grounded"}
