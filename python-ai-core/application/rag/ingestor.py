"""
FinAgentX — Document Ingestor

End-to-end pipeline: PDF → parse → normalize → chunk → embed → store
"""

from __future__ import annotations

import logging
from typing import Any

from application.rag.chunker import SemanticChunker
from application.rag.embedding_manager import EmbeddingManager
from application.rag.indexer import IncrementalIndexer
from application.rag.parser import FinancialPDFParser
from domain.interfaces import VectorStore
from domain.schemas import FinancialDocument

logger = logging.getLogger(__name__)


class DocumentIngestor:
    """End-to-end document ingestion pipeline."""

    def __init__(
        self,
        vector_store: VectorStore,
        chunker: SemanticChunker,
        indexer: IncrementalIndexer,
        embedding_manager: EmbeddingManager,
        *,
        collection_name: str = "FinancialDocuments",
    ):
        self.vector_store = vector_store
        self.chunker = chunker
        self.indexer = indexer
        self.embedding_manager = embedding_manager
        self.collection_name = collection_name
        self.parser = FinancialPDFParser()

    async def ingest_pdf(self, pdf_path: str) -> dict[str, Any]:
        """Ingest a PDF into the vector store."""
        documents = self.parser.parse(pdf_path)
        total_chunks = 0

        for doc in documents:
            chunks_count = await self.ingest_document(doc)
            total_chunks += chunks_count

        return {
            "documents_processed": len(documents),
            "total_chunks": total_chunks,
            "source": pdf_path,
        }

    async def ingest_document(self, doc: FinancialDocument) -> int:
        """Ingest a single document."""
        if not self.indexer.needs_indexing(doc.document_id, doc.text):
            logger.info(f"Document {doc.document_id} unchanged, skipping.")
            return 0

        version = self.embedding_manager.get_current_version()
        metadata = {
            "ticker": doc.ticker,
            "document_type": doc.document_type,
            "period": doc.period,
            **doc.metadata,
        }

        chunks = self.chunker.chunk_document(
            doc.text,
            document_id=doc.document_id,
            metadata=metadata,
            embedding_model=version.model_name,
            embedding_version=version.model_version,
        )

        if doc.period:
            chunks = self.indexer.apply_freshness_to_chunks(chunks, doc.period)

        # Weaviate handles embedding via text2vec module
        await self.vector_store.upsert(
            self.collection_name,
            chunks,
            embeddings=[[] for _ in chunks],  # Weaviate auto-embeds
        )

        self.indexer.mark_indexed(doc.document_id, doc.text)
        logger.info(f"Ingested {len(chunks)} chunks from {doc.document_id}")

        return len(chunks)

    async def ingest_financial_statements(
        self, statements: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Ingest financial statement data (from yfinance)."""
        total_chunks = 0

        for stmt in statements:
            doc = FinancialDocument(
                document_id=stmt["document_id"],
                ticker=stmt.get("ticker", ""),
                document_type=stmt.get("document_type", ""),
                period=stmt.get("period", ""),
                text=stmt.get("text", ""),
                data=stmt.get("data", {}),
                metadata=stmt.get("metadata", {}),
            )
            count = await self.ingest_document(doc)
            total_chunks += count

        return {
            "documents_processed": len(statements),
            "total_chunks": total_chunks,
        }
