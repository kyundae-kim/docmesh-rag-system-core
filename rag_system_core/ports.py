from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, Callable, Protocol

from rag_system_core.types import ChunkRecord, DocumentRecord, IngestionProgressRecord


class Chunker(Protocol):
    def chunk(self, text: str) -> list[str]: ...


class VectorStore(Protocol):
    def add(self, chunks: list[ChunkRecord], vectors: list[list[float]]) -> list[str]: ...

    def search(self, *, user_id: str, query_vector: list[float], top_k: int) -> list[ChunkRecord]: ...

    def delete_document(self, doc_id: str) -> None: ...

    def delete_chunks(self, chunk_ids: list[str]) -> None: ...


class MetadataRepository(Protocol):
    def add_document(self, document: DocumentRecord) -> None: ...

    def add_chunks(self, chunks: list[ChunkRecord]) -> None: ...

    def delete_chunks(self, chunk_ids: list[str]) -> None: ...

    def add_ingestion_progress(self, progress_rows: list[IngestionProgressRecord]) -> None: ...

    def get_document_for_user(self, *, doc_id: str, user_id: str) -> DocumentRecord | None: ...

    def list_documents(self, user_id: str) -> list[DocumentRecord]: ...

    def list_document_chunks(self, *, doc_id: str, user_id: str) -> list[ChunkRecord]: ...

    def list_ingestion_progress(
        self,
        *,
        doc_id: str,
        user_id: str,
        job_id: str | None = None,
    ) -> list[IngestionProgressRecord]: ...

    def delete_document(self, *, doc_id: str, user_id: str) -> DocumentRecord | None: ...

    def check(self) -> None: ...


class DocumentAssetStorage(Protocol):
    def store_text(
        self,
        *,
        doc_id: str,
        user_id: str,
        text: str,
        source: str,
        idempotency_key: str,
    ) -> str: ...

    def store_file_stream(
        self,
        *,
        doc_id: str,
        user_id: str,
        file_stream: BinaryIO,
        size: int,
        source: str,
        idempotency_key: str,
    ) -> str: ...

    def store_file_path(
        self,
        *,
        doc_id: str,
        user_id: str,
        file_path: Path,
        source: str | None = None,
        idempotency_key: str,
    ) -> str: ...

    def load(self, document: DocumentRecord) -> str | None: ...

    def delete(self, document: DocumentRecord) -> None: ...


class HealthCheckRunner(Protocol):
    def __call__(
        self,
        service_checks: dict[str, Callable[[], None]],
        required_services: set[str] | None = None,
    ) -> object: ...


__all__ = [
    "Chunker",
    "DocumentAssetStorage",
    "HealthCheckRunner",
    "MetadataRepository",
    "VectorStore",
]
