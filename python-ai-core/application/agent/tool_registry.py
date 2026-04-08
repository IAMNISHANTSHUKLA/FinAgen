"""
FinAgentX — Agent Tool Registry

Pluggable tool registration with schema validation.
Open/Closed: add new tools without modifying orchestrator.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from pydantic import BaseModel

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    """Definition of a registered agent tool."""
    name: str
    description: str
    function: Callable[..., Awaitable[dict[str, Any]]]
    input_schema: type[BaseModel]
    output_schema: type[BaseModel] | None = None
    requires_approval: bool = False
    timeout_seconds: float = 10.0
    required_roles: list[str] = field(default_factory=lambda: ["analyst", "engineer", "admin"])


class ToolRegistry:
    """
    Pluggable tool registry — extensible without modifying orchestrator.

    Register tools with typed schemas. The orchestrator calls tools
    through this registry, which handles validation and error wrapping.
    """

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a new tool."""
        self._tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name} (approval={tool.requires_approval})")

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def get_tool_descriptions(self) -> list[dict[str, str]]:
        """Get tool descriptions for LLM prompt injection."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema.model_json_schema() if t.input_schema else {},
            }
            for t in self._tools.values()
        ]

    async def execute(self, name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool with input validation."""
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")

        # Validate input
        if tool.input_schema:
            validated = tool.input_schema(**parameters)
            parameters = validated.model_dump()

        # Execute
        result = await tool.function(**parameters)
        return result
