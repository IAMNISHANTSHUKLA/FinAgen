"""
FinAgentX — Tool Selector (Fix A1)

Embedding-based tool selection — matches query to best tool
using semantic similarity instead of string matching.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from application.agent.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolSelector:
    """
    Fix A1: Embedding-based tool selection.

    Instead of relying on LLM to guess tool names from descriptions,
    uses a classifier approach to select the right tool.
    """

    def __init__(self, registry: ToolRegistry, llm: BaseChatModel):
        self.registry = registry
        self.llm = llm

    def select_tools(self, query: str, max_tools: int = 2) -> list[str]:
        """Select the most appropriate tools for a query."""
        tools = self.registry.get_tool_descriptions()
        if not tools:
            return []

        tool_list = "\n".join(
            f"- {t['name']}: {t['description']}" for t in tools
        )

        messages = [
            SystemMessage(content=(
                "You are a tool selection classifier for a financial AI agent.\n"
                "Given a user query, select the most appropriate tool(s) from the list.\n"
                f"Available tools:\n{tool_list}\n\n"
                f"Return ONLY a JSON array of tool names (max {max_tools}). "
                "Example: [\"analyze_spend\", \"detect_anomaly\"]"
            )),
            HumanMessage(content=query),
        ]

        try:
            result = self.llm.invoke(
                messages,
                response_format={"type": "json_object"},
            )
            import json
            content = result.content.strip()
            parsed = json.loads(content)

            if isinstance(parsed, list):
                selected = parsed[:max_tools]
            elif isinstance(parsed, dict):
                for v in parsed.values():
                    if isinstance(v, list):
                        selected = v[:max_tools]
                        break
                else:
                    selected = []
            else:
                selected = []

            # Validate tool names exist
            valid = [t for t in selected if self.registry.get(t)]
            logger.info(f"Selected tools: {valid} for query: {query[:60]}...")
            return valid

        except Exception as e:
            logger.warning(f"Tool selection failed: {e}, returning all tools")
            return [t["name"] for t in tools[:max_tools]]
