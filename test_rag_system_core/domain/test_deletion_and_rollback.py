from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

import rag_system_core.core as core_module

from test_rag_system_core.support import create_test_rig, FakeEmbeddingClient


def test_delete_document_removes_metadata_chunks_asset_and_query_visibility(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path, storage_mode="local")
    target = rig.core.ingest_text(
        token="token-a",
        text="alpha one. beta two. gamma three. delta four. epsilon five.",
        source="target.txt",
    )
    survivor = rig.core.ingest_text(
        token="token-a",
        text="beta survivor document only.",
        source="survivor.txt",
    )
    stored = rig.core.get_document(target.doc_id, token="token-a")
    assert stored is not None
    assert stored.storage_path is not None
    stored_path = Path(stored.storage_path)
    assert stored_path.exists()
    assert rig.core.list_ingestion_progress(target.doc_id, token="token-a")

    deleted = rig.core.delete_document(target.doc_id, token="token-a")

    assert deleted is True
    assert rig.core.get_document(target.doc_id, token="token-a") is None
    assert rig.core.list_document_chunks(target.doc_id, token="token-a") == []
    assert rig.core.list_ingestion_progress(target.doc_id, token="token-a") == []
    assert not stored_path.exists()
    assert [doc.doc_id for doc in rig.core.list_documents(token="token-a")] == [survivor.doc_id]

    response = rig.core.query(token="token-a", question="Where is alpha?", top_k=5)
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
    service = core_module.IngestionService(
        chunker=core_module.FixedWindowChunker(chunk_size=32, chunk_overlap=4),
        embedding_client=FakeEmbeddingClient(),
        vector_store=cast(core_module.VectorStore, vector_store),
        metadata_store=cast(core_module.MetadataStore, metadata_store),
        document_storage=core_module.DocumentStorage("memory", tmp_path / "documents"),
    )
    chunks = [
        core_module.ChunkRecord(
            chunk_id="",
            doc_id="doc-1",
            user_id="token-a",
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
    service = core_module.IngestionService(
        chunker=core_module.FixedWindowChunker(chunk_size=32, chunk_overlap=4),
        embedding_client=FakeEmbeddingClient(),
        vector_store=cast(core_module.VectorStore, vector_store),
        metadata_store=cast(core_module.MetadataStore, metadata_store),
        document_storage=core_module.DocumentStorage("memory", tmp_path / "documents"),
    )
    chunks = [
        core_module.ChunkRecord(
            chunk_id="",
            doc_id="doc-1",
            user_id="token-a",
            content="alpha",
            metadata={"source": "x.txt"},
        ),
        core_module.ChunkRecord(
            chunk_id="",
            doc_id="doc-1",
            user_id="token-a",
            content="beta",
            metadata={"source": "x.txt"},
        ),
    ]

    with pytest.raises(RuntimeError, match="Milvus returned a mismatched number of chunk ids"):
        service.store(chunks, [[1.0, 0.0, 0.0, 5.0], [0.0, 1.0, 0.0, 4.0]])

    assert vector_store.deleted_chunk_ids == [["101"]]
    assert metadata_store.add_chunks_calls == 0


def test_delete_document_leaves_metadata_intact_when_milvus_delete_fails_and_allows_retry(
    monkeypatch, tmp_path: Path
) -> None:
    rig = create_test_rig(tmp_path, storage_mode="local")
    ingested = rig.core.ingest_text(token="token-a", text="alpha retry cleanup", source="retry.txt")
    original_delete_document = rig.core.vector_store.delete_document
    attempts = {"count": 0}

    def flaky_delete_document(doc_id: str) -> None:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("milvus delete failed")
        original_delete_document(doc_id)

    monkeypatch.setattr(rig.core.vector_store, "delete_document", flaky_delete_document)

    with pytest.raises(RuntimeError, match="milvus delete failed"):
        rig.core.delete_document(ingested.doc_id, token="token-a")

    assert rig.core.get_document(ingested.doc_id, token="token-a") is not None
    assert rig.core.list_document_chunks(ingested.doc_id, token="token-a")

    assert rig.core.delete_document(ingested.doc_id, token="token-a") is True
    assert rig.core.get_document(ingested.doc_id, token="token-a") is None


def test_embedding_requests_are_batched_for_chunk_ingestion(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)
    text = "alpha one. beta two. gamma three. delta four. epsilon five."

    result = rig.core.ingest_text(token="token-a", text=text, source="batch.txt")

    assert result.chunk_count > 1
    assert len(rig.embedding_client.calls) == 1
    assert len(rig.embedding_client.calls[0]) == result.chunk_count
