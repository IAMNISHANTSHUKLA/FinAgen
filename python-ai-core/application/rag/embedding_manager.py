"""
FinAgentX — Embedding Manager (Fix #4)

- Version tracking — store model name + version per embedding
- Re-embed trigger — detect model change, queue full re-embedding
- Metadata storage — embedding dim, model, timestamp per collection
"""

from __future__ import annotations

import logging
from datetime import datetime

from domain.exceptions import EmbeddingVersionMismatch
from domain.schemas import EmbeddingVersion

logger = logging.getLogger(__name__)


class EmbeddingManager:
    """
    Manages embedding model versions and triggers re-embedding
    when the model changes.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        model_version: str = "1.0.0",
        embedding_dim: int = 384,
    ):
        self.current = EmbeddingVersion(
            model_name=model_name,
            model_version=model_version,
            embedding_dim=embedding_dim,
            created_at=datetime.utcnow(),
            document_count=0,
            is_current=True,
        )
        # Registry of collection versions
        self._collection_versions: dict[str, EmbeddingVersion] = {}

    def register_collection(
        self, collection_name: str, version: EmbeddingVersion
    ) -> None:
        """Register the embedding version used by a collection."""
        self._collection_versions[collection_name] = version
        logger.info(
            f"Registered collection '{collection_name}' with "
            f"model={version.model_name} version={version.model_version}"
        )

    def check_compatibility(self, collection_name: str) -> bool:
        """
        Check if current embedding model matches collection version.

        Returns True if compatible, raises if mismatch detected.
        """
        stored = self._collection_versions.get(collection_name)
        if stored is None:
            return True  # New collection, no version conflict

        if (
            stored.model_name != self.current.model_name
            or stored.model_version != self.current.model_version
        ):
            logger.warning(
                f"Embedding version mismatch for '{collection_name}': "
                f"stored={stored.model_name}@{stored.model_version}, "
                f"current={self.current.model_name}@{self.current.model_version}"
            )
            raise EmbeddingVersionMismatch(
                f"Collection '{collection_name}' uses {stored.model_name}@{stored.model_version}, "
                f"but current model is {self.current.model_name}@{self.current.model_version}. "
                f"Re-embedding required.",
                current_version=f"{self.current.model_name}@{self.current.model_version}",
                collection_version=f"{stored.model_name}@{stored.model_version}",
            )

        return True

    def needs_reembed(self, collection_name: str) -> bool:
        """Check if collection needs re-embedding due to model change."""
        try:
            self.check_compatibility(collection_name)
            return False
        except EmbeddingVersionMismatch:
            return True

    def get_current_version(self) -> EmbeddingVersion:
        """Get current embedding model version info."""
        return self.current

    def update_document_count(self, collection_name: str, count: int) -> None:
        """Update document count for a collection."""
        if collection_name in self._collection_versions:
            self._collection_versions[collection_name].document_count = count
