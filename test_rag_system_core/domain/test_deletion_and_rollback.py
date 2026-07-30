from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from rag_system_core.adapters.chunking import FixedWindowChunker
from rag_system_core.domain.ingestion import IngestionService
from rag_system_core.ports import VectorStore
from rag_system_core.storage.metadata_store import MetadataStore
from rag_system_core.types import ChunkRecord

from test_rag_system_core.support import (
    authenticated_user,
    create_test_rig,
    FakeDocumentStorage,
    FakeEmbeddingClient,
)

USER_A = authenticated_user("user-a")


def test_delete_document_removes_metadata_chunks_asset_and_query_visibility(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path, storage_mode="local")
    target = rig.core.ingest_text(
        user=USER_A,
        text="alpha one. beta two. gamma three. delta four. epsilon five.",
        source="target.txt",
    )
    survivor = rig.core.ingest_text(
        user=USER_A,
        text="beta survivor document only.",
        source="survivor.txt",
    )
    stored = rig.core.get_document(target.doc_id, user=USER_A)
    assert stored is not None
    assert stored.asset_reference is not None
    stored_path = Path(stored.asset_reference)
    assert stored_path.exists()
    assert rig.core.list_ingestion_progress(target.doc_id, user=USER_A)

    deleted = rig.core.delete_document(target.doc_id, user=USER_A)

    assert deleted is True
    assert rig.core.get_document(target.doc_id, user=USER_A) is None
    assert rig.core.list_document_chunks(target.doc_id, user=USER_A) == []
    assert rig.core.list_ingestion_progress(target.doc_id, user=USER_A) == []
    assert not stored_path.exists()
    assert [doc.doc_id for doc in rig.core.list_documents(user=USER_A)] == [survivor.doc_id]

    response = rig.core.query(user=USER_A, question="Where is alpha?", top_k=5)
    assert all(chunk.doc_id != target.doc_id for chunk in response.context_chunks)


def test_ingestion_service_store_rolls_back_milvus_chunks_when_chunk_persistence_fails(tmp_path: Path) -> None:
    class FakeVectorStore:
        def __init__(self) -> None:
            self.deleted_chunk_ids: list[list[str]] = []

        def add(self, chunks, vectors):
            del chunks, vectors
            return ["101"]

        def delete_chunks(self, chunk_ids):
            self.deleted_chunk_ids.append(list(chunk_ids))

    class FailingMetadataStore:
        def add_chunks(self, chunks):
            del chunks
            raise RuntimeError("sqlite write failed")

    vector_store = FakeVectorStore()
    metadata_store = FailingMetadataStore()
    service = IngestionService(
        chunker=FixedWindowChunker(chunk_size=32, chunk_overlap=4),
        embedding_client=FakeEmbeddingClient(),
        vector_store=cast(VectorStore, vector_store),
        metadata_store=cast(MetadataStore, metadata_store),
        document_storage=FakeDocumentStorage("memory", tmp_path / "documents"),
    )
    chunks = [
        ChunkRecord(
            chunk_id="",
            doc_id="doc-1",
            user_id="user-a",
            content="alpha",
            metadata={"source": "x.txt"},
        )
    ]

    with pytest.raises(RuntimeError, match="sqlite write failed"):
        service.store(chunks, [[1.0, 0.0, 0.0, 5.0]])

    assert vector_store.deleted_chunk_ids == [["101"]]


def test_ingestion_service_store_rolls_back_milvus_chunks_when_generated_id_count_is_mismatched(tmp_path: Path) -> None:
    class FakeVectorStore:
        def __init__(self) -> None:
            self.deleted_chunk_ids: list[list[str]] = []

        def add(self, chunks, vectors):
            del chunks, vectors
            return ["101"]

        def delete_chunks(self, chunk_ids):
            self.deleted_chunk_ids.append(list(chunk_ids))

    class MetadataStoreSpy:
        def __init__(self) -> None:
            self.add_chunks_calls = 0

        def add_chunks(self, chunks):
            del chunks
            self.add_chunks_calls += 1

    metadata_store = MetadataStoreSpy()
    vector_store = FakeVectorStore()
    service = IngestionService(
        chunker=FixedWindowChunker(chunk_size=32, chunk_overlap=4),
        embedding_client=FakeEmbeddingClient(),
        vector_store=cast(VectorStore, vector_store),
        metadata_store=cast(MetadataStore, metadata_store),
        document_storage=FakeDocumentStorage("memory", tmp_path / "documents"),
    )
    chunks = [
        ChunkRecord(
            chunk_id="",
            doc_id="doc-1",
            user_id="user-a",
            content="alpha",
            metadata={"source": "x.txt"},
        ),
        ChunkRecord(
            chunk_id="",
            doc_id="doc-1",
            user_id="user-a",
            content="beta",
            metadata={"source": "x.txt"},
        ),
    ]

    with pytest.raises(RuntimeError, match="Milvus returned a mismatched number of chunk ids"):
        service.store(chunks, [[1.0, 0.0, 0.0, 5.0], [0.0, 1.0, 0.0, 4.0]])

    assert vector_store.deleted_chunk_ids == [["101"]]
    assert metadata_store.add_chunks_calls == 0


def test_ingest_text_rolls_back_generated_ids_when_vector_store_returns_wrong_count(tmp_path: Path) -> None:
    class MismatchedVectorStore:
        def __init__(self) -> None:
            self.deleted_chunk_ids: list[list[str]] = []

        def add(self, chunks, vectors):
            del chunks, vectors
            return ["101"]

        def delete_chunks(self, chunk_ids):
            self.deleted_chunk_ids.append(list(chunk_ids))

    vector_store = MismatchedVectorStore()
    metadata_store = MetadataStore(tmp_path / "metadata.db")
    service = IngestionService(
        chunker=FixedWindowChunker(chunk_size=5, chunk_overlap=0),
        embedding_client=FakeEmbeddingClient(),
        vector_store=cast(VectorStore, vector_store),
        metadata_store=metadata_store,
        document_storage=FakeDocumentStorage("memory", tmp_path / "documents"),
    )

    with pytest.raises(RuntimeError, match="Milvus returned a mismatched number of chunk ids"):
        service.ingest_text(user_id="user-a", text="alpha beta", source="mismatch.txt")

    assert vector_store.deleted_chunk_ids == [["101"]]
    document = metadata_store.list_documents("user-a")[0]
    progress = metadata_store.list_ingestion_progress(doc_id=document.doc_id, user_id="user-a")
    assert [(row.step_name, row.status) for row in progress][-1] == ("vector_store", "failed")


def test_ingest_text_rolls_back_persisted_chunks_when_completion_progress_fails(
    monkeypatch, tmp_path: Path
) -> None:
    class TrackingVectorStore:
        def __init__(self) -> None:
            self.deleted_chunk_ids: list[list[str]] = []

        def add(self, chunks, vectors):
            del vectors
            return [str(index + 101) for index, _ in enumerate(chunks)]

        def delete_chunks(self, chunk_ids):
            self.deleted_chunk_ids.append(list(chunk_ids))

    vector_store = TrackingVectorStore()
    metadata_store = MetadataStore(tmp_path / "metadata.db")
    add_progress = metadata_store.add_ingestion_progress

    def fail_chunk_persistence_completion(records) -> None:
        record = records[0]
        if record.step_name == "chunk_persistence" and record.status == "completed":
            raise RuntimeError("progress persistence failed")
        add_progress(records)

    monkeypatch.setattr(metadata_store, "add_ingestion_progress", fail_chunk_persistence_completion)
    service = IngestionService(
        chunker=FixedWindowChunker(chunk_size=5, chunk_overlap=0),
        embedding_client=FakeEmbeddingClient(),
        vector_store=cast(VectorStore, vector_store),
        metadata_store=metadata_store,
        document_storage=FakeDocumentStorage("memory", tmp_path / "documents"),
    )

    with pytest.raises(RuntimeError, match="progress persistence failed"):
        service.ingest_text(user_id="user-a", text="alpha beta", source="progress-failure.txt")

    document = metadata_store.list_documents("user-a")[0]
    assert metadata_store.list_document_chunks(doc_id=document.doc_id, user_id="user-a") == []
    assert vector_store.deleted_chunk_ids == [["101", "102"]]


def test_ingest_text_rolls_back_vectors_when_vector_completion_progress_fails(
    monkeypatch, tmp_path: Path
) -> None:
    class TrackingVectorStore:
        def __init__(self) -> None:
            self.deleted_chunk_ids: list[list[str]] = []

        def add(self, chunks, vectors):
            del vectors
            return [str(index + 101) for index, _ in enumerate(chunks)]

        def delete_chunks(self, chunk_ids):
            self.deleted_chunk_ids.append(list(chunk_ids))

    vector_store = TrackingVectorStore()
    metadata_store = MetadataStore(tmp_path / "metadata.db")
    add_progress = metadata_store.add_ingestion_progress

    def fail_vector_store_completion(records) -> None:
        record = records[0]
        if record.step_name == "vector_store" and record.status == "completed":
            raise RuntimeError("vector progress persistence failed")
        add_progress(records)

    monkeypatch.setattr(metadata_store, "add_ingestion_progress", fail_vector_store_completion)
    service = IngestionService(
        chunker=FixedWindowChunker(chunk_size=5, chunk_overlap=0),
        embedding_client=FakeEmbeddingClient(),
        vector_store=cast(VectorStore, vector_store),
        metadata_store=metadata_store,
        document_storage=FakeDocumentStorage("memory", tmp_path / "documents"),
    )

    with pytest.raises(RuntimeError, match="vector progress persistence failed"):
        service.ingest_text(user_id="user-a", text="alpha beta", source="vector-progress-failure.txt")

    assert vector_store.deleted_chunk_ids == [["101", "102"]]


def test_ingest_text_continues_vector_rollback_when_chunk_metadata_rollback_fails(
    monkeypatch, tmp_path: Path
) -> None:
    class TrackingVectorStore:
        def __init__(self) -> None:
            self.deleted_chunk_ids: list[list[str]] = []

        def add(self, chunks, vectors):
            del vectors
            return [str(index + 101) for index, _ in enumerate(chunks)]

        def delete_chunks(self, chunk_ids):
            self.deleted_chunk_ids.append(list(chunk_ids))

    vector_store = TrackingVectorStore()
    metadata_store = MetadataStore(tmp_path / "metadata.db")
    add_progress = metadata_store.add_ingestion_progress

    def fail_chunk_persistence_completion(records) -> None:
        record = records[0]
        if record.step_name == "chunk_persistence" and record.status == "completed":
            raise RuntimeError("progress persistence failed")
        add_progress(records)

    def fail_metadata_rollback(chunk_ids) -> None:
        del chunk_ids
        raise RuntimeError("metadata rollback failed")

    monkeypatch.setattr(metadata_store, "add_ingestion_progress", fail_chunk_persistence_completion)
    monkeypatch.setattr(metadata_store, "delete_chunks", fail_metadata_rollback)
    service = IngestionService(
        chunker=FixedWindowChunker(chunk_size=5, chunk_overlap=0),
        embedding_client=FakeEmbeddingClient(),
        vector_store=cast(VectorStore, vector_store),
        metadata_store=metadata_store,
        document_storage=FakeDocumentStorage("memory", tmp_path / "documents"),
    )

    with pytest.raises(RuntimeError, match="progress persistence failed") as exc_info:
        service.ingest_text(user_id="user-a", text="alpha beta", source="rollback-failure.txt")

    assert vector_store.deleted_chunk_ids == [["101", "102"]]
    assert any("metadata rollback failed" in note for note in exc_info.value.__notes__)


def test_ingest_text_preserves_operation_error_when_failed_progress_write_fails(
    monkeypatch, tmp_path: Path
) -> None:
    class MismatchedVectorStore:
        def __init__(self) -> None:
            self.deleted_chunk_ids: list[list[str]] = []

        def add(self, chunks, vectors):
            del chunks, vectors
            return ["101"]

        def delete_chunks(self, chunk_ids):
            self.deleted_chunk_ids.append(list(chunk_ids))

    vector_store = MismatchedVectorStore()
    metadata_store = MetadataStore(tmp_path / "metadata.db")
    add_progress = metadata_store.add_ingestion_progress

    def fail_failed_progress_write(records) -> None:
        record = records[0]
        if record.step_name == "vector_store" and record.status == "failed":
            raise RuntimeError("failed progress persistence failed")
        add_progress(records)

    monkeypatch.setattr(metadata_store, "add_ingestion_progress", fail_failed_progress_write)
    service = IngestionService(
        chunker=FixedWindowChunker(chunk_size=5, chunk_overlap=0),
        embedding_client=FakeEmbeddingClient(),
        vector_store=cast(VectorStore, vector_store),
        metadata_store=metadata_store,
        document_storage=FakeDocumentStorage("memory", tmp_path / "documents"),
    )

    with pytest.raises(RuntimeError, match="Milvus returned a mismatched number of chunk ids") as exc_info:
        service.ingest_text(user_id="user-a", text="alpha beta", source="failed-progress.txt")

    assert vector_store.deleted_chunk_ids == [["101"]]
    assert any("failed progress persistence failed" in note for note in exc_info.value.__notes__)


def test_store_preserves_metadata_error_when_vector_cleanup_fails(monkeypatch, tmp_path: Path) -> None:
    class FailingCleanupVectorStore:
        def add(self, chunks, vectors):
            del chunks, vectors
            return ["101"]

        def delete_chunks(self, chunk_ids):
            del chunk_ids
            raise RuntimeError("vector rollback failed")

    metadata_store = MetadataStore(tmp_path / "metadata.db")

    def fail_chunk_write(chunks) -> None:
        del chunks
        raise RuntimeError("metadata write failed")

    monkeypatch.setattr(metadata_store, "add_chunks", fail_chunk_write)
    service = IngestionService(
        chunker=FixedWindowChunker(chunk_size=5, chunk_overlap=0),
        embedding_client=FakeEmbeddingClient(),
        vector_store=cast(VectorStore, FailingCleanupVectorStore()),
        metadata_store=metadata_store,
        document_storage=FakeDocumentStorage("memory", tmp_path / "documents"),
    )
    chunks = [
        ChunkRecord(
            chunk_id="",
            doc_id="doc-1",
            user_id="user-a",
            content="alpha",
            metadata={"source": "metadata-failure.txt"},
        )
    ]

    with pytest.raises(RuntimeError, match="metadata write failed") as exc_info:
        service.store(chunks, [[1.0]])

    assert any("vector rollback failed" in note for note in exc_info.value.__notes__)


def test_store_preserves_id_mismatch_error_when_vector_cleanup_fails(tmp_path: Path) -> None:
    class FailingCleanupVectorStore:
        def add(self, chunks, vectors):
            del chunks, vectors
            return ["101"]

        def delete_chunks(self, chunk_ids):
            del chunk_ids
            raise RuntimeError("vector rollback failed")

    service = IngestionService(
        chunker=FixedWindowChunker(chunk_size=5, chunk_overlap=0),
        embedding_client=FakeEmbeddingClient(),
        vector_store=cast(VectorStore, FailingCleanupVectorStore()),
        metadata_store=MetadataStore(tmp_path / "metadata.db"),
        document_storage=FakeDocumentStorage("memory", tmp_path / "documents"),
    )
    chunks = [
        ChunkRecord(
            chunk_id="",
            doc_id="doc-1",
            user_id="user-a",
            content=content,
            metadata={"source": "mismatch-failure.txt"},
        )
        for content in ("alpha", "beta")
    ]

    with pytest.raises(RuntimeError, match="Milvus returned a mismatched number of chunk ids") as exc_info:
        service.store(chunks, [[1.0], [2.0]])

    assert any("vector rollback failed" in note for note in exc_info.value.__notes__)


def test_delete_document_leaves_metadata_intact_when_milvus_delete_fails_and_allows_retry(
    monkeypatch, tmp_path: Path
) -> None:
    rig = create_test_rig(tmp_path, storage_mode="local")
    ingested = rig.core.ingest_text(user=USER_A, text="alpha retry cleanup", source="retry.txt")
    original_delete_document = rig.core.vector_store.delete_document
    attempts = {"count": 0}

    def flaky_delete_document(doc_id: str) -> None:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("milvus delete failed")
        original_delete_document(doc_id)

    monkeypatch.setattr(rig.core.vector_store, "delete_document", flaky_delete_document)

    with pytest.raises(RuntimeError, match="milvus delete failed"):
        rig.core.delete_document(ingested.doc_id, user=USER_A)

    assert rig.core.get_document(ingested.doc_id, user=USER_A) is not None
    assert rig.core.list_document_chunks(ingested.doc_id, user=USER_A)

    assert rig.core.delete_document(ingested.doc_id, user=USER_A) is True
    assert rig.core.get_document(ingested.doc_id, user=USER_A) is None


def test_delete_document_leaves_metadata_intact_when_asset_soft_delete_fails(
    monkeypatch, tmp_path: Path
) -> None:
    rig = create_test_rig(tmp_path, storage_mode="local")
    ingested = rig.core.ingest_text(user=USER_A, text="alpha retry cleanup", source="retry.txt")

    def fail_asset_delete(document) -> None:
        del document
        raise RuntimeError("dms delete failed")

    monkeypatch.setattr(rig.core.document_storage, "delete", fail_asset_delete)

    with pytest.raises(RuntimeError, match="dms delete failed"):
        rig.core.delete_document(ingested.doc_id, user=USER_A)

    assert rig.core.get_document(ingested.doc_id, user=USER_A) is not None
    assert rig.core.list_document_chunks(ingested.doc_id, user=USER_A)


def test_embedding_requests_are_batched_for_chunk_ingestion(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)
    text = "alpha one. beta two. gamma three. delta four. epsilon five."

    result = rig.core.ingest_text(user=USER_A, text=text, source="batch.txt")

    assert result.chunk_count > 1
    assert len(rig.embedding_client.calls) == 1
    assert len(rig.embedding_client.calls[0]) == result.chunk_count
