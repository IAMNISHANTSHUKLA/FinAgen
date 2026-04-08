"""
FinAgentX — Semantic Chunker (Fix #2, #3)

Handles all chunking failure modes:
- Fix #3: Semantic chunking (not fixed-size), overlap windows, document structure
- Fix #2: Parent-child chunking hierarchy for recall
"""

from __future__ import annotations

import hashlib
import logging
import re
import uuid
from datetime import datetime
from typing import Any

from domain.schemas import Chunk

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    Semantic document chunker for financial documents.

    Fix #3 — Chunking Failure:
    - Semantic boundaries (not fixed character count)
    - Overlap windows (20% overlap between chunks)
    - Document structure preservation (sections, headings)

    Fix #2 — Recall Failure:
    - Parent-child chunk hierarchy
    - Parent chunks: broader context for LLM
    - Child chunks: precise passages for retrieval
    """

    def __init__(
        self,
        *,
        max_chunk_size: int = 512,     # tokens (approximate)
        overlap_ratio: float = 0.2,     # 20% overlap
        min_chunk_size: int = 50,       # minimum viable chunk
        parent_multiplier: int = 3,     # parent = 3x child size
    ):
        self.max_chunk_size = max_chunk_size
        self.overlap_ratio = overlap_ratio
        self.min_chunk_size = min_chunk_size
        self.parent_multiplier = parent_multiplier

    def chunk_document(
        self,
        text: str,
        *,
        document_id: str,
        metadata: dict[str, Any] | None = None,
        embedding_model: str = "",
        embedding_version: str = "",
    ) -> list[Chunk]:
        """
        Chunk a financial document into semantic units with parent-child hierarchy.

        Returns both parent and child chunks:
        - Child chunks: used for precise retrieval
        - Parent chunks: used for broader context after retrieval
        """
        metadata = metadata or {}

        # Step 1: Split into sections based on document structure
        sections = self._split_into_sections(text)

        # Step 2: Create child chunks within each section
        child_chunks: list[Chunk] = []
        parent_chunks: list[Chunk] = []

        for section_name, section_text in sections:
            if len(section_text.strip()) < self.min_chunk_size:
                continue

            section_metadata = {**metadata, "section": section_name}

            # Create child chunks with overlap
            children = self._create_overlapping_chunks(
                section_text,
                document_id=document_id,
                metadata=section_metadata,
                embedding_model=embedding_model,
                embedding_version=embedding_version,
            )

            if not children:
                continue

            # Create parent chunk for this section (broader context)
            parent = Chunk(
                chunk_id=f"parent-{uuid.uuid4().hex[:8]}",
                document_id=document_id,
                text=section_text[:self.max_chunk_size * self.parent_multiplier],
                start_idx=0,
                end_idx=min(
                    len(section_text),
                    self.max_chunk_size * self.parent_multiplier,
                ),
                metadata=section_metadata,
                child_chunk_ids=[c.chunk_id for c in children],
                embedding_model=embedding_model,
                embedding_version=embedding_version,
                created_at=datetime.utcnow(),
            )

            # Link children to parent
            for child in children:
                child.parent_chunk_id = parent.chunk_id

            parent_chunks.append(parent)
            child_chunks.extend(children)

        all_chunks = parent_chunks + child_chunks
        logger.info(
            f"Chunked document into {len(parent_chunks)} parents + "
            f"{len(child_chunks)} children = {len(all_chunks)} total chunks",
            extra={
                "document_id": document_id,
                "parent_count": len(parent_chunks),
                "child_count": len(child_chunks),
            },
        )
        return all_chunks

    def _split_into_sections(self, text: str) -> list[tuple[str, str]]:
        """
        Split text into named sections based on document structure.

        Preserves headings, section breaks, and logical groupings.
        """
        # Pattern: lines that look like section headers
        section_pattern = re.compile(
            r'^(?:'
            r'(?:#{1,4}\s+.+)|'              # Markdown headers
            r'(?:[A-Z][A-Za-z\s&/]+:$)|'      # "Section Name:" format
            r'(?:[A-Z][A-Z\s]+$)'              # ALL CAPS lines
            r')',
            re.MULTILINE,
        )

        matches = list(section_pattern.finditer(text))

        if not matches:
            return [("main", text)]

        sections: list[tuple[str, str]] = []

        for i, match in enumerate(matches):
            section_name = match.group().strip().rstrip(":")
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_text = text[start:end].strip()

            if section_text:
                sections.append((section_name, section_text))

        # If first section starts after beginning, capture preamble
        if matches and matches[0].start() > 0:
            preamble = text[: matches[0].start()].strip()
            if preamble:
                sections.insert(0, ("preamble", preamble))

        return sections if sections else [("main", text)]

    def _create_overlapping_chunks(
        self,
        text: str,
        *,
        document_id: str,
        metadata: dict[str, Any],
        embedding_model: str,
        embedding_version: str,
    ) -> list[Chunk]:
        """
        Create chunks with semantic boundaries and overlap windows.

        Uses sentence boundaries rather than fixed character counts.
        Overlap ensures no information is lost at chunk boundaries.
        """
        # Split into sentences for semantic boundaries
        sentences = self._split_into_sentences(text)

        if not sentences:
            return []

        chunks: list[Chunk] = []
        current_sentences: list[str] = []
        current_length = 0
        overlap_sentences: list[str] = []

        for sentence in sentences:
            sentence_tokens = len(sentence) // 4  # approximate tokens

            if (
                current_length + sentence_tokens > self.max_chunk_size
                and current_sentences
            ):
                # Create chunk from accumulated sentences
                chunk_text = " ".join(current_sentences)
                start_idx = text.find(chunk_text[:50])

                chunk = Chunk(
                    chunk_id=f"chunk-{hashlib.md5(chunk_text.encode()).hexdigest()[:8]}",
                    document_id=document_id,
                    text=chunk_text,
                    start_idx=max(0, start_idx),
                    end_idx=max(0, start_idx) + len(chunk_text),
                    metadata=metadata,
                    embedding_model=embedding_model,
                    embedding_version=embedding_version,
                    created_at=datetime.utcnow(),
                )
                chunks.append(chunk)

                # Keep overlap_ratio of sentences for next chunk
                overlap_count = max(1, int(len(current_sentences) * self.overlap_ratio))
                overlap_sentences = current_sentences[-overlap_count:]
                current_sentences = list(overlap_sentences)
                current_length = sum(len(s) // 4 for s in current_sentences)

            current_sentences.append(sentence)
            current_length += sentence_tokens

        # Final chunk
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            if len(chunk_text) >= self.min_chunk_size:
                chunk = Chunk(
                    chunk_id=f"chunk-{hashlib.md5(chunk_text.encode()).hexdigest()[:8]}",
                    document_id=document_id,
                    text=chunk_text,
                    start_idx=max(0, text.find(chunk_text[:50])),
                    end_idx=len(text),
                    metadata=metadata,
                    embedding_model=embedding_model,
                    embedding_version=embedding_version,
                    created_at=datetime.utcnow(),
                )
                chunks.append(chunk)

        return chunks

    @staticmethod
    def _split_into_sentences(text: str) -> list[str]:
        """Split text into sentences using regex-based boundary detection."""
        # Financial text often has: $1,234.56, Q3 2024, etc.
        # Need to avoid splitting on decimal points and abbreviations
        sentence_endings = re.compile(
            r'(?<=[.!?])\s+(?=[A-Z])|'  # Standard sentence boundary
            r'(?<=\n)\s*(?=\S)|'         # Newline boundaries
            r'(?<=:)\s*\n'               # Colon + newline
        )

        sentences = sentence_endings.split(text)
        return [s.strip() for s in sentences if s.strip()]
