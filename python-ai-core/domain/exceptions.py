"""
FinAgentX — Domain Exceptions

Custom exception hierarchy for the domain layer.
Each exception carries enough context for proper error handling
and structured logging upstream.
"""

from __future__ import annotations


class FinAgentXError(Exception):
    """Base exception for all FinAgentX errors."""

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}


# ─────────────────────────────────────────────
# Schema & Validation Errors
# ─────────────────────────────────────────────

class SchemaValidationError(FinAgentXError):
    """LLM output failed Pydantic schema validation."""

    def __init__(self, message: str, *, raw_output: str = "", schema_name: str = ""):
        super().__init__(
            message,
            details={"raw_output": raw_output, "schema_name": schema_name},
        )
        self.raw_output = raw_output
        self.schema_name = schema_name


class StructuredOutputParseError(FinAgentXError):
    """Failed to parse structured JSON from LLM response."""

    def __init__(self, message: str, *, raw_response: str = ""):
        super().__init__(message, details={"raw_response": raw_response})
        self.raw_response = raw_response


# ─────────────────────────────────────────────
# RAG Pipeline Errors
# ─────────────────────────────────────────────

class RetrievalError(FinAgentXError):
    """Error during retrieval from vector store."""
    pass


class ChunkingError(FinAgentXError):
    """Error during document chunking."""
    pass


class EmbeddingVersionMismatch(FinAgentXError):
    """Embedding model version differs from collection version (Fix #4)."""

    def __init__(
        self,
        message: str,
        *,
        current_version: str = "",
        collection_version: str = "",
    ):
        super().__init__(
            message,
            details={
                "current_version": current_version,
                "collection_version": collection_version,
            },
        )


class ContextWindowOverflow(FinAgentXError):
    """Retrieved context exceeds token budget (Fix #5)."""

    def __init__(self, message: str, *, tokens_needed: int = 0, budget: int = 0):
        super().__init__(
            message,
            details={"tokens_needed": tokens_needed, "budget": budget},
        )


class StaleDocumentError(FinAgentXError):
    """Document freshness score below threshold (Fix #8)."""
    pass


# ─────────────────────────────────────────────
# Agent Errors
# ─────────────────────────────────────────────

class ToolExecutionError(FinAgentXError):
    """Error during tool execution."""

    def __init__(self, message: str, *, tool_name: str = "", input_data: str = ""):
        super().__init__(
            message,
            details={"tool_name": tool_name, "input_data": input_data},
        )
        self.tool_name = tool_name


class LoopDetected(FinAgentXError):
    """Agent detected an infinite loop — same tool called with same input (Fix A2)."""

    def __init__(self, message: str, *, tool_name: str = "", iteration_count: int = 0):
        super().__init__(
            message,
            details={"tool_name": tool_name, "iteration_count": iteration_count},
        )


class MaxStepsExceeded(FinAgentXError):
    """Agent exceeded maximum allowed steps (Fix A2)."""

    def __init__(self, message: str, *, max_steps: int = 10, current_step: int = 0):
        super().__init__(
            message,
            details={"max_steps": max_steps, "current_step": current_step},
        )


class AgentTimeoutError(FinAgentXError):
    """Agent exceeded overall timeout (Fix A2)."""

    def __init__(self, message: str, *, timeout_seconds: float = 60.0):
        super().__init__(message, details={"timeout_seconds": timeout_seconds})


class HumanApprovalRequired(FinAgentXError):
    """Action requires human approval before proceeding (Fix A3)."""

    def __init__(
        self,
        message: str,
        *,
        action: str = "",
        confidence: float = 0.0,
        session_id: str = "",
    ):
        super().__init__(
            message,
            details={
                "action": action,
                "confidence": confidence,
                "session_id": session_id,
            },
        )


class ToolAccessDenied(FinAgentXError):
    """User does not have permission to use this tool (Fix A3)."""

    def __init__(self, message: str, *, tool_name: str = "", user_id: str = ""):
        super().__init__(
            message,
            details={"tool_name": tool_name, "user_id": user_id},
        )


# ─────────────────────────────────────────────
# Safety Errors
# ─────────────────────────────────────────────

class HallucinationDetected(FinAgentXError):
    """LLM output contains ungrounded claims (Fix #6)."""

    def __init__(
        self,
        message: str,
        *,
        ungrounded_claims: list[str] | None = None,
    ):
        super().__init__(
            message,
            details={"ungrounded_claims": ungrounded_claims or []},
        )


class DomainRestrictionViolation(FinAgentXError):
    """Query is outside the allowed financial domain."""
    pass


# ─────────────────────────────────────────────
# Authorization Errors (Fix #13)
# ─────────────────────────────────────────────

class AuthorizationDenied(FinAgentXError):
    """User lacks authorization for requested operation."""

    def __init__(self, message: str, *, user_id: str = "", resource: str = ""):
        super().__init__(
            message,
            details={"user_id": user_id, "resource": resource},
        )


# ─────────────────────────────────────────────
# Infrastructure Errors
# ─────────────────────────────────────────────

class LLMConnectionError(FinAgentXError):
    """Failed to connect to LLM provider."""
    pass


class VectorStoreConnectionError(FinAgentXError):
    """Failed to connect to vector store."""
    pass


class CacheConnectionError(FinAgentXError):
    """Failed to connect to cache (Redis)."""
    pass
