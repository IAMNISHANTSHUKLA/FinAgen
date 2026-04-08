"""
FinAgentX — Weaviate Vector Store Client

Implements VectorStore interface for Weaviate.
Supports hybrid search (BM25 + dense) with tuned RRF fusion (Fix #3).
"""

from __future__ import annotations

import logging
from typing import Any

import weaviate
from weaviate.classes.config import Configure, DataType, Property
from weaviate.classes.query import HybridFusion, MetadataQuery

from domain.interfaces import VectorStore
from domain.schemas import Chunk, RetrievalResult

logger = logging.getLogger(__name__)


class WeaviateClient(VectorStore):
    """Weaviate vector store implementation with hybrid search."""

    def __init__(self, url: str = "http://localhost:8081"):
        self.client = weaviate.connect_to_local(
            host=url.replace("http://", "").split(":")[0],
            port=int(url.split(":")[-1]) if ":" in url.split("//")[-1] else 8080,
        )
        logger.info(f"Connected to Weaviate at {url}")

    async def create_collection(
        self,
        name: str,
        *,
        embedding_dim: int = 384,
        metadata_schema: dict[str, str] | None = None,
    ) -> None:
        """Create a collection with financial document schema."""
        if self.client.collections.exists(name):
            logger.info(f"Collection '{name}' already exists, skipping creation.")
            return

        properties = [
            Property(name="text", data_type=DataType.TEXT),
            Property(name="chunk_id", data_type=DataType.TEXT),
            Property(name="document_id", data_type=DataType.TEXT),
            Property(name="ticker", data_type=DataType.TEXT),
            Property(name="document_type", data_type=DataType.TEXT),
            Property(name="period", data_type=DataType.TEXT),
            Property(name="section", data_type=DataType.TEXT),
            Property(name="parent_chunk_id", data_type=DataType.TEXT),
            Property(name="embedding_model", data_type=DataType.TEXT),
            Property(name="embedding_version", data_type=DataType.TEXT),
            Property(name="freshness_score", data_type=DataType.NUMBER),
            # Access control (Fix #13)
            Property(name="access_roles", data_type=DataType.TEXT_ARRAY),
        ]

        self.client.collections.create(
            name=name,
            vectorizer_config=Configure.Vectorizer.text2vec_transformers(),
            properties=properties,
        )
        logger.info(f"Created collection '{name}' with {len(properties)} properties.")

    async def upsert(
        self,
        collection: str,
        chunks: list[Chunk],
        embeddings: list[list[float]],
    ) -> None:
        """Insert or update chunks with their embeddings."""
        col = self.client.collections.get(collection)

        with col.batch.dynamic() as batch:
            for chunk, embedding in zip(chunks, embeddings):
                properties = {
                    "text": chunk.text,
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "ticker": chunk.metadata.get("ticker", ""),
                    "document_type": chunk.metadata.get("document_type", ""),
                    "period": chunk.metadata.get("period", ""),
                    "section": chunk.metadata.get("section", ""),
                    "parent_chunk_id": chunk.parent_chunk_id or "",
                    "embedding_model": chunk.embedding_model,
                    "embedding_version": chunk.embedding_version,
                    "freshness_score": chunk.freshness_score,
                    "access_roles": chunk.metadata.get("access_roles", ["public"]),
                }
                batch.add_object(properties=properties, vector=embedding)

        logger.info(f"Upserted {len(chunks)} chunks to '{collection}'.")

    async def hybrid_search(
        self,
        collection: str,
        query: str,
        *,
        alpha: float = 0.75,
        top_k: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        """
        Hybrid search: dense + BM25 with Reciprocal Rank Fusion.

        Fix #3: alpha=0.75 leans on dense for semantic matching,
        BM25 catches exact amounts/merchants/tickers.
        RELATIVE_SCORE fusion is more stable across collection sizes.
        """
        col = self.client.collections.get(collection)

        # Build Weaviate filter from dict
        weaviate_filter = None
        if filters:
            from weaviate.classes.query import Filter

            filter_conditions = []
            for key, value in filters.items():
                if isinstance(value, list):
                    filter_conditions.append(
                        Filter.by_property(key).contains_any(value)
                    )
                else:
                    filter_conditions.append(
                        Filter.by_property(key).equal(value)
                    )

            if len(filter_conditions) == 1:
                weaviate_filter = filter_conditions[0]
            elif len(filter_conditions) > 1:
                weaviate_filter = Filter.all_of(filter_conditions)

        results = col.query.hybrid(
            query=query,
            alpha=alpha,
            fusion_type=HybridFusion.RELATIVE_SCORE,
            limit=top_k,
            return_metadata=MetadataQuery(score=True, distance=True),
            filters=weaviate_filter,
        )

        retrieval_results = []
        for obj in results.objects:
            chunk = Chunk(
                chunk_id=obj.properties.get("chunk_id", ""),
                document_id=obj.properties.get("document_id", ""),
                text=obj.properties.get("text", ""),
                start_idx=0,
                end_idx=len(obj.properties.get("text", "")),
                metadata={
                    "ticker": obj.properties.get("ticker", ""),
                    "document_type": obj.properties.get("document_type", ""),
                    "period": obj.properties.get("period", ""),
                    "section": obj.properties.get("section", ""),
                },
                parent_chunk_id=obj.properties.get("parent_chunk_id") or None,
                embedding_model=obj.properties.get("embedding_model", ""),
                embedding_version=obj.properties.get("embedding_version", ""),
                freshness_score=obj.properties.get("freshness_score", 1.0),
            )

            score = obj.metadata.score if obj.metadata and obj.metadata.score else 0.0

            retrieval_results.append(
                RetrievalResult(
                    chunk=chunk,
                    score=score,
                    retrieval_method="hybrid",
                )
            )

        logger.info(
            f"Hybrid search returned {len(retrieval_results)} results "
            f"(alpha={alpha}, top_k={top_k})"
        )
        return retrieval_results

    async def delete_collection(self, name: str) -> None:
        if self.client.collections.exists(name):
            self.client.collections.delete(name)
            logger.info(f"Deleted collection '{name}'.")

    async def get_collection_info(self, name: str) -> dict[str, Any]:
        if not self.client.collections.exists(name):
            return {"exists": False}

        col = self.client.collections.get(name)
        aggregate = col.aggregate.over_all(total_count=True)
        return {
            "exists": True,
            "name": name,
            "total_count": aggregate.total_count,
        }

    def close(self) -> None:
        self.client.close()
