"""
FinAgentX — Cerebras LangChain Adapter (Fix #1)

Wraps Cerebras API into LangChain's BaseChatModel interface
so it's Liskov-substitutable with any LangChain-compatible LLM.
Enables direct use with LangGraph orchestrator.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from domain.exceptions import LLMConnectionError, StructuredOutputParseError

logger = logging.getLogger(__name__)


def _message_to_dict(message: BaseMessage) -> dict[str, str]:
    """Convert LangChain message to Cerebras API format."""
    role_map = {
        "human": "user",
        "ai": "assistant",
        "system": "system",
    }
    role = role_map.get(message.type, "user")
    return {"role": role, "content": message.content}


class CerebrasAdapter(BaseChatModel):
    """
    LangChain-compatible adapter for Cerebras API.

    Supports:
    - Standard chat completions
    - Structured JSON output via response_format
    - Token counting
    - Retry with exponential backoff
    - Latency tracking for observability
    """

    api_key: str
    model: str = "llama-4-scout-17b-16e-instruct"
    base_url: str = "https://api.cerebras.ai/v1"
    timeout: float = 30.0
    max_retries: int = 3
    temperature: float = 0.0

    class Config:
        arbitrary_types_allowed = True

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Generate a chat completion via Cerebras API."""
        start_time = time.monotonic()

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [_message_to_dict(m) for m in messages],
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        # Structured output support
        if "response_format" in kwargs and kwargs["response_format"]:
            payload["response_format"] = kwargs["response_format"]

        if stop:
            payload["stop"] = stop

        # Clean None values
        payload = {k: v for k, v in payload.items() if v is not None}

        # Retry with exponential backoff
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = httpx.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                data = response.json()
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})

                latency_ms = int((time.monotonic() - start_time) * 1000)
                logger.info(
                    "cerebras_completion",
                    extra={
                        "model": self.model,
                        "latency_ms": latency_ms,
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "attempt": attempt + 1,
                    },
                )

                generation = ChatGeneration(
                    message=AIMessage(
                        content=text,
                        additional_kwargs={
                            "usage": usage,
                            "latency_ms": latency_ms,
                            "model": self.model,
                        },
                    )
                )
                return ChatResult(generations=[generation])

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    # Rate limited — backoff
                    wait = (2**attempt) * 0.5
                    logger.warning(f"Rate limited, retrying in {wait}s (attempt {attempt + 1})")
                    time.sleep(wait)
                elif e.response.status_code >= 500:
                    wait = (2**attempt) * 1.0
                    logger.warning(f"Server error {e.response.status_code}, retrying in {wait}s")
                    time.sleep(wait)
                else:
                    raise LLMConnectionError(
                        f"Cerebras API error: {e.response.status_code} — {e.response.text}"
                    ) from e
            except httpx.TimeoutException as e:
                last_error = e
                wait = (2**attempt) * 1.0
                logger.warning(f"Timeout, retrying in {wait}s (attempt {attempt + 1})")
                time.sleep(wait)

        raise LLMConnectionError(
            f"Cerebras API failed after {self.max_retries} attempts"
        ) from last_error

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Async generate via Cerebras API."""
        start_time = time.monotonic()

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [_message_to_dict(m) for m in messages],
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", 4096),
        }

        if "response_format" in kwargs and kwargs["response_format"]:
            payload["response_format"] = kwargs["response_format"]

        if stop:
            payload["stop"] = stop

        payload = {k: v for k, v in payload.items() if v is not None}

        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                        timeout=self.timeout,
                    )
                    response.raise_for_status()

                data = response.json()
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                latency_ms = int((time.monotonic() - start_time) * 1000)

                generation = ChatGeneration(
                    message=AIMessage(
                        content=text,
                        additional_kwargs={
                            "usage": usage,
                            "latency_ms": latency_ms,
                            "model": self.model,
                        },
                    )
                )
                return ChatResult(generations=[generation])

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code in (429, 500, 502, 503):
                    import asyncio
                    wait = (2**attempt) * 0.5
                    await asyncio.sleep(wait)
                else:
                    raise LLMConnectionError(
                        f"Cerebras API error: {e.response.status_code}"
                    ) from e
            except httpx.TimeoutException as e:
                last_error = e
                import asyncio
                await asyncio.sleep((2**attempt) * 1.0)

        raise LLMConnectionError(
            f"Cerebras API failed after {self.max_retries} attempts"
        ) from last_error

    def generate_structured(
        self,
        messages: list[BaseMessage],
        *,
        schema_name: str = "response",
    ) -> dict[str, Any]:
        """Generate structured JSON output."""
        result = self._generate(
            messages,
            response_format={"type": "json_object"},
        )
        text = result.generations[0].message.content

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise StructuredOutputParseError(
                f"Failed to parse structured output: {e}",
                raw_response=text,
            ) from e

    def count_tokens(self, text: str) -> int:
        """Approximate token count (4 chars ≈ 1 token for LLaMA-family)."""
        return len(text) // 4

    @property
    def _llm_type(self) -> str:
        return "cerebras"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "base_url": self.base_url,
            "temperature": self.temperature,
        }
