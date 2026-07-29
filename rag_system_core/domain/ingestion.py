from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Callable, TypeVar
from uuid import uuid4

from rag_system_core.ports import (
    Chunker,
    DocumentAssetStorage,
    EmbeddingClient,
    MetadataRepository,
    VectorStore,
)
from rag_system_core.types import (
    ChunkRecord,
    DocumentRecord,
    IngestionProgressRecord,
    IngestResult,
)

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class _ProgressContext:
    job_id: str
    doc_id: str
    user_id: str
    source: str
    created_at: str


class IngestionService:
    PIPELINE_STEPS = [
        "load",
        "preprocess",
        "chunking",
        "embedding",
        "vector_store",
        "chunk_persistence",
    ]

    def __init__(
        self,
        *,
        chunker: Chunker,
        embedding_client: EmbeddingClient,
        vector_store: VectorStore,
        metadata_store: MetadataRepository,
        document_storage: DocumentAssetStorage,
    ) -> None:
        self.chunker = chunker
        self.embedding_client = embedding_client
        self.vector_store = vector_store
        self.metadata_store = metadata_store
        self.document_storage = document_storage

    def ingest_text(self, *, user_id: str, text: str, source: str) -> IngestResult:
        normalized = self.preprocess(text)
        doc_id = str(uuid4())
        job_id = str(uuid4())
        asset_reference = self.document_storage.store_text(
            doc_id=doc_id,
            user_id=user_id,
            text=normalized,
            source=source,
            idempotency_key=job_id,
        )
        return self._finalize_ingest(
            user_id=user_id,
            text=normalized,
            source=source,
            doc_id=doc_id,
            job_id=job_id,
            asset_reference=asset_reference,
        )

    def ingest_file_stream(self, *, user_id: str, file_stream: BinaryIO, source: str) -> IngestResult:
        payload = file_stream.read()
        text = payload.decode("utf-8")
        doc_id = str(uuid4())
        job_id = str(uuid4())
        asset_reference = self.document_storage.store_file_stream(
            doc_id=doc_id,
            user_id=user_id,
            file_stream=BytesIO(payload),
            size=len(payload),
            source=source,
            idempotency_key=job_id,
        )
        return self._finalize_ingest(
            user_id=user_id,
            text=text,
            source=source,
            doc_id=doc_id,
            job_id=job_id,
            asset_reference=asset_reference,
        )

    def ingest_file_path(self, *, user_id: str, file_path: Path, source: str | None = None) -> IngestResult:
        payload = file_path.read_bytes()
        resolved_source = source or file_path.name
        doc_id = str(uuid4())
        job_id = str(uuid4())
        asset_reference = self.document_storage.store_file_path(
            doc_id=doc_id,
            user_id=user_id,
            file_path=file_path,
            source=resolved_source,
            idempotency_key=job_id,
        )
        return self._finalize_ingest(
            user_id=user_id,
            text=payload.decode("utf-8"),
            source=resolved_source,
            doc_id=doc_id,
            job_id=job_id,
            asset_reference=asset_reference,
        )

    def _finalize_ingest(
        self,
        *,
        user_id: str,
        text: str,
        source: str,
        doc_id: str,
        job_id: str,
        asset_reference: str,
    ) -> IngestResult:
        created_at = datetime.now(UTC).isoformat()
        context = _ProgressContext(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            created_at=created_at,
        )
        document_record = DocumentRecord(
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            created_at=created_at,
            asset_reference=asset_reference,
        )
        self.metadata_store.add_document(document_record)

        self._run_step(context, "load", lambda: None)
        normalized = self._run_step(context, "preprocess", lambda: self.preprocess(text))
        chunks = self._run_step(context, "chunking", lambda: self._require_chunks(normalized))

        chunk_records = [
            ChunkRecord(
                chunk_id="",
                doc_id=doc_id,
                user_id=user_id,
                content=chunk,
                metadata={"source": source},
            )
            for chunk in chunks
        ]

        embeddings = self._run_step(context, "embedding", lambda: self.embed(chunks))
        generated_chunk_ids = self._run_step(
            context,
            "vector_store",
            lambda: self._add_vectors(chunk_records, embeddings),
            completion_failure_rollback=self.vector_store.delete_chunks,
        )
        self._run_step(
            context,
            "chunk_persistence",
            lambda: self._persist_chunks(chunk_records, generated_chunk_ids),
            completion_failure_rollback=lambda _: self._rollback_persisted_chunks(generated_chunk_ids),
        )

        return IngestResult(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            created_at=created_at,
            chunk_count=len(chunk_records),
        )

    def preprocess(self, text: str) -> str:
        return text.strip()

    def chunk(self, text: str) -> list[str]:
        return self.chunker.chunk(text)

    def embed(self, chunks: list[str]) -> list[list[float]]:
        return self.embedding_client.embed(chunks)

    def _run_step(
        self,
        context: _ProgressContext,
        step_name: str,
        operation: Callable[[], T],
        completion_failure_rollback: Callable[[T], None] | None = None,
    ) -> T:
        self._record_progress_transition(context=context, step_name=step_name, status="running")
        try:
            result = operation()
        except Exception as operation_error:
            try:
                self._record_progress_transition(context=context, step_name=step_name, status="failed")
            except Exception as progress_error:
                operation_error.add_note(f"Failed to persist failed progress: {progress_error!r}")
            raise
        try:
            self._record_progress_transition(context=context, step_name=step_name, status="completed")
        except Exception as completion_error:
            if completion_failure_rollback is not None:
                try:
                    completion_failure_rollback(result)
                except Exception as rollback_error:
                    completion_error.add_note(f"Completion rollback failed: {rollback_error!r}")
            raise
        return result

    def _require_chunks(self, text: str) -> list[str]:
        chunks = self.chunk(text)
        if not chunks:
            raise ValueError("Document must contain non-empty text")
        return chunks

    def _add_vectors(self, chunks: list[ChunkRecord], embeddings: list[list[float]]) -> list[str]:
        generated_chunk_ids = self.vector_store.add(chunks, embeddings)
        if len(generated_chunk_ids) != len(chunks):
            self.vector_store.delete_chunks(generated_chunk_ids)
            raise RuntimeError("Milvus returned a mismatched number of chunk ids")
        return generated_chunk_ids

    def _persist_chunks(self, chunks: list[ChunkRecord], generated_chunk_ids: list[str]) -> None:
        persisted_chunks = [
            ChunkRecord(
                chunk_id=chunk_id,
                doc_id=chunk.doc_id,
                user_id=chunk.user_id,
                content=chunk.content,
                metadata=dict(chunk.metadata),
            )
            for chunk, chunk_id in zip(chunks, generated_chunk_ids, strict=True)
        ]
        try:
            self.metadata_store.add_chunks(persisted_chunks)
        except Exception:
            self.vector_store.delete_chunks(generated_chunk_ids)
            raise

    def _rollback_persisted_chunks(self, chunk_ids: list[str]) -> None:
        rollback_errors: list[Exception] = []
        for rollback in (
            lambda: self.metadata_store.delete_chunks(chunk_ids),
            lambda: self.vector_store.delete_chunks(chunk_ids),
        ):
            try:
                rollback()
            except Exception as error:
                rollback_errors.append(error)
        if rollback_errors:
            raise ExceptionGroup("Failed to rollback persisted chunks", rollback_errors)

    def _record_progress_transition(
        self,
        *,
        context: _ProgressContext,
        step_name: str,
        status: str,
    ) -> None:
        self.metadata_store.add_ingestion_progress(
            [
                IngestionProgressRecord(
                    progress_id=str(uuid4()),
                    job_id=context.job_id,
                    doc_id=context.doc_id,
                    user_id=context.user_id,
                    source=context.source,
                    step_name=step_name,
                    step_order=self.PIPELINE_STEPS.index(step_name),
                    status=status,
                    created_at=context.created_at,
                )
            ]
        )

    def store(self, chunks: list[ChunkRecord], embeddings: list[list[float]]) -> None:
        generated_chunk_ids = self._add_vectors(chunks, embeddings)
        self._persist_chunks(chunks, generated_chunk_ids)
