"""
FinAgentX — Evaluation Metrics (Fix #14)

Retrieval precision@k, recall@k, faithfulness score, hallucination rate.
"""

from __future__ import annotations

import logging
from typing import Any

from domain.schemas import EvalMetrics, EvalResult

logger = logging.getLogger(__name__)


def precision_at_k(
    retrieved_ids: list[str],
    relevant_ids: list[str],
    k: int,
) -> float:
    """Compute precision@k."""
    if not retrieved_ids or k == 0:
        return 0.0
    top_k = retrieved_ids[:k]
    relevant_in_top_k = sum(1 for rid in top_k if rid in relevant_ids)
    return relevant_in_top_k / k


def recall_at_k(
    retrieved_ids: list[str],
    relevant_ids: list[str],
    k: int,
) -> float:
    """Compute recall@k."""
    if not relevant_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    relevant_in_top_k = sum(1 for rid in top_k if rid in relevant_ids)
    return relevant_in_top_k / len(relevant_ids)


def compute_hallucination_rate(results: list[EvalResult]) -> float:
    """Compute overall hallucination rate from evaluation results."""
    if not results:
        return 0.0
    hallucinated = sum(1 for r in results if r.hallucination_detected)
    return hallucinated / len(results)


def aggregate_metrics(
    eval_run_id: str,
    results: list[EvalResult],
    retrieval_precision: float = 0.0,
    retrieval_recall: float = 0.0,
) -> EvalMetrics:
    """Aggregate per-case results into overall metrics."""
    if not results:
        return EvalMetrics(
            eval_run_id=eval_run_id,
            total_cases=0,
            avg_correctness=0.0,
            avg_faithfulness=0.0,
            hallucination_rate=0.0,
            retrieval_precision_at_k=0.0,
            retrieval_recall_at_k=0.0,
        )

    return EvalMetrics(
        eval_run_id=eval_run_id,
        total_cases=len(results),
        avg_correctness=sum(r.correctness for r in results) / len(results),
        avg_faithfulness=sum(r.faithfulness for r in results) / len(results),
        hallucination_rate=compute_hallucination_rate(results),
        retrieval_precision_at_k=retrieval_precision,
        retrieval_recall_at_k=retrieval_recall,
        per_case_results=results,
    )
