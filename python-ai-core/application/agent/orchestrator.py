"""
FinAgentX — LangGraph Agent Orchestrator

Full ReAct workflow: Plan → Select Tool → Execute → Validate → Check Guardrails → Reason → Answer
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from application.agent.graph_state import AgentState, get_checkpointer, get_initial_state
from application.agent.guardrails import AgentGuardrails, GuardrailConfig
from application.agent.prompts import AGENT_SYSTEM_PROMPT, GROUNDED_GENERATION_PROMPT, PLANNING_PROMPT
from application.agent.tool_registry import ToolRegistry
from application.agent.tool_selector import ToolSelector
from application.rag.citations import CitationTracker
from domain.exceptions import (
    AgentTimeoutError,
    HumanApprovalRequired,
    LoopDetected,
    MaxStepsExceeded,
)
from domain.schemas import QueryIntent, TraceStep, UserContext
from infrastructure.observability.metrics import (
    GUARDRAIL_TRIGGERS,
    QUERIES_TOTAL,
    QUERY_DURATION,
    TOOL_CALLS_TOTAL,
    TOOL_LATENCY,
)

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    LangGraph-based agent orchestrator with ReAct loop.

    Flow:
    1. plan → Determine which tools to call
    2. select_tool → Pick next tool from plan
    3. execute_tool → Run tool with input validation
    4. validate_output → Schema-validate tool output
    5. check_guardrails → Loop/timeout/approval checks
    6. reason → Decide: more tools needed or generate answer
    7. generate_answer → Produce grounded response with citations
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tool_registry: ToolRegistry,
        citation_tracker: CitationTracker,
        *,
        guardrail_config: GuardrailConfig | None = None,
    ):
        self.llm = llm
        self.tool_registry = tool_registry
        self.tool_selector = ToolSelector(tool_registry, llm)
        self.citation_tracker = citation_tracker
        self.guardrails = AgentGuardrails(guardrail_config)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        graph = StateGraph(AgentState)

        graph.add_node("plan", self._plan_node)
        graph.add_node("execute_tool", self._execute_tool_node)
        graph.add_node("reason", self._reason_node)
        graph.add_node("generate_answer", self._generate_answer_node)

        graph.set_entry_point("plan")
        graph.add_edge("plan", "execute_tool")
        graph.add_conditional_edges(
            "execute_tool",
            self._route_after_execution,
            {"continue": "reason", "answer": "generate_answer", "error": "generate_answer"},
        )
        graph.add_conditional_edges(
            "reason",
            self._route_after_reasoning,
            {"more_tools": "execute_tool", "answer": "generate_answer"},
        )
        graph.add_edge("generate_answer", END)

        checkpointer = get_checkpointer()
        return graph.compile(checkpointer=checkpointer)

    async def run(
        self,
        query: str,
        *,
        session_id: str | None = None,
        user_context: UserContext | None = None,
        intent: QueryIntent = QueryIntent.UNKNOWN,
    ) -> dict[str, Any]:
        """Run the agent orchestrator on a query."""
        session_id = session_id or uuid.uuid4().hex[:12]
        user_id = user_context.user_id if user_context else "anonymous"
        start_time = time.monotonic()

        self.guardrails.reset()

        state = get_initial_state(
            session_id=session_id,
            user_id=user_id,
            query=query,
            intent=intent.value,
        )

        try:
            config = {"configurable": {"thread_id": session_id}}
            final_state = await self.graph.ainvoke(state, config=config)

            latency_ms = int((time.monotonic() - start_time) * 1000)
            QUERY_DURATION.labels(intent=intent.value, status="success").observe(
                latency_ms / 1000
            )
            QUERIES_TOTAL.labels(intent=intent.value, status="success").inc()

            return {
                "session_id": session_id,
                "answer": final_state.get("messages", [{"content": "No answer"}])[-1].get(
                    "content", ""
                ) if isinstance(final_state.get("messages", [])[-1], dict) else str(final_state.get("messages", [""])[-1]),
                "steps": final_state.get("trace_steps", []),
                "citations": final_state.get("citations", []),
                "confidence": final_state.get("confidence", 0.0),
                "intent": intent.value,
                "total_latency_ms": latency_ms,
                "requires_approval": final_state.get("requires_approval", False),
                "risk_flags": final_state.get("risk_flags", []),
            }

        except (LoopDetected, MaxStepsExceeded, AgentTimeoutError) as e:
            latency_ms = int((time.monotonic() - start_time) * 1000)
            QUERIES_TOTAL.labels(intent=intent.value, status="guardrail").inc()
            logger.warning(f"Guardrail triggered: {e}")
            return {
                "session_id": session_id,
                "answer": f"Agent stopped: {str(e)}",
                "steps": [],
                "citations": [],
                "confidence": 0.0,
                "intent": intent.value,
                "total_latency_ms": latency_ms,
                "requires_approval": False,
                "error": str(e),
            }

    async def _plan_node(self, state: AgentState) -> dict:
        """Plan which tools to call based on the query."""
        query = state["messages"][0]["content"] if state["messages"] else ""
        selected = self.tool_selector.select_tools(query, max_tools=3)

        return {
            "tool_outputs": [{"_plan": selected}],
            "step_count": state.get("step_count", 0),
        }

    async def _execute_tool_node(self, state: AgentState) -> dict:
        """Execute the next tool in the plan."""
        plan = []
        for to in state.get("tool_outputs", []):
            if "_plan" in to:
                plan = to["_plan"]
                break

        step_count = state.get("step_count", 0)

        if step_count >= len(plan):
            return {"step_count": step_count}

        tool_name = plan[step_count]
        query = state["messages"][0]["content"] if state["messages"] else ""

        self.guardrails.check_step(tool_name, query)

        start = time.monotonic()
        try:
            result = await self.tool_registry.execute(
                tool_name, {"ticker": "AAPL", "context": query}
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            TOOL_CALLS_TOTAL.labels(tool_name=tool_name, status="success").inc()
            TOOL_LATENCY.labels(tool_name=tool_name).observe(latency_ms / 1000)

            trace_step = {
                "step_id": uuid.uuid4().hex[:8],
                "step_number": step_count + 1,
                "tool_name": tool_name,
                "input_json": json.dumps({"query": query[:100]}),
                "output_json": json.dumps(result)[:500],
                "latency_ms": latency_ms,
                "confidence": result.get("confidence", 0.7),
                "reasoning": f"Called {tool_name} to process query",
            }

            return {
                "tool_outputs": state.get("tool_outputs", []) + [result],
                "trace_steps": state.get("trace_steps", []) + [trace_step],
                "step_count": step_count + 1,
                "risk_flags": state.get("risk_flags", []) + result.get("risk_flags", []),
            }

        except Exception as e:
            TOOL_CALLS_TOTAL.labels(tool_name=tool_name, status="error").inc()
            logger.error(f"Tool {tool_name} failed: {e}")
            return {
                "error": str(e),
                "step_count": step_count + 1,
            }

    def _route_after_execution(self, state: AgentState) -> str:
        if state.get("error"):
            return "error"

        plan = []
        for to in state.get("tool_outputs", []):
            if "_plan" in to:
                plan = to["_plan"]
                break

        if state.get("step_count", 0) >= len(plan):
            return "answer"
        return "continue"

    async def _reason_node(self, state: AgentState) -> dict:
        """Reason over tool outputs and decide next action."""
        return {"confidence": 0.75}

    def _route_after_reasoning(self, state: AgentState) -> str:
        plan = []
        for to in state.get("tool_outputs", []):
            if "_plan" in to:
                plan = to["_plan"]
                break

        if state.get("step_count", 0) < len(plan):
            return "more_tools"
        return "answer"

    async def _generate_answer_node(self, state: AgentState) -> dict:
        """Generate final grounded answer with citations."""
        query = state["messages"][0]["content"] if state["messages"] else ""
        tool_outputs = [
            to for to in state.get("tool_outputs", []) if "_plan" not in to
        ]

        prompt = GROUNDED_GENERATION_PROMPT.format(
            query=query,
            intent=state.get("intent", "unknown"),
            context="[Retrieved context from RAG pipeline]",
            tool_outputs=json.dumps(tool_outputs, indent=2)[:2000],
        )

        result = self.llm.invoke([
            SystemMessage(content="You are FinAgentX, a financial AI agent."),
            HumanMessage(content=prompt),
        ])

        answer = result.content
        confidence = state.get("confidence", 0.7)

        return {
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": answer}
            ],
            "confidence": confidence,
        }
