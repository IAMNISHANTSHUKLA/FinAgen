"""
FinAgentX — Reversible PII Masker (Fix #7)

Uses Microsoft Presidio for entity recognition + anonymization.
Supports reversible tokenization — original values stored in encrypted Redis,
never logged, TTL-auto-expired.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from domain.interfaces import PIIMasker

logger = logging.getLogger(__name__)

# PII entity types relevant to financial domain
FINANCIAL_PII_ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "IBAN_CODE",
    "US_SSN",
    "US_BANK_NUMBER",
    "IP_ADDRESS",
    "LOCATION",
    "DATE_TIME",  # Careful: dates in finance are data, not PII — context matters
]


class PresidioPIIMasker(PIIMasker):
    """
    Reversible PII masking using Microsoft Presidio.

    Flow:
    1. Analyze text for PII entities
    2. Replace each with a unique token [ENTITY_TYPE_xxxx]
    3. Store reverse map (token → original) — caller stores in encrypted Redis
    4. After LLM processing, unmask using reverse map

    Security:
    - reverse_map is NEVER logged
    - Stored in Redis with TTL=1hr, encrypted at rest
    - Token format is non-reversible without the map
    """

    def __init__(
        self,
        *,
        entities: list[str] | None = None,
        score_threshold: float = 0.7,
    ):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        self.entities = entities or FINANCIAL_PII_ENTITIES
        self.score_threshold = score_threshold

        logger.info(
            f"PII masker initialized with {len(self.entities)} entity types, "
            f"threshold={score_threshold}"
        )

    def mask(self, text: str) -> tuple[str, dict[str, str]]:
        """
        Mask all PII in text.

        Returns:
            (masked_text, reverse_map) — store reverse_map encrypted, NEVER log it.
        """
        # Analyze for PII entities
        results = self.analyzer.analyze(
            text=text,
            language="en",
            entities=self.entities,
            score_threshold=self.score_threshold,
        )

        if not results:
            return text, {}

        # Sort by start position (descending) to replace from end → start
        # This prevents position shifts during replacement
        results = sorted(results, key=lambda r: r.start, reverse=True)

        reverse_map: dict[str, str] = {}
        masked_text = text

        for result in results:
            original = text[result.start : result.end]
            token = f"[{result.entity_type}_{uuid.uuid4().hex[:8]}]"

            # Replace in text
            masked_text = masked_text[: result.start] + token + masked_text[result.end :]
            reverse_map[token] = original

        pii_count = len(reverse_map)
        entity_types = list({r.entity_type for r in results})
        logger.info(
            f"Masked {pii_count} PII entities of types: {entity_types}",
            extra={"pii_count": pii_count, "entity_types": entity_types},
        )

        return masked_text, reverse_map

    def unmask(self, text: str, reverse_map: dict[str, str]) -> str:
        """Restore original PII from masked text."""
        for token, original in reverse_map.items():
            text = text.replace(token, original)
        return text

    def mask_dict(self, data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
        """Mask PII in all string values of a dict (recursive)."""
        combined_map: dict[str, str] = {}
        masked_data = {}

        for key, value in data.items():
            if isinstance(value, str):
                masked_value, reverse_map = self.mask(value)
                masked_data[key] = masked_value
                combined_map.update(reverse_map)
            elif isinstance(value, dict):
                masked_value, reverse_map = self.mask_dict(value)
                masked_data[key] = masked_value
                combined_map.update(reverse_map)
            elif isinstance(value, list):
                masked_list = []
                for item in value:
                    if isinstance(item, str):
                        masked_item, reverse_map = self.mask(item)
                        masked_list.append(masked_item)
                        combined_map.update(reverse_map)
                    else:
                        masked_list.append(item)
                masked_data[key] = masked_list
            else:
                masked_data[key] = value

        return masked_data, combined_map
