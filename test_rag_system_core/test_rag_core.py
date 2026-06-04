from __future__ import annotations

from io import BytesIO
from pathlib import Path

from sqlalchemy import inspect

from rag_system_core import RAGCore


class FakeEmbeddingClient:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        vectors: list[list[float]] = []
        for text in texts:
            normalized = text.lower()
            vectors.append(
                [
                    float(normalized.count("alpha")),
                    float(normalized.count("beta")),
                    float(normalized.count("gamma")),
                    float(len(normalized)),
                ]
            )
        return vectors


class FakeGenerationClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        context_block = prompt.split("[Retrieved Context]\n", 1)[1]
        context, question = context_block.rsplit("\n\n[User Query]\n", 1)
        first_context_line = context.strip().splitlines()[0]
        return f"ANSWER::{question.strip()}::{first_context_line}"


def create_core(tmp_path: Path, *, storage_mode: str = "memory") -> RAGCore:
    return RAGCore(
        embedding_client=FakeEmbeddingClient(),
        generation_client=FakeGenerationClient(),
        metadata_path=tmp_path / "metadata.db",
        document_storage_dir=tmp_path / "documents",
        storage_mode=storage_mode,
        chunk_size=32,
        chunk_overlap=4,
    )


def test_ingest_text_uses_token_as_user_scope(tmp_path: Path) -> None:
    core = create_core(tmp_path)

    result = core.ingest_text(token="token-a", text="alpha beta gamma", source="note.txt")

    assert result.user_id == "token-a"
    assert result.source == "note.txt"
    assert result.doc_id
    assert result.created_at
    assert result.chunk_count == 1
    assert [doc.doc_id for doc in core.list_documents(token="token-a")] == [result.doc_id]


def test_ingest_text_without_token_uses_single_user_scope(tmp_path: Path) -> None:
    core = create_core(tmp_path)

    result = core.ingest_text(text="alpha solo text", source="solo.txt")

    assert result.user_id == "single-user"
    assert [doc.doc_id for doc in core.list_documents()] == [result.doc_id]


def test_ingest_text_stores_string_input_as_managed_asset(tmp_path: Path) -> None:
    core = create_core(tmp_path, storage_mode="local")

    result = core.ingest_text(token="token-a", text="alpha asset text", source="asset.txt")

    stored = core.get_document(result.doc_id, token="token-a")
    assert stored is not None
    assert stored.storage_path is not None
    stored_path = Path(stored.storage_path)
    assert stored_path.exists()
    assert stored_path.read_text(encoding="utf-8") == "alpha asset text"


def test_ingest_text_memory_storage_uses_logical_asset_path(tmp_path: Path) -> None:
    core = create_core(tmp_path, storage_mode="memory")

    result = core.ingest_text(token="token-a", text="alpha memory asset", source="memory.txt")

    stored = core.get_document(result.doc_id, token="token-a")
    assert stored is not None
    assert stored.storage_path is not None
    assert stored.storage_path.startswith("memory://")
    assert core.document_storage.load(stored) == "alpha memory asset"


def test_ingest_file_stream_copies_input_stream_into_managed_storage(tmp_path: Path) -> None:
    core = create_core(tmp_path, storage_mode="local")
    stream = BytesIO(b"alpha original file")

    result = core.ingest_file_stream(token="token-a", file_stream=stream, source="source.txt")

    stored = core.get_document(result.doc_id, token="token-a")
    assert stored is not None
    assert stored.storage_path is not None
    stored_path = Path(stored.storage_path)
    assert stored_path.exists()
    assert stored_path.name != "source.txt"
    assert stored_path.read_text(encoding="utf-8") == "alpha original file"


def test_ingest_file_stream_requires_explicit_source(tmp_path: Path) -> None:
    core = create_core(tmp_path, storage_mode="local")

    try:
        core.ingest_file_stream(token="token-a", file_stream=BytesIO(b"alpha"))
    except ValueError as exc:
        assert str(exc) == "source is required for stream ingestion"
    else:
        raise AssertionError("Expected ValueError when source is omitted for stream ingestion")


def test_ingest_file_path_reads_existing_file_via_dedicated_api(tmp_path: Path) -> None:
    core = create_core(tmp_path, storage_mode="local")
    source_file = tmp_path / "existing.txt"
    source_file.write_text("alpha from path", encoding="utf-8")

    result = core.ingest_file_path(token="token-a", file_path=source_file)

    stored = core.get_document(result.doc_id, token="token-a")
    assert stored is not None
    assert stored.source == "existing.txt"
    assert stored.storage_path is not None
    assert Path(stored.storage_path).read_text(encoding="utf-8") == "alpha from path"


def test_ingestion_service_exposes_separate_stream_and_path_methods(tmp_path: Path) -> None:
    core = create_core(tmp_path)

    assert hasattr(core.ingestor, "ingest_file_stream")
    assert hasattr(core.ingestor, "ingest_file_path")
    assert not hasattr(core.ingestor, "ingest_file")


def test_document_storage_exposes_text_stream_and_path_methods(tmp_path: Path) -> None:
    core = create_core(tmp_path)

    assert hasattr(core.document_storage, "store_text")
    assert hasattr(core.document_storage, "store_file_stream")
    assert hasattr(core.document_storage, "store_file_path")
    assert not hasattr(core.document_storage, "store_bytes")


def test_ragcore_exposes_explicit_stream_and_path_ingest_methods(tmp_path: Path) -> None:
    core = create_core(tmp_path)

    assert hasattr(core, "ingest_file_stream")
    assert hasattr(core, "ingest_file_path")
    assert not hasattr(core, "ingest_file")


def test_query_filters_results_by_token_derived_user_id(tmp_path: Path) -> None:
    core = create_core(tmp_path)
    core.ingest_text(token="token-a", text="alpha document only for token a", source="a.txt")
    core.ingest_text(token="token-b", text="beta document only for token b", source="b.txt")

    response = core.query(token="token-a", question="Where is alpha?", top_k=3)

    assert response.answer.startswith("ANSWER::Where is alpha?::")
    assert "alpha document only for token a" in response.answer
    assert all(chunk.user_id == "token-a" for chunk in response.context_chunks)
    assert all("token b" not in chunk.content for chunk in response.context_chunks)


def test_query_prompt_includes_system_query_and_context(tmp_path: Path) -> None:
    core = create_core(tmp_path)
    core.ingest_text(token="token-a", text="alpha context block", source="a.txt")

    response = core.query(token="token-a", question="Summarize alpha", top_k=1)

    prompt = core.generator.last_prompt
    assert response.answer.startswith("ANSWER::Summarize alpha::")
    assert "[System Prompt]" in prompt
    assert "[Retrieved Context]" in prompt
    assert "alpha context block" in prompt
    assert "[User Query]\nSummarize alpha" in prompt


def test_metadata_store_uses_sqlalchemy_orm_models_and_chunk_table(tmp_path: Path) -> None:
    core = create_core(tmp_path)
    result = core.ingest_text(token="token-a", text="alpha sqlite", source="sqlite.txt")
    stored = core.get_document(result.doc_id, token="token-a")
    assert stored is not None

    assert hasattr(core.metadata_store, "engine")
    assert hasattr(core.metadata_store, "DocumentModel")
    assert hasattr(core.metadata_store, "ChunkModel")

    inspector = inspect(core.metadata_store.engine)
    assert "documents" in inspector.get_table_names()
    assert "chunks" in inspector.get_table_names()

    with core.metadata_store.session() as session:
        row = session.get(core.metadata_store.DocumentModel, result.doc_id)

    assert row is not None
    assert row.doc_id == result.doc_id
    assert row.user_id == "token-a"
    assert row.source == "sqlite.txt"
    assert row.storage_path == stored.storage_path


def test_chunk_rows_are_persisted_and_rehydrated_across_restarts(tmp_path: Path) -> None:
    core = create_core(tmp_path, storage_mode="local")
    result = core.ingest_text(
        token="token-a",
        text="alpha one. beta two. gamma three. delta four. epsilon five.",
        source="persist.txt",
    )

    with core.metadata_store.session() as session:
        chunk_rows = (
            session.query(core.metadata_store.ChunkModel)
            .filter_by(doc_id=result.doc_id)
            .order_by(core.metadata_store.ChunkModel.chunk_index)
            .all()
        )

    assert len(chunk_rows) == result.chunk_count
    assert all(row.user_id == "token-a" for row in chunk_rows)
    assert all(row.embedding for row in chunk_rows)
    assert all(row.content for row in chunk_rows)

    restarted = create_core(tmp_path, storage_mode="local")
    response = restarted.query(token="token-a", question="Where is alpha?", top_k=3)

    assert response.context_chunks
    assert any("alpha" in chunk.content.lower() for chunk in response.context_chunks)


def test_list_document_chunks_returns_only_requested_document_chunks(tmp_path: Path) -> None:
    core = create_core(tmp_path)
    first = core.ingest_text(
        token="token-a",
        text="alpha one. beta two. gamma three. delta four. epsilon five.",
        source="first.txt",
    )
    second = core.ingest_text(
        token="token-a",
        text="alpha separate document for second result set only.",
        source="second.txt",
    )

    chunks = core.list_document_chunks(first.doc_id, token="token-a")

    assert len(chunks) == first.chunk_count
    assert all(chunk.doc_id == first.doc_id for chunk in chunks)
    assert all(chunk.doc_id != second.doc_id for chunk in chunks)


def test_get_document_is_limited_to_current_token_scope(tmp_path: Path) -> None:
    core = create_core(tmp_path)
    token_a_result = core.ingest_text(token="token-a", text="alpha scoped document", source="a.txt")
    core.ingest_text(token="token-b", text="beta scoped document", source="b.txt")

    visible = core.get_document(token_a_result.doc_id, token="token-a")
    hidden = core.get_document(token_a_result.doc_id, token="token-b")

    assert visible is not None
    assert visible.doc_id == token_a_result.doc_id
    assert hidden is None


def test_delete_document_removes_metadata_chunks_asset_and_query_visibility(tmp_path: Path) -> None:
    core = create_core(tmp_path, storage_mode="local")
    target = core.ingest_text(
        token="token-a",
        text="alpha one. beta two. gamma three. delta four. epsilon five.",
        source="target.txt",
    )
    survivor = core.ingest_text(
        token="token-a",
        text="beta survivor document only.",
        source="survivor.txt",
    )
    stored = core.get_document(target.doc_id, token="token-a")
    assert stored is not None
    assert stored.storage_path is not None
    stored_path = Path(stored.storage_path)
    assert stored_path.exists()

    deleted = core.delete_document(target.doc_id, token="token-a")

    assert deleted is True
    assert core.get_document(target.doc_id, token="token-a") is None
    assert core.list_document_chunks(target.doc_id, token="token-a") == []
    assert not stored_path.exists()
    assert [doc.doc_id for doc in core.list_documents(token="token-a")] == [survivor.doc_id]

    response = core.query(token="token-a", question="Where is alpha?", top_k=5)
    assert all(chunk.doc_id != target.doc_id for chunk in response.context_chunks)


def test_metadata_persists_across_restarts(tmp_path: Path) -> None:
    core = create_core(tmp_path, storage_mode="local")
    first = core.ingest_text(token="token-a", text="alpha persists", source="persist.txt")

    restarted = create_core(tmp_path, storage_mode="local")

    documents = restarted.list_documents(token="token-a")
    assert [doc.doc_id for doc in documents] == [first.doc_id]
    stored = restarted.get_document(first.doc_id, token="token-a")
    assert stored is not None
    assert stored.user_id == "token-a"
    assert stored.source == "persist.txt"
    assert stored.storage_path is not None


def test_embedding_requests_are_batched_for_chunk_ingestion(tmp_path: Path) -> None:
    core = create_core(tmp_path)
    text = "alpha one. beta two. gamma three. delta four. epsilon five."

    result = core.ingest_text(token="token-a", text=text, source="batch.txt")

    assert result.chunk_count > 1
    assert len(core.embedding_client.calls) == 1
    assert len(core.embedding_client.calls[0]) == result.chunk_count


def test_blank_token_falls_back_to_single_user_scope(tmp_path: Path) -> None:
    core = create_core(tmp_path)

    result = core.ingest_text(token="   ", text="alpha", source="x.txt")

    assert result.user_id == "single-user"
    assert [doc.doc_id for doc in core.list_documents()] == [result.doc_id]
