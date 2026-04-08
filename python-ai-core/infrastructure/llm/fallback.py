"""
FinAgentX — Ollama Fallback LLM Client

Local development fallback when Cerebras API is unavailable.
Implements same BaseChatModel interface — Liskov substitutable.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from domain.exceptions import LLMConnectionError

logger = logging.getLogger(__name__)


class OllamaFallback(BaseChatModel):
    """Ollama-based LLM for local development. Same interface as CerebrasAdapter."""

    model: str = "llama3.1"
    base_url: str = "http://localhost:11434"
    timeout: float = 120.0

    class Config:
        arbitrary_types_allowed = True

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        start_time = time.monotonic()

        role_map = {"human": "user", "ai": "assistant", "system": "system"}
        ollama_messages = [
            {"role": role_map.get(m.type, "user"), "content": m.content}
            for m in messages
        ]

        try:
            resp = httpx.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": ollama_messages,
                    "stream": False,
                    "options": {
                        "temperature": kwargs.get("temperature", 0.0),
                        "num_predict": kwargs.get("max_tokens", 4096),
                    },
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["message"]["content"]
            latency_ms = int((time.monotonic() - start_time) * 1000)

            logger.info(
                "ollama_completion",
                extra={"model": self.model, "latency_ms": latency_ms},
            )

            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(
                            content=text,
                            additional_kwargs={"latency_ms": latency_ms, "model": self.model},
                        )
                    )
                ]
            )
        except Exception as e:
            raise LLMConnectionError(f"Ollama error: {e}") from e

    def count_tokens(self, text: str) -> int:
        return len(text) // 4

    @property
    def _llm_type(self) -> str:
        return "ollama"
