"""
FinAgentX — Agent Tools

Domain-specific financial tools with typed I/O schemas.
Each tool: typed input, typed output, latency budget (10s).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from application.rag.retriever import HybridRetriever
from domain.schemas import AlertType

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Tool Input/Output Pydantic Schemas
# ─────────────────────────────────────────────

class AnalyzeSpendInput(BaseModel):
    ticker: str = Field(description="Stock ticker symbol")
    period: str = Field(default="latest", description="Time period: latest, Q1-Q4, or YYYY")
    metrics: list[str] = Field(
        default=["revenue", "net_income", "operating_margin"],
        description="Financial metrics to analyze",
    )

class AnalyzeSpendOutput(BaseModel):
    ticker: str
    period: str
    metrics: dict[str, float | None]
    summary: str
    data_sources: list[str]

class DetectAnomalyInput(BaseModel):
    ticker: str = Field(description="Ticker to check for anomalies")
    lookback_days: int = Field(default=30, description="Days to look back")
    threshold_multiplier: float = Field(default=3.0, description="Spike threshold")

class DetectAnomalyOutput(BaseModel):
    ticker: str
    anomalies_found: int
    alerts: list[dict[str, Any]]
    risk_score: float = Field(ge=0, le=1)
    summary: str

class RecommendActionInput(BaseModel):
    ticker: str
    risk_flags: list[str] = Field(default_factory=list)
    context: str = Field(default="", description="Additional context")

class RecommendActionOutput(BaseModel):
    action: str
    rationale: str
    confidence: float = Field(ge=0, le=1)
    risk_level: str
    caveats: list[str]
    requires_human_approval: bool

class GenerateReportInput(BaseModel):
    ticker: str
    report_type: str = Field(default="comprehensive", description="Type: comprehensive, risk, earnings")
    include_sections: list[str] = Field(
        default=["overview", "financials", "risk", "recommendation"]
    )

class GenerateReportOutput(BaseModel):
    title: str
    sections: list[dict[str, str]]
    risk_flags: list[str]
    summary: str


# ─────────────────────────────────────────────
# Tool Implementations
# ─────────────────────────────────────────────

async def analyze_spend_impl(
    ticker: str,
    period: str = "latest",
    metrics: list[str] | None = None,
    retriever: HybridRetriever | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Analyze financial spend/metrics for a ticker."""
    metrics = metrics or ["revenue", "net_income", "operating_margin"]

    query = f"{ticker} financial metrics {' '.join(metrics)} for {period}"
    retrieved = []
    if retriever:
        results = await retriever.retrieve(
            query, filters={"ticker": ticker}
        )
        retrieved = [r.chunk.text for r in results[:5]]

    logger.info(f"analyze_spend: {ticker} {period}, {len(retrieved)} sources")

    return AnalyzeSpendOutput(
        ticker=ticker,
        period=period,
        metrics={m: None for m in metrics},
        summary=f"Analysis of {ticker} for {period} based on {len(retrieved)} sources.",
        data_sources=[f"source_{i}" for i in range(len(retrieved))],
    ).model_dump()


async def detect_anomaly_impl(
    ticker: str,
    lookback_days: int = 30,
    threshold_multiplier: float = 3.0,
    retriever: HybridRetriever | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Detect anomalies in a ticker's trading data."""
    query = f"{ticker} volume spike price crash anomaly unusual activity"
    retrieved = []
    if retriever:
        results = await retriever.retrieve(
            query, filters={"ticker": ticker}
        )
        retrieved = results[:5]

    alerts = []
    for r in retrieved:
        chunk_meta = r.chunk.metadata
        if "VOLUME_SPIKE" in str(chunk_meta) or "CRASH" in str(chunk_meta):
            alerts.append({
                "type": AlertType.VOLUME_SPIKE.value,
                "source": r.chunk.chunk_id,
                "score": r.score,
            })

    risk_score = min(1.0, len(alerts) * 0.2) if alerts else 0.1

    return DetectAnomalyOutput(
        ticker=ticker,
        anomalies_found=len(alerts),
        alerts=alerts,
        risk_score=risk_score,
        summary=f"Found {len(alerts)} anomalies for {ticker} in last {lookback_days} days.",
    ).model_dump()


async def recommend_action_impl(
    ticker: str,
    risk_flags: list[str] | None = None,
    context: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """Recommend actions based on risk analysis."""
    risk_flags = risk_flags or []
    requires_approval = len(risk_flags) > 2 or any("CRASH" in f for f in risk_flags)
    confidence = max(0.3, 1.0 - len(risk_flags) * 0.15)

    risk_level = "low"
    if len(risk_flags) > 3:
        risk_level = "critical"
    elif len(risk_flags) > 2:
        risk_level = "high"
    elif len(risk_flags) > 0:
        risk_level = "medium"

    return RecommendActionOutput(
        action=f"Monitor {ticker} closely" if risk_flags else f"No action needed for {ticker}",
        rationale=f"Based on {len(risk_flags)} risk flags: {', '.join(risk_flags[:3])}",
        confidence=confidence,
        risk_level=risk_level,
        caveats=["This is an automated recommendation", "Verify with domain expert"],
        requires_human_approval=requires_approval,
    ).model_dump()


async def generate_report_impl(
    ticker: str,
    report_type: str = "comprehensive",
    include_sections: list[str] | None = None,
    retriever: HybridRetriever | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Generate a financial report for a ticker."""
    include_sections = include_sections or ["overview", "financials", "risk", "recommendation"]

    sections = []
    for section_name in include_sections:
        sections.append({
            "title": section_name.title(),
            "content": f"[{section_name} analysis for {ticker}]",
        })

    return GenerateReportOutput(
        title=f"{ticker} {report_type.title()} Report",
        sections=sections,
        risk_flags=[],
        summary=f"{report_type.title()} report for {ticker} covering {len(sections)} sections.",
    ).model_dump()
