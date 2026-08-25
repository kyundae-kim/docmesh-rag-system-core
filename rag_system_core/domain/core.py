from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from rag_system_core.domain.generation import GenerationService
from rag_system_core.domain.ingestion import IngestionService
from rag_system_core.domain.retrieval import RetrievalService
from rag_system_core.ports import (
    Chunker,
    DocumentAssetStorage,
    EmbeddingClient,
    GenerationClient,
    MetadataRepository,
    VectorStore,
)
from rag_system_core.types import (
    AuthenticatedUser,
    ChunkRecord,
    DocumentRecord,
    IngestionProgressRecord,
    IngestResult,
    QueryResult,
)


class RAGCore:
    def __init__(
        self,
        *,
        embedding_client: EmbeddingClient,
        generation_client: GenerationClient,
        vector_store: VectorStore,
        metadata_store: MetadataRepository,
        document_storage: DocumentAssetStorage,
        chunker: Chunker,
    ) -> None:
        self.embedding_client = embedding_client
        self.generation_client = generation_client
        self.metadata_store = metadata_store
        self.document_storage = document_storage
        self.vector_store = vector_store
        self.chunker = chunker
        self.ingestor = IngestionService(
            chunker=self.chunker,
            embedding_client=embedding_client,
            vector_store=self.vector_store,
            metadata_store=self.metadata_store,
            document_storage=self.document_storage,
        )
        self.retriever = RetrievalService(
            embedding_client=embedding_client,
            vector_store=self.vector_store,
        )
        self.generator = GenerationService(generation_client)

    def ingest_text(self, *, user: AuthenticatedUser, text: str, source: str) -> IngestResult:
        return self.ingestor.ingest_text(user_id=user.sub, text=text, source=source)

    def ingest_file_stream(
        self,
        *,
        user: AuthenticatedUser,
        file_stream: BinaryIO,
        source: str | None = None,
    ) -> IngestResult:
        if source is None or not source.strip():
            raise ValueError("source is required for stream ingestion")
        return self.ingestor.ingest_file_stream(
            user_id=user.sub,
            file_stream=file_stream,
            source=source,
        )

    def ingest_file_path(
        self,
        *,
        user: AuthenticatedUser,
        file_path: str | Path,
        source: str | None = None,
    ) -> IngestResult:
        return self.ingestor.ingest_file_path(
            user_id=user.sub,
            file_path=Path(file_path),
            source=source,
        )

    def query(
        self,
        *,
        user: AuthenticatedUser,
        question: str,
        top_k: int = 3,
    ) -> QueryResult:
        context = self.retriever.search(user_id=user.sub, question=question, top_k=top_k)
        return self.generator.generate(question=question, context_chunks=context)

    def list_documents(self, *, user: AuthenticatedUser) -> list[DocumentRecord]:
        return self.metadata_store.list_documents(user.sub)

    def get_document(self, doc_id: str, *, user: AuthenticatedUser) -> DocumentRecord | None:
        return self.metadata_store.get_document_for_user(doc_id=doc_id, user_id=user.sub)

    def list_document_chunks(self, doc_id: str, *, user: AuthenticatedUser) -> list[ChunkRecord]:
        return self.metadata_store.list_document_chunks(doc_id=doc_id, user_id=user.sub)

    def list_ingestion_progress(
        self,
        doc_id: str,
        *,
        user: AuthenticatedUser,
        job_id: str | None = None,
    ) -> list[IngestionProgressRecord]:
        return self.metadata_store.list_ingestion_progress(doc_id=doc_id, user_id=user.sub, job_id=job_id)

    def get_ingestion_step_statuses(
        self,
        doc_id: str,
        *,
        user: AuthenticatedUser,
        job_id: str | None = None,
    ) -> dict[str, str]:
        """Return the final known status for each ingestion pipeline step."""
        progress_rows = self.metadata_store.list_ingestion_progress(
            doc_id=doc_id,
            user_id=user.sub,
            job_id=job_id,
        )
        status_priority = {
            "not_started": 0,
            "running": 1,
            "completed": 2,
            "failed": 3,
        }
        statuses = {step_name: "not_started" for step_name in self.ingestor.PIPELINE_STEPS}
        if not progress_rows:
            document = self.metadata_store.get_document_for_user(doc_id=doc_id, user_id=user.sub)
            if job_id is None and document is not None:
                return statuses
            return {}
        for row in progress_rows:
            current_status = statuses.get(row.step_name, "not_started")
            if status_priority.get(row.status, 0) >= status_priority.get(current_status, 0):
                statuses[row.step_name] = row.status
        return statuses

    def delete_document(self, doc_id: str, *, user: AuthenticatedUser) -> bool:
        document = self.metadata_store.get_document_for_user(doc_id=doc_id, user_id=user.sub)
        if document is None:
            return False
        self.vector_store.delete_document(doc_id)
        self.document_storage.delete(document)
        deleted_document = self.metadata_store.delete_document(doc_id=doc_id, user_id=user.sub)
        if deleted_document is None:
            return False
        return True

__all__ = [
    "ChunkRecord",
    "DocumentRecord",
    "EmbeddingClient",
    "GenerationClient",
    "GenerationService",
    "IngestResult",
    "IngestionProgressRecord",
    "IngestionService",
    "QueryResult",
    "RAGCore",
    "RetrievalService",
    "VectorStore",
]
