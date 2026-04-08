"""
FinAgentX — LangGraph State with Redis Persistence (Fix #2)

- Redis checkpointer — survives crashes, restartable mid-workflow
- AgentState TypedDict with messages, tool outputs, risk flags, citations
"""

from __future__ import annotations

import operator
import os
from typing import Annotated, Any, TypedDict

from domain.schemas import Citation, TraceStep

logger_name = __name__


class AgentState(TypedDict):
    """State managed across the LangGraph workflow."""
    messages: Annotated[list, operator.add]
    tool_outputs: list[dict[str, Any]]
    risk_flags: list[str]
    citations: list[dict]
    trace_steps: list[dict]
    session_id: str
    user_id: str
    intent: str
    step_count: int
    confidence: float
    requires_approval: bool
    error: str | None


def get_initial_state(
    session_id: str,
    user_id: str,
    query: str,
    intent: str = "unknown",
) -> AgentState:
    """Create initial agent state for a new session."""
    return AgentState(
        messages=[{"role": "user", "content": query}],
        tool_outputs=[],
        risk_flags=[],
        citations=[],
        trace_steps=[],
        session_id=session_id,
        user_id=user_id,
        intent=intent,
        step_count=0,
        confidence=0.0,
        requires_approval=False,
        error=None,
    )


def get_checkpointer():
    """
    Get Redis checkpointer for LangGraph state persistence.

    Any crash mid-workflow → resume from last Redis checkpoint.
    Usage: graph.invoke(state, config={"configurable": {"thread_id": session_id}})
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    try:
        from langgraph.checkpoint.redis import RedisSaver
        return RedisSaver.from_conn_string(redis_url)
    except ImportError:
        # Fallback to memory saver for local dev
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
