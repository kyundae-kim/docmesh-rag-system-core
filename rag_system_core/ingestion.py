from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from rag_system_core.helpers import (
    ChunkRecord,
    DocumentRecord,
    DocumentStorage,
    EmbeddingClient,
    FixedWindowChunker,
    IngestResult,
    IngestionProgressRecord,
    extract_doc_id_from_storage_path,
)
from rag_system_core.metadata_store import MetadataStore
from rag_system_core.vector_store import VectorStore


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
        chunker: FixedWindowChunker,
        embedding_client: EmbeddingClient,
        vector_store: VectorStore,
        metadata_store: MetadataStore,
        document_storage: DocumentStorage,
    ) -> None:
        self.chunker = chunker
        self.embedding_client = embedding_client
        self.vector_store = vector_store
        self.metadata_store = metadata_store
        self.document_storage = document_storage

    def ingest_text(self, *, user_id: str, text: str, source: str) -> IngestResult:
        normalized = self.preprocess(text)
        storage_path = self.document_storage.store_text(
            doc_id=str(uuid4()),
            text=normalized,
            source=source,
        )
        doc_id = extract_doc_id_from_storage_path(storage_path)
        return self._finalize_ingest(
            user_id=user_id,
            text=normalized,
            source=source,
            doc_id=doc_id,
            storage_path=storage_path,
        )

    def ingest_file_stream(self, *, user_id: str, file_stream: BinaryIO, source: str) -> IngestResult:
        payload = file_stream.read()
        text = payload.decode("utf-8")
        doc_id = str(uuid4())
        storage_path = self.document_storage.store_file_stream(
            doc_id=doc_id,
            file_stream=BytesIO(payload),
            source=source,
        )
        return self._finalize_ingest(
            user_id=user_id,
            text=text,
            source=source,
            doc_id=doc_id,
            storage_path=storage_path,
        )

    def ingest_file_path(self, *, user_id: str, file_path: Path, source: str | None = None) -> IngestResult:
        payload = file_path.read_bytes()
        resolved_source = source or file_path.name
        doc_id = str(uuid4())
        storage_path = self.document_storage.store_file_path(
            doc_id=doc_id,
            file_path=file_path,
            source=resolved_source,
        )
        return self._finalize_ingest(
            user_id=user_id,
            text=payload.decode("utf-8"),
            source=resolved_source,
            doc_id=doc_id,
            storage_path=storage_path,
        )

    def _finalize_ingest(
        self,
        *,
        user_id: str,
        text: str,
        source: str,
        doc_id: str,
        storage_path: str,
    ) -> IngestResult:
        job_id = str(uuid4())
        created_at = datetime.now(UTC).isoformat()
        document_record = DocumentRecord(
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            created_at=created_at,
            storage_path=storage_path,
        )
        self.metadata_store.add_document(document_record)

        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="load",
            status="running",
            created_at=created_at,
        )
        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="load",
            status="completed",
            created_at=created_at,
        )

        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="preprocess",
            status="running",
            created_at=created_at,
        )
        normalized = self.preprocess(text)
        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="preprocess",
            status="completed",
            created_at=created_at,
        )

        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="chunking",
            status="running",
            created_at=created_at,
        )
        chunks = self.chunk(normalized)
        if not chunks:
            self._record_progress_transition(
                job_id=job_id,
                doc_id=doc_id,
                user_id=user_id,
                source=source,
                step_name="chunking",
                status="failed",
                created_at=created_at,
            )
            raise ValueError("Document must contain non-empty text")
        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="chunking",
            status="completed",
            created_at=created_at,
        )

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

        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="embedding",
            status="running",
            created_at=created_at,
        )
        try:
            embeddings = self.embed(chunks)
        except Exception:
            self._record_progress_transition(
                job_id=job_id,
                doc_id=doc_id,
                user_id=user_id,
                source=source,
                step_name="embedding",
                status="failed",
                created_at=created_at,
            )
            raise
        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="embedding",
            status="completed",
            created_at=created_at,
        )

        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="vector_store",
            status="running",
            created_at=created_at,
        )
        try:
            generated_chunk_ids = self.vector_store.add(chunk_records, embeddings)
        except Exception:
            self._record_progress_transition(
                job_id=job_id,
                doc_id=doc_id,
                user_id=user_id,
                source=source,
                step_name="vector_store",
                status="failed",
                created_at=created_at,
            )
            raise
        if len(generated_chunk_ids) != len(chunk_records):
            self._record_progress_transition(
                job_id=job_id,
                doc_id=doc_id,
                user_id=user_id,
                source=source,
                step_name="vector_store",
                status="failed",
                created_at=created_at,
            )
            raise RuntimeError("Milvus returned a mismatched number of chunk ids")
        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="vector_store",
            status="completed",
            created_at=created_at,
        )

        persisted_chunk_records = [
            ChunkRecord(
                chunk_id=chunk_id,
                doc_id=chunk.doc_id,
                user_id=chunk.user_id,
                content=chunk.content,
                metadata=dict(chunk.metadata),
            )
            for chunk, chunk_id in zip(chunk_records, generated_chunk_ids, strict=True)
        ]

        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="chunk_persistence",
            status="running",
            created_at=created_at,
        )
        try:
            self.metadata_store.add_chunks(persisted_chunk_records)
        except Exception:
            self.vector_store.delete_chunks(generated_chunk_ids)
            self._record_progress_transition(
                job_id=job_id,
                doc_id=doc_id,
                user_id=user_id,
                source=source,
                step_name="chunk_persistence",
                status="failed",
                created_at=created_at,
            )
            raise
        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="chunk_persistence",
            status="completed",
            created_at=created_at,
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

    def _record_progress_transition(
        self,
        *,
        job_id: str,
        doc_id: str,
        user_id: str,
        source: str,
        step_name: str,
        status: str,
        created_at: str,
    ) -> None:
        self.metadata_store.add_ingestion_progress(
            [
                IngestionProgressRecord(
                    progress_id=str(uuid4()),
                    job_id=job_id,
                    doc_id=doc_id,
                    user_id=user_id,
                    source=source,
                    step_name=step_name,
                    step_order=self.PIPELINE_STEPS.index(step_name),
                    status=status,
                    created_at=created_at,
                )
            ]
        )

    def store(self, chunks: list[ChunkRecord], embeddings: list[list[float]]) -> None:
        generated_chunk_ids = self.vector_store.add(chunks, embeddings)
        if len(generated_chunk_ids) != len(chunks):
            self.vector_store.delete_chunks(generated_chunk_ids)
            raise RuntimeError("Milvus returned a mismatched number of chunk ids")
        persisted_chunk_records = [
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
            self.metadata_store.add_chunks(persisted_chunk_records)
        except Exception:
            self.vector_store.delete_chunks(generated_chunk_ids)
            raise
