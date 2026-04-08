"""
FinAgentX — Prometheus Observability Metrics

Exports production metrics in Prometheus format:
- Query latency (p50/p95/p99)
- Token usage
- Error rates
- Hallucination frequency
- Cache hit rates
- Tool call distribution
- Retrieval precision
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, Info

# ─────────────────────────────────────────────
# Application Info
# ─────────────────────────────────────────────

APP_INFO = Info(
    "finagentx",
    "FinAgentX AI Core service information",
)
APP_INFO.info({
    "version": "1.0.0",
    "service": "python-ai-core",
})

# ─────────────────────────────────────────────
# Query Metrics
# ─────────────────────────────────────────────

QUERY_DURATION = Histogram(
    "finagentx_query_duration_seconds",
    "End-to-end query processing duration",
    ["intent", "status"],
    buckets=[0.5, 1, 2, 5, 10, 15, 30, 60],
)

QUERIES_TOTAL = Counter(
    "finagentx_queries_total",
    "Total number of queries processed",
    ["intent", "status"],
)

# ─────────────────────────────────────────────
# LLM Metrics
# ─────────────────────────────────────────────

TOKENS_TOTAL = Counter(
    "finagentx_tokens_total",
    "Total tokens consumed",
    ["model", "type"],  # type: prompt, completion
)

LLM_LATENCY = Histogram(
    "finagentx_llm_latency_seconds",
    "LLM call latency",
    ["model", "operation"],  # operation: generate, structured, judge
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
)

LLM_ERRORS = Counter(
    "finagentx_llm_errors_total",
    "LLM call errors",
    ["model", "error_type"],
)

# ─────────────────────────────────────────────
# Tool Metrics
# ─────────────────────────────────────────────

TOOL_CALLS_TOTAL = Counter(
    "finagentx_tool_calls_total",
    "Total tool invocations",
    ["tool_name", "status"],
)

TOOL_LATENCY = Histogram(
    "finagentx_tool_latency_seconds",
    "Tool execution latency",
    ["tool_name"],
    buckets=[0.1, 0.5, 1, 2, 5, 10],
)

# ─────────────────────────────────────────────
# RAG Metrics
# ─────────────────────────────────────────────

RETRIEVAL_LATENCY = Histogram(
    "finagentx_retrieval_latency_seconds",
    "Retrieval pipeline latency",
    ["stage"],  # stage: search, rerank, compress
    buckets=[0.05, 0.1, 0.25, 0.5, 1, 2, 5],
)

RETRIEVAL_PRECISION = Gauge(
    "finagentx_retrieval_precision_at_k",
    "Retrieval precision@k from evaluation",
    ["k"],
)

CHUNKS_RETRIEVED = Histogram(
    "finagentx_chunks_retrieved",
    "Number of chunks retrieved per query",
    buckets=[1, 3, 5, 8, 10, 15, 20],
)

# ─────────────────────────────────────────────
# Safety Metrics
# ─────────────────────────────────────────────

HALLUCINATIONS_TOTAL = Counter(
    "finagentx_hallucinations_total",
    "Total hallucination events detected",
)

PII_MASKED = Counter(
    "finagentx_pii_masked_total",
    "Total PII entities masked",
    ["entity_type"],
)

GUARDRAIL_TRIGGERS = Counter(
    "finagentx_guardrail_triggers_total",
    "Guardrail trigger events",
    ["guardrail_type"],  # loop_detected, max_steps, timeout, human_approval
)

# ─────────────────────────────────────────────
# Cache Metrics
# ─────────────────────────────────────────────

CACHE_HITS = Counter(
    "finagentx_cache_hits_total",
    "Cache hit count",
    ["cache_type"],  # embedding, response
)

CACHE_MISSES = Counter(
    "finagentx_cache_misses_total",
    "Cache miss count",
    ["cache_type"],
)

# ─────────────────────────────────────────────
# Feedback Metrics
# ─────────────────────────────────────────────

FEEDBACK_TOTAL = Counter(
    "finagentx_feedback_total",
    "Total feedback entries received",
    ["feedback_type"],
)

# ─────────────────────────────────────────────
# Error Metrics
# ─────────────────────────────────────────────

ERRORS_TOTAL = Counter(
    "finagentx_errors_total",
    "Total errors by type and service",
    ["service", "error_type"],
)
