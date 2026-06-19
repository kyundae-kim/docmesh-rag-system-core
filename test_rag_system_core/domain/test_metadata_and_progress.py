from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect

import rag_system_core.core as core_module

from test_rag_system_core.support import create_test_rig


def test_metadata_store_uses_sqlalchemy_orm_models_and_chunk_table(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)
    result = rig.core.ingest_text(token="token-a", text="alpha sqlite", source="sqlite.txt")
    stored = rig.core.get_document(result.doc_id, token="token-a")
    assert stored is not None

    assert hasattr(rig.core.metadata_store, "engine")
    assert hasattr(rig.core.metadata_store, "DocumentModel")
    assert hasattr(rig.core.metadata_store, "ChunkModel")
    assert hasattr(rig.core.metadata_store, "IngestionProgressModel")

    inspector = inspect(rig.core.metadata_store.engine)
    assert "documents" in inspector.get_table_names()
    assert "chunks" in inspector.get_table_names()
    assert "ingestion_progress" in inspector.get_table_names()
    chunk_columns = {column["name"] for column in inspector.get_columns("chunks")}
    assert "embedding" not in chunk_columns

    with rig.core.metadata_store.session() as session:
        row = session.get(rig.core.metadata_store.DocumentModel, result.doc_id)

    assert row is not None
    assert row.doc_id == result.doc_id
    assert row.user_id == "token-a"
    assert row.source == "sqlite.txt"
    assert row.storage_path == stored.storage_path


def test_ingest_text_persists_milvus_generated_chunk_ids_to_metadata(tmp_path: Path) -> None:
    generated_ids = [101, 102]

    class FakeMilvusClient:
        inserted_payload: list[dict[str, object]] = []

        def __init__(self, *, uri: str, timeout: float) -> None:
            del uri, timeout
            self._has_collection = False

        def has_collection(self, collection_name: str) -> bool:
            del collection_name
            return self._has_collection

        def create_collection(self, **kwargs) -> None:
            del kwargs
            self._has_collection = True

        def insert(self, collection_name: str, data: list[dict[str, object]], timeout: float):
            del collection_name, timeout
            FakeMilvusClient.inserted_payload = data
            return {"insert_count": len(data), "ids": generated_ids}

        def search(self, *args, **kwargs):
            del args, kwargs
            return [[]]

        def delete(self, *args, **kwargs) -> None:
            del args, kwargs

    original_client = core_module.vector_store_module.MilvusClient
    core_module.vector_store_module.MilvusClient = FakeMilvusClient
    try:
        rig = create_test_rig(tmp_path)
        result = rig.core.ingest_text(
            token="token-a",
            text="alpha one. beta two. gamma three. delta four. epsilon five.",
            source="milvus-ids.txt",
        )
    finally:
        core_module.vector_store_module.MilvusClient = original_client

    assert result.chunk_count == 2
    assert all("chunk_id" not in payload for payload in FakeMilvusClient.inserted_payload)

    with rig.core.metadata_store.session() as session:
        rows = (
            session.query(rig.core.metadata_store.ChunkModel)
            .filter_by(doc_id=result.doc_id)
            .order_by(rig.core.metadata_store.ChunkModel.chunk_index)
            .all()
        )

    assert [row.chunk_id for row in rows] == [str(value) for value in generated_ids]


def test_ingestion_progress_rows_are_persisted_in_pipeline_order(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)

    result = rig.core.ingest_text(
        token="token-a",
        text="alpha one. beta two. gamma three. delta four. epsilon five.",
        source="pipeline.txt",
    )

    progress_rows = rig.core.list_ingestion_progress(result.doc_id, token="token-a", job_id=result.job_id)
    completed_rows = [row for row in progress_rows if row.status == "completed"]

    assert [row.step_name for row in completed_rows] == [
        "load",
        "preprocess",
        "chunking",
        "embedding",
        "vector_store",
        "chunk_persistence",
    ]
    assert all(row.doc_id == result.doc_id for row in progress_rows)
    assert all(row.user_id == "token-a" for row in progress_rows)
    assert len({row.job_id for row in progress_rows}) == 1


def test_ingestion_progress_records_running_and_completed_statuses_per_job(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)

    result = rig.core.ingest_text(
        token="token-a",
        text="alpha progress state tracking",
        source="stateful.txt",
    )

    progress_rows = rig.core.list_ingestion_progress(result.doc_id, token="token-a")

    assert any(row.status == "running" for row in progress_rows)
    assert any(row.status == "completed" for row in progress_rows)
    assert {row.job_id for row in progress_rows}


def test_ingestion_progress_records_failed_step_when_ingest_errors(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)

    try:
        rig.core.ingest_text(token="token-a", text="   ", source="blank.txt")
    except ValueError as exc:
        assert str(exc) == "Document must contain non-empty text"
    else:
        raise AssertionError("Expected ValueError for blank document ingestion")

    failed_docs = rig.core.list_documents(token="token-a")
    assert len(failed_docs) == 1
    failed_doc = failed_docs[0]
    progress_rows = rig.core.list_ingestion_progress(failed_doc.doc_id, token="token-a")
    terminal_rows = [row for row in progress_rows if row.status != "running"]

    assert [row.step_name for row in terminal_rows] == ["load", "preprocess", "chunking"]
    assert [row.status for row in terminal_rows] == ["completed", "completed", "failed"]
    assert len({row.job_id for row in progress_rows}) == 1


def test_ingestion_progress_can_be_grouped_by_job_id_for_same_document(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)
    first = rig.core.ingest_text(token="token-a", text="alpha first ingest", source="same.txt")
    second = rig.core.ingest_text(token="token-a", text="alpha second ingest", source="same.txt")

    first_rows = rig.core.list_ingestion_progress(first.doc_id, token="token-a", job_id=first.job_id)
    second_rows = rig.core.list_ingestion_progress(second.doc_id, token="token-a", job_id=second.job_id)

    assert first.job_id != second.job_id
    assert first_rows
    assert second_rows
    assert all(row.job_id == first.job_id for row in first_rows)
    assert all(row.job_id == second.job_id for row in second_rows)


def test_ingestion_progress_is_limited_to_current_token_scope(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)
    token_a_result = rig.core.ingest_text(token="token-a", text="alpha scoped pipeline", source="a.txt")
    rig.core.ingest_text(token="token-b", text="beta scoped pipeline", source="b.txt")

    visible = rig.core.list_ingestion_progress(token_a_result.doc_id, token="token-a")
    hidden = rig.core.list_ingestion_progress(token_a_result.doc_id, token="token-b")

    assert visible
    assert all(row.doc_id == token_a_result.doc_id for row in visible)
    assert hidden == []


def test_chunk_rows_are_persisted_and_rehydrated_across_restarts(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path, storage_mode="local")
    result = rig.core.ingest_text(
        token="token-a",
        text="alpha one. beta two. gamma three. delta four. epsilon five.",
        source="persist.txt",
    )

    with rig.core.metadata_store.session() as session:
        chunk_rows = (
            session.query(rig.core.metadata_store.ChunkModel)
            .filter_by(doc_id=result.doc_id)
            .order_by(rig.core.metadata_store.ChunkModel.chunk_index)
            .all()
        )

    assert len(chunk_rows) == result.chunk_count
    assert all(row.user_id == "token-a" for row in chunk_rows)
    assert all(row.chunk_id for row in chunk_rows)
    assert all(row.content for row in chunk_rows)

    restarted = create_test_rig(tmp_path, storage_mode="local")
    response = restarted.core.query(token="token-a", question="Where is alpha?", top_k=3)

    assert response.context_chunks
    assert any("alpha" in chunk.content.lower() for chunk in response.context_chunks)


def test_list_document_chunks_returns_only_requested_document_chunks(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)
    first = rig.core.ingest_text(
        token="token-a",
        text="alpha one. beta two. gamma three. delta four. epsilon five.",
        source="first.txt",
    )
    second = rig.core.ingest_text(
        token="token-a",
        text="alpha separate document for second result set only.",
        source="second.txt",
    )

    chunks = rig.core.list_document_chunks(first.doc_id, token="token-a")

    assert len(chunks) == first.chunk_count
    assert all(chunk.doc_id == first.doc_id for chunk in chunks)
    assert all(chunk.doc_id != second.doc_id for chunk in chunks)


def test_get_document_is_limited_to_current_token_scope(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)
    token_a_result = rig.core.ingest_text(token="token-a", text="alpha scoped document", source="a.txt")
    rig.core.ingest_text(token="token-b", text="beta scoped document", source="b.txt")

    visible = rig.core.get_document(token_a_result.doc_id, token="token-a")
    hidden = rig.core.get_document(token_a_result.doc_id, token="token-b")

    assert visible is not None
    assert visible.doc_id == token_a_result.doc_id
    assert hidden is None


def test_metadata_persists_across_restarts(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path, storage_mode="local")
    first = rig.core.ingest_text(token="token-a", text="alpha persists", source="persist.txt")

    restarted = create_test_rig(tmp_path, storage_mode="local")

    documents = restarted.core.list_documents(token="token-a")
    assert [doc.doc_id for doc in documents] == [first.doc_id]
    stored = restarted.core.get_document(first.doc_id, token="token-a")
    assert stored is not None
    assert stored.user_id == "token-a"
    assert stored.source == "persist.txt"
    assert stored.storage_path is not None
