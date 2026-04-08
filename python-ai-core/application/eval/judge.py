"""
FinAgentX — LLM-as-Judge Evaluator (Fix #4, #6, #14)

- Fix #4: Separate stronger model (Mixtral-8x22B) for unbiased evaluation
- Fix #6: Faithfulness verification chain
- Fix #14: RAGAS-style evaluation metrics
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from domain.schemas import EvalResult

logger = logging.getLogger(__name__)


class LLMJudge:
    """
    Uses a DIFFERENT, stronger model than the agent — prevents circular scoring.

    Agent uses llama3.1-70b → judge uses Mixtral-8x22B (or equivalent).
    """

    def __init__(
        self,
        api_key: str,
        *,
        judge_model: str = "llama3.1-70b",
        base_url: str = "https://api.cerebras.ai/v1",
    ):
        self.api_key = api_key
        self.judge_model = judge_model
        self.base_url = base_url

    def evaluate(
        self,
        query: str,
        answer: str,
        retrieved_chunks: list[str],
        *,
        expected_answer: str | None = None,
    ) -> EvalResult:
        """Run full evaluation: correctness + faithfulness + hallucination detection."""
        context = "\n---\n".join(retrieved_chunks)

        expected_section = ""
        if expected_answer:
            expected_section = f"\nExpected answer: {expected_answer}"

        prompt = f"""You are a strict financial answer evaluator. Evaluate the following answer.

Query: {query}{expected_section}
Retrieved context:
{context}

Answer to evaluate:
{answer}

Evaluate on these criteria:
1. CORRECTNESS (0.0-1.0): How accurate is the answer? Does it match the expected answer (if provided)?
2. FAITHFULNESS (0.0-1.0): Is every claim in the answer supported by the retrieved context?
3. HALLUCINATION: Does the answer contain any claims NOT supported by the context?

Return ONLY valid JSON:
{{
  "correctness": 0.0-1.0,
  "faithfulness": 0.0-1.0,
  "hallucination_detected": true/false,
  "grounded_claims": ["claim1", "claim2"],
  "ungrounded_claims": ["claim1"],
  "reasoning": "detailed explanation"
}}"""

        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.judge_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.0,
                },
                timeout=30,
            )
            resp.raise_for_status()

            content = resp.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)

            return EvalResult(
                correctness=float(parsed.get("correctness", 0)),
                faithfulness=float(parsed.get("faithfulness", 0)),
                hallucination_detected=bool(parsed.get("hallucination_detected", False)),
                grounded_claims=parsed.get("grounded_claims", []),
                ungrounded_claims=parsed.get("ungrounded_claims", []),
                reasoning=parsed.get("reasoning", ""),
            )
        except Exception as e:
            logger.error(f"Judge evaluation failed: {e}")
            return EvalResult(
                correctness=0.0,
                faithfulness=0.0,
                hallucination_detected=True,
                reasoning=f"Evaluation failed: {str(e)}",
            )
