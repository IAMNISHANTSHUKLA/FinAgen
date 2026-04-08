"""
FinAgentX — Agent Guardrails (Fix A2, A3)

- Fix A2: Max steps, timeout, termination conditions, loop detection
- Fix A3: Human approval checkpoints, action policies
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from domain.exceptions import (
    AgentTimeoutError,
    HumanApprovalRequired,
    LoopDetected,
    MaxStepsExceeded,
    ToolAccessDenied,
)
from domain.schemas import UserContext
from infrastructure.observability.metrics import GUARDRAIL_TRIGGERS

logger = logging.getLogger(__name__)


@dataclass
class GuardrailConfig:
    """Configuration for agent guardrails."""
    max_steps: int = 10
    overall_timeout_seconds: float = 60.0
    per_tool_timeout_seconds: float = 10.0
    max_same_tool_calls: int = 3  # Loop detection threshold
    confidence_threshold_for_approval: float = 0.7
    high_risk_tools: list[str] = field(
        default_factory=lambda: ["recommend_action"]
    )


class AgentGuardrails:
    """
    Safety guardrails for agent orchestration.

    Prevents:
    - Infinite loops (same tool with same input)
    - Runaway execution (max steps, timeout)
    - Unauthorized actions (role-based, human approval)
    """

    def __init__(self, config: GuardrailConfig | None = None):
        self.config = config or GuardrailConfig()
        self._start_time: float = 0
        self._step_count: int = 0
        self._tool_call_history: list[tuple[str, str]] = []  # (tool, input_hash)

    def reset(self) -> None:
        """Reset guardrails for a new session."""
        self._start_time = time.monotonic()
        self._step_count = 0
        self._tool_call_history = []

    def check_step(self, tool_name: str, input_data: str) -> None:
        """
        Check all guardrails before executing a step.

        Raises appropriate exception if any guardrail triggers.
        """
        self._check_timeout()
        self._check_max_steps()
        self._check_loop(tool_name, input_data)

    def _check_timeout(self) -> None:
        """Fix A2: Check overall timeout."""
        if self._start_time == 0:
            self._start_time = time.monotonic()

        elapsed = time.monotonic() - self._start_time
        if elapsed > self.config.overall_timeout_seconds:
            GUARDRAIL_TRIGGERS.labels(guardrail_type="timeout").inc()
            raise AgentTimeoutError(
                f"Agent timeout: {elapsed:.1f}s > {self.config.overall_timeout_seconds}s",
                timeout_seconds=self.config.overall_timeout_seconds,
            )

    def _check_max_steps(self) -> None:
        """Fix A2: Check max steps."""
        self._step_count += 1
        if self._step_count > self.config.max_steps:
            GUARDRAIL_TRIGGERS.labels(guardrail_type="max_steps").inc()
            raise MaxStepsExceeded(
                f"Agent exceeded max steps: {self._step_count} > {self.config.max_steps}",
                max_steps=self.config.max_steps,
                current_step=self._step_count,
            )

    def _check_loop(self, tool_name: str, input_data: str) -> None:
        """Fix A2: Detect infinite loops."""
        import hashlib
        input_hash = hashlib.md5(input_data.encode()).hexdigest()[:8]
        call_sig = (tool_name, input_hash)

        same_calls = sum(
            1 for t, h in self._tool_call_history if t == tool_name and h == input_hash
        )

        if same_calls >= self.config.max_same_tool_calls:
            GUARDRAIL_TRIGGERS.labels(guardrail_type="loop_detected").inc()
            raise LoopDetected(
                f"Loop detected: tool '{tool_name}' called {same_calls + 1} times with same input",
                tool_name=tool_name,
                iteration_count=same_calls + 1,
            )

        self._tool_call_history.append(call_sig)

    def check_approval_needed(
        self,
        tool_name: str,
        confidence: float,
        user_context: UserContext,
    ) -> bool:
        """
        Fix A3: Check if human approval is needed.

        Triggers for:
        - High-risk tools
        - Low confidence scores
        - Non-admin users performing sensitive actions
        """
        if tool_name in self.config.high_risk_tools:
            if confidence < self.config.confidence_threshold_for_approval:
                GUARDRAIL_TRIGGERS.labels(guardrail_type="human_approval").inc()
                return True

            if "admin" not in user_context.roles and "engineer" not in user_context.roles:
                GUARDRAIL_TRIGGERS.labels(guardrail_type="human_approval").inc()
                return True

        return False

    def check_tool_policy(
        self,
        tool_name: str,
        user_context: UserContext,
    ) -> None:
        """Fix A3: Check if user's role permits this tool."""
        from infrastructure.auth.jwt_middleware import RBACGuard

        if not RBACGuard.check_tool_access(tool_name, user_context):
            raise ToolAccessDenied(
                f"User {user_context.user_id} cannot use tool '{tool_name}'",
                tool_name=tool_name,
                user_id=user_context.user_id,
            )

    @property
    def current_step(self) -> int:
        return self._step_count

    @property
    def elapsed_seconds(self) -> float:
        if self._start_time == 0:
            return 0
        return time.monotonic() - self._start_time
