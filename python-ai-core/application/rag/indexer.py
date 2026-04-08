"""
FinAgentX — Incremental Indexer (Fix #8)

- Incremental indexing — only process new/modified documents
- TTL/freshness scoring — decay score for old documents
- Event-driven ingestion — listen for new document events
"""

from __future__ import annotations

import hashlib
import logging
import math
from datetime import datetime, timedelta
from typing import Any

from domain.schemas import Chunk

logger = logging.getLogger(__name__)


class IncrementalIndexer:
    """
    Manages incremental document indexing with freshness scoring.

    Documents are only re-indexed when their content hash changes.
    Freshness scores decay over time — queries favor recent data.
    """

    def __init__(
        self,
        *,
        freshness_decay_days: int = 90,
        freshness_min_score: float = 0.3,
    ):
        # In-memory hash registry (production: use Redis or DB)
        self._document_hashes: dict[str, str] = {}
        self.freshness_decay_days = freshness_decay_days
        self.freshness_min_score = freshness_min_score

    def needs_indexing(self, document_id: str, content: str) -> bool:
        """Check if a document needs (re-)indexing based on content hash."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        stored_hash = self._document_hashes.get(document_id)

        if stored_hash == content_hash:
            logger.debug(f"Document {document_id} unchanged, skipping.")
            return False

        return True

    def mark_indexed(self, document_id: str, content: str) -> None:
        """Mark a document as indexed with its content hash."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        self._document_hashes[document_id] = content_hash
        logger.info(f"Indexed document {document_id} (hash: {content_hash[:12]})")

    def compute_freshness_score(
        self,
        document_date: datetime | str,
        reference_date: datetime | None = None,
    ) -> float:
        """
        Compute freshness score based on document age.

        Uses exponential decay: score = max(min_score, e^(-age/decay))
        Newer documents score higher → queries favor recent data.
        """
        ref = reference_date or datetime.utcnow()

        if isinstance(document_date, str):
            try:
                document_date = datetime.fromisoformat(document_date)
            except ValueError:
                return 1.0  # Can't parse, assume fresh

        age_days = (ref - document_date).days
        if age_days <= 0:
            return 1.0

        # Exponential decay
        decay_rate = self.freshness_decay_days
        score = math.exp(-age_days / decay_rate)

        return max(self.freshness_min_score, score)

    def apply_freshness_to_chunks(
        self,
        chunks: list[Chunk],
        document_date: datetime | str,
    ) -> list[Chunk]:
        """Apply freshness scores to all chunks from a document."""
        freshness = self.compute_freshness_score(document_date)

        for chunk in chunks:
            chunk.freshness_score = freshness

        logger.info(
            f"Applied freshness score {freshness:.3f} to {len(chunks)} chunks"
        )
        return chunks

    def get_indexing_stats(self) -> dict[str, Any]:
        """Return indexing statistics."""
        return {
            "total_documents_indexed": len(self._document_hashes),
            "freshness_decay_days": self.freshness_decay_days,
            "freshness_min_score": self.freshness_min_score,
        }
