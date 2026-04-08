"""
FinAgentX — Domain Schemas (Zero External Dependencies)

All domain entities, value objects, and data transfer objects.
This module has NO external dependencies — pure Python + stdlib only.
Every other layer depends on this; this depends on nothing.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ─────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────

class QueryIntent(str, enum.Enum):
    """Classified intent of a financial query."""
    SPEND_ANALYSIS = "spend_analysis"
    ANOMALY = "anomaly"
    COMPARISON = "comparison"
    REPORT = "report"
    UNKNOWN = "unknown"


class AlertType(str, enum.Enum):
    """Types of anomaly alerts."""
    VOLUME_SPIKE = "VOLUME_SPIKE"
    PRICE_DEVIATION = "PRICE_DEVIATION"
    DAILY_CRASH = "DAILY_CRASH"
    DAILY_SURGE = "DAILY_SURGE"
    RECURRING_CHANGE = "RECURRING_CHANGE"
    HIGH_RISK_ACTIVITY = "HIGH_RISK_ACTIVITY"


class FeedbackType(str, enum.Enum):
    """Types of human feedback."""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    CORRECTION = "correction"


class ToolName(str, enum.Enum):
    """Available agent tools."""
    ANALYZE_SPEND = "analyze_spend"
    DETECT_ANOMALY = "detect_anomaly"
    RECOMMEND_ACTION = "recommend_action"
    GENERATE_REPORT = "generate_report"


# ─────────────────────────────────────────────
# Core Financial Entities
# ─────────────────────────────────────────────

@dataclass(frozen=True)
class Transaction:
    """Normalized financial transaction / market event."""
    event_id: str
    ticker: str
    date: str
    open_price: float
    high: float
    low: float
    close: float
    volume: int
    daily_return_pct: float
    volume_vs_30d_avg: float
    price_deviation_30d_pct: float
    sector: str
    industry: str
    high_risk: bool
    anomaly_flags: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class FinancialDocument:
    """A financial document ingested for RAG."""
    document_id: str
    ticker: str
    document_type: str  # income_statement, balance_sheet, cash_flow
    period: str
    text: str
    data: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, str] = field(default_factory=dict)


# ─────────────────────────────────────────────
# RAG Entities
# ─────────────────────────────────────────────

@dataclass
class Chunk:
    """A chunk of text extracted from a financial document."""
    chunk_id: str
    document_id: str
    text: str
    start_idx: int
    end_idx: int
    metadata: dict[str, Any] = field(default_factory=dict)
    # Parent-child hierarchy (Fix #2 — Recall Failure)
    parent_chunk_id: str | None = None
    child_chunk_ids: list[str] = field(default_factory=list)
    # Embedding versioning (Fix #4 — Embedding Drift)
    embedding_model: str = ""
    embedding_version: str = ""
    # Freshness (Fix #8 — Stale Knowledge Base)
    created_at: datetime | None = None
    freshness_score: float = 1.0  # decays over time


@dataclass
class ChunkMetadata:
    """Metadata attached to a chunk for filtering and attribution."""
    ticker: str = ""
    document_type: str = ""
    period: str = ""
    section: str = ""
    page_number: int = 0


@dataclass
class RetrievalResult:
    """Result from the retrieval pipeline."""
    chunk: Chunk
    score: float
    retrieval_method: str  # "dense", "sparse", "hybrid"
    rerank_score: float | None = None


@dataclass
class Citation:
    """Source attribution for a generated claim."""
    chunk_id: str
    document_id: str
    text: str
    relevance_score: float
    metadata: dict[str, str] = field(default_factory=dict)
    is_grounded: bool = True  # true if claim is grounded in this chunk


# ─────────────────────────────────────────────
# Agent Entities
# ─────────────────────────────────────────────

@dataclass
class ToolInput:
    """Input to an agent tool — validated against schema before execution."""
    tool_name: str
    parameters: dict[str, Any]
    session_id: str
    user_id: str


@dataclass
class ToolOutput:
    """Output from an agent tool — validated against schema after execution."""
    tool_name: str
    result: dict[str, Any]
    confidence: float
    latency_ms: int
    risk_flags: list[str] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    error: str | None = None


@dataclass
class TraceStep:
    """One step in an agent's reasoning trace."""
    step_id: str
    step_number: int
    tool_name: str
    input_json: str
    output_json: str
    latency_ms: int
    confidence: float
    reasoning: str
    risk_flags: list[str] = field(default_factory=list)


@dataclass
class AgentResponse:
    """Complete response from the agent orchestrator."""
    session_id: str
    answer: str
    steps: list[TraceStep]
    citations: list[Citation]
    confidence: float
    intent: QueryIntent
    total_latency_ms: int
    tokens_used: int
    requires_approval: bool = False


# ─────────────────────────────────────────────
# Structured Tool Outputs (Pydantic-validated at boundaries)
# ─────────────────────────────────────────────

@dataclass
class SpendAnalysis:
    """Output of analyze_spend tool."""
    ticker: str
    period: str
    total_revenue: float | None = None
    net_income: float | None = None
    operating_margin: float | None = None
    revenue_growth_pct: float | None = None
    key_metrics: dict[str, float] = field(default_factory=dict)
    summary: str = ""
    data_sources: list[str] = field(default_factory=list)


@dataclass
class AnomalyReport:
    """Output of detect_anomaly tool."""
    ticker: str
    alert_type: AlertType
    risk_score: float  # 0.0 - 1.0
    description: str
    evidence: list[str] = field(default_factory=list)
    affected_dates: list[str] = field(default_factory=list)
    recommended_action: str = ""
    data_sources: list[str] = field(default_factory=list)


@dataclass
class ActionRecommendation:
    """Output of recommend_action tool."""
    action: str
    rationale: str
    confidence: float
    risk_level: str  # low, medium, high, critical
    supporting_evidence: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    requires_human_approval: bool = False


@dataclass
class ReportOutput:
    """Output of generate_report tool."""
    title: str
    summary: str
    sections: list[dict[str, str]] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    risk_flags: list[str] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)


# ─────────────────────────────────────────────
# Evaluation Entities
# ─────────────────────────────────────────────

@dataclass
class EvalResult:
    """Result from LLM-as-judge evaluation."""
    correctness: float  # 0.0 - 1.0
    faithfulness: float  # 0.0 - 1.0
    hallucination_detected: bool
    grounded_claims: list[str] = field(default_factory=list)
    ungrounded_claims: list[str] = field(default_factory=list)
    reasoning: str = ""


@dataclass
class EvalMetrics:
    """Aggregate evaluation metrics for a test run."""
    eval_run_id: str
    total_cases: int
    avg_correctness: float
    avg_faithfulness: float
    hallucination_rate: float
    retrieval_precision_at_k: float
    retrieval_recall_at_k: float
    per_case_results: list[EvalResult] = field(default_factory=list)


# ─────────────────────────────────────────────
# Feedback Entities
# ─────────────────────────────────────────────

@dataclass
class FeedbackEntry:
    """Human-in-the-loop feedback entry."""
    feedback_id: str
    session_id: str
    user_id: str
    feedback_type: FeedbackType
    correction: str | None = None
    comment: str | None = None
    timestamp: datetime | None = None


@dataclass
class FeedbackStats:
    """Aggregate feedback statistics."""
    total_feedback: int
    positive: int
    negative: int
    corrections: int
    satisfaction_rate: float
    top_failure_queries: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────
# Embedding Version Tracking (Fix #4)
# ─────────────────────────────────────────────

@dataclass
class EmbeddingVersion:
    """Tracks which embedding model version is used for a collection."""
    model_name: str
    model_version: str
    embedding_dim: int
    created_at: datetime
    document_count: int
    is_current: bool = True


# ─────────────────────────────────────────────
# Authorization (Fix #13)
# ─────────────────────────────────────────────

@dataclass
class UserContext:
    """User context for retrieval-time authorization."""
    user_id: str
    roles: list[str] = field(default_factory=list)
    allowed_tickers: list[str] = field(default_factory=list)  # empty = all
    allowed_document_types: list[str] = field(default_factory=list)  # empty = all
    max_risk_level: str = "critical"  # low, medium, high, critical
