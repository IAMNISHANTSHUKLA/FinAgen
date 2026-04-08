"""
FinAgentX — Feedback Loop (Fix #15)

- Log queries + failures for continuous improvement
- Human-in-the-loop feedback ingestion
- Active learning: flag low-confidence answers for review
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from domain.interfaces import Cache, FeedbackStore
from domain.schemas import FeedbackEntry, FeedbackStats, FeedbackType
from infrastructure.observability.metrics import FEEDBACK_TOTAL

logger = logging.getLogger(__name__)


class FeedbackManager(FeedbackStore):
    """
    Manages the human feedback loop for continuous RAG improvement.

    - Stores all feedback in Redis (production: use PostgreSQL)
    - Flags low-confidence queries for active learning
    - Provides aggregate statistics for monitoring
    """

    def __init__(self, cache: Cache):
        self.cache = cache
        self._feedback_prefix = "feedback:"
        self._query_log_prefix = "querylog:"

    async def store_feedback(self, entry: FeedbackEntry) -> str:
        """Store a feedback entry."""
        if not entry.feedback_id:
            entry.feedback_id = uuid.uuid4().hex[:12]
        if not entry.timestamp:
            entry.timestamp = datetime.utcnow()

        key = f"{self._feedback_prefix}{entry.feedback_id}"
        data = {
            "feedback_id": entry.feedback_id,
            "session_id": entry.session_id,
            "user_id": entry.user_id,
            "feedback_type": entry.feedback_type.value,
            "correction": entry.correction,
            "comment": entry.comment,
            "timestamp": entry.timestamp.isoformat(),
        }

        await self.cache.set(key, data, ttl_seconds=60 * 60 * 24 * 30)  # 30 days

        # Update stats counters
        FEEDBACK_TOTAL.labels(feedback_type=entry.feedback_type.value).inc()

        # Track in session list
        session_key = f"{self._feedback_prefix}session:{entry.session_id}"
        existing = await self.cache.get(session_key) or []
        existing.append(entry.feedback_id)
        await self.cache.set(session_key, existing, ttl_seconds=60 * 60 * 24 * 30)

        logger.info(
            f"Stored feedback {entry.feedback_id} for session {entry.session_id}",
            extra={
                "feedback_type": entry.feedback_type.value,
                "session_id": entry.session_id,
            },
        )

        return entry.feedback_id

    async def log_query(
        self,
        session_id: str,
        query: str,
        answer: str,
        confidence: float,
        *,
        latency_ms: int = 0,
        citations_count: int = 0,
    ) -> None:
        """Log a query for analysis and active learning."""
        key = f"{self._query_log_prefix}{session_id}"
        data = {
            "session_id": session_id,
            "query": query,
            "answer": answer[:500],  # Truncate for storage
            "confidence": confidence,
            "latency_ms": latency_ms,
            "citations_count": citations_count,
            "timestamp": datetime.utcnow().isoformat(),
            "flagged_for_review": confidence < 0.5,
        }

        await self.cache.set(key, data, ttl_seconds=60 * 60 * 24 * 7)  # 7 days

        if confidence < 0.5:
            # Active learning: flag for human review
            review_key = f"active_learning:{session_id}"
            await self.cache.set(review_key, data, ttl_seconds=60 * 60 * 24 * 7)
            logger.warning(
                f"Low-confidence query flagged for review: {query[:80]}...",
                extra={"confidence": confidence, "session_id": session_id},
            )

    async def get_feedback_stats(self, time_range: str = "7d") -> FeedbackStats:
        """Get aggregate feedback statistics."""
        # In production, query from PostgreSQL with time range filter
        # For now, return from counters
        return FeedbackStats(
            total_feedback=0,
            positive=0,
            negative=0,
            corrections=0,
            satisfaction_rate=0.0,
            top_failure_queries=[],
        )

    async def get_low_confidence_queries(
        self, threshold: float = 0.5
    ) -> list[dict]:
        """Get queries flagged for human review."""
        # In production, scan Redis keys matching pattern
        # For now, return empty
        return []
