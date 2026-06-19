from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, Callable

from rag_system_core.adapters.chunking import FixedWindowChunker
from rag_system_core.composition.auth import resolve_user_id
from rag_system_core.composition.health import run_health_checks
from rag_system_core.composition.docmesh_runtime import resolve_milvus_runtime_settings
from rag_system_core.domain.generation import GenerationService
from rag_system_core.domain.ingestion import IngestionService
from rag_system_core.domain.retrieval import RetrievalService
from rag_system_core.storage.document_storage import DocumentStorage
from rag_system_core.storage.metadata_store import ChunkModel, DocumentModel, IngestionProgressModel, MetadataStore
from rag_system_core.storage.vector_store import MilvusClient, MilvusLiteVectorStore, VectorStore
from rag_system_core.types import (
    ChunkRecord,
    DocumentRecord,
    EmbeddingClient,
    GenerationClient,
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
        metadata_path: str | Path,
        document_storage_dir: str | Path,
        storage_mode: str = "memory",
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.embedding_client = embedding_client
        self.generation_client = generation_client
        metadata_path = Path(metadata_path)
        self.metadata_store = MetadataStore(metadata_path)
        self.document_storage = DocumentStorage(storage_mode, Path(document_storage_dir))
        if vector_store is None:
            milvus_uri, milvus_collection_name, milvus_timeout = resolve_milvus_runtime_settings(
                fallback_uri=str(metadata_path.with_suffix(".milvus.db"))
            )
            vector_store = MilvusLiteVectorStore(
                uri=milvus_uri,
                collection_name=milvus_collection_name,
                timeout=milvus_timeout,
            )
        self.vector_store = vector_store
        self.ingestor = IngestionService(
            chunker=FixedWindowChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap),
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

    def ingest_text(self, *, text: str, source: str, token: str | None = None) -> IngestResult:
        resolved_user_id = resolve_user_id(token)
        return self.ingestor.ingest_text(user_id=resolved_user_id, text=text, source=source)

    def ingest_file_stream(
        self,
        *,
        file_stream: BinaryIO,
        source: str | None = None,
        token: str | None = None,
    ) -> IngestResult:
        resolved_user_id = resolve_user_id(token)
        if source is None or not source.strip():
            raise ValueError("source is required for stream ingestion")
        return self.ingestor.ingest_file_stream(
            user_id=resolved_user_id,
            file_stream=file_stream,
            source=source,
        )

    def ingest_file_path(
        self,
        *,
        file_path: str | Path,
        token: str | None = None,
        source: str | None = None,
    ) -> IngestResult:
        resolved_user_id = resolve_user_id(token)
        return self.ingestor.ingest_file_path(
            user_id=resolved_user_id,
            file_path=Path(file_path),
            source=source,
        )

    def query(
        self,
        *,
        question: str,
        top_k: int = 3,
        token: str | None = None,
    ) -> QueryResult:
        resolved_user_id = resolve_user_id(token)
        context = self.retriever.search(user_id=resolved_user_id, question=question, top_k=top_k)
        return self.generator.generate(question=question, context_chunks=context)

    def list_documents(self, token: str | None = None) -> list[DocumentRecord]:
        resolved_user_id = resolve_user_id(token)
        return self.metadata_store.list_documents(resolved_user_id)

    def get_document(self, doc_id: str, *, token: str | None = None) -> DocumentRecord | None:
        resolved_user_id = resolve_user_id(token)
        return self.metadata_store.get_document_for_user(doc_id=doc_id, user_id=resolved_user_id)

    def list_document_chunks(self, doc_id: str, *, token: str | None = None) -> list[ChunkRecord]:
        resolved_user_id = resolve_user_id(token)
        return self.metadata_store.list_document_chunks(doc_id=doc_id, user_id=resolved_user_id)

    def list_ingestion_progress(
        self,
        doc_id: str,
        *,
        token: str | None = None,
        job_id: str | None = None,
    ) -> list[IngestionProgressRecord]:
        resolved_user_id = resolve_user_id(token)
        return self.metadata_store.list_ingestion_progress(doc_id=doc_id, user_id=resolved_user_id, job_id=job_id)

    def delete_document(self, doc_id: str, *, token: str | None = None) -> bool:
        resolved_user_id = resolve_user_id(token)
        document = self.metadata_store.get_document_for_user(doc_id=doc_id, user_id=resolved_user_id)
        if document is None:
            return False
        self.vector_store.delete_document(doc_id)
        deleted_document = self.metadata_store.delete_document(doc_id=doc_id, user_id=resolved_user_id)
        if deleted_document is None:
            return False
        self.document_storage.delete(deleted_document)
        return True

    def health_check(self):
        service_checks: dict[str, Callable[[], None]] = {"metadata": self.metadata_store.check}
        if hasattr(self.vector_store, "check"):
            service_checks["milvus"] = self.vector_store.check
        if hasattr(self.embedding_client, "check"):
            service_checks["embedding"] = self.embedding_client.check
        if hasattr(self.generation_client, "check"):
            service_checks["generation"] = self.generation_client.check
        return run_health_checks(service_checks, required_services=set(service_checks))


__all__ = [
    "ChunkModel",
    "ChunkRecord",
    "DocumentModel",
    "DocumentRecord",
    "DocumentStorage",
    "EmbeddingClient",
    "FixedWindowChunker",
    "GenerationClient",
    "GenerationService",
    "IngestionProgressModel",
    "IngestionProgressRecord",
    "IngestionService",
    "IngestResult",
    "MetadataStore",
    "MilvusClient",
    "MilvusLiteVectorStore",
    "QueryResult",
    "RAGCore",
    "RetrievalService",
    "VectorStore",
]
