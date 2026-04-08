"""
FinAgentX — Cascaded Inference (Fix #10)

- Cheap model first (llama3.1-8b), escalate on low confidence
- Context compression for cost reduction
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage

from infrastructure.observability.metrics import LLM_LATENCY, TOKENS_TOTAL

logger = logging.getLogger(__name__)


class CascadedInference:
    """
    Cost-aware inference pipeline.

    Stage 1: Cheap/fast model (llama3.1-8b) generates initial response
    Stage 2: If confidence < threshold, escalate to expensive model (llama3.1-70b)

    This reduces cost by handling simple queries with smaller models
    and only invoking large models when needed.
    """

    def __init__(
        self,
        cheap_llm: BaseChatModel,
        expensive_llm: BaseChatModel,
        *,
        confidence_threshold: float = 0.7,
    ):
        self.cheap_llm = cheap_llm
        self.expensive_llm = expensive_llm
        self.confidence_threshold = confidence_threshold

    async def generate(
        self,
        messages: list[BaseMessage],
        **kwargs: Any,
    ) -> tuple[str, float, str]:
        """
        Generate response with cascaded inference.

        Returns:
            (response_text, confidence, model_used)
        """
        # Stage 1: Try cheap model
        try:
            result = self.cheap_llm.invoke(messages, **kwargs)
            text = result.content
            confidence = self._estimate_confidence(text)

            cheap_model = getattr(self.cheap_llm, 'model', 'cheap')
            logger.info(
                f"Cheap model response (confidence={confidence:.2f})",
                extra={"model": cheap_model, "confidence": confidence},
            )

            if confidence >= self.confidence_threshold:
                return text, confidence, cheap_model

            # Stage 2: Escalate to expensive model
            logger.info(
                f"Confidence {confidence:.2f} < {self.confidence_threshold}, "
                f"escalating to expensive model"
            )

        except Exception as e:
            logger.warning(f"Cheap model failed: {e}, falling back to expensive model")

        # Expensive model
        result = self.expensive_llm.invoke(messages, **kwargs)
        text = result.content
        confidence = self._estimate_confidence(text)
        expensive_model = getattr(self.expensive_llm, 'model', 'expensive')

        logger.info(
            f"Expensive model response (confidence={confidence:.2f})",
            extra={"model": expensive_model, "confidence": confidence},
        )

        return text, confidence, expensive_model

    def _estimate_confidence(self, response: str) -> float:
        """
        Estimate confidence of a response based on heuristics.

        Signals of low confidence:
        - Hedging language ("I'm not sure", "might", "possibly")
        - Insufficient data mentions
        - Very short responses
        - No numerical data in financial context
        """
        text_lower = response.lower()

        score = 0.8  # Base confidence

        # Hedging language reduces confidence
        hedging_phrases = [
            "i'm not sure", "might be", "possibly", "unclear",
            "i don't have", "insufficient", "cannot determine",
            "not enough information", "unable to", "approximate",
        ]
        for phrase in hedging_phrases:
            if phrase in text_lower:
                score -= 0.1

        # Very short responses are suspicious for financial queries
        if len(response) < 50:
            score -= 0.2

        # Having numbers suggests grounded data
        import re
        numbers = re.findall(r'\$[\d,.]+|\d+\.\d+%|\d{1,3}(?:,\d{3})+', response)
        if numbers:
            score += 0.1

        # Citing sources is good
        if "[SOURCE_" in response:
            score += 0.1

        return max(0.0, min(1.0, score))
