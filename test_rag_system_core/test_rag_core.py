from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import cast

from sqlalchemy import inspect

import rag_system_core.core as core_module
from rag_system_core import OllamaEmbeddingClient, RAGCore


def test_ollama_embedding_client_requires_model_when_not_configured(monkeypatch) -> None:
    monkeypatch.delenv("OLLAMA_EMBED_MODEL", raising=False)

    try:
        OllamaEmbeddingClient(base_url="http://ollama", timeout=7.0)
    except ValueError as exc:
        assert str(exc) == "Ollama embed model must be provided either as 'model' or OLLAMA_EMBED_MODEL"
    else:
        raise AssertionError("Expected ValueError when no Ollama embed model is configured")


def test_ollama_embedding_client_reads_configuration_from_environment(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, *, host: str, timeout: float) -> None:
            captured["host"] = host
            captured["timeout"] = timeout

        def embed(self, *, model: str, input: list[str]):
            captured["model"] = model
            captured["input"] = input
            return {"embeddings": [[1.0, 0.0, 0.5]]}

    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama")
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "bge-m3")
    monkeypatch.setenv("OLLAMA_TIMEOUT", "12.5")

    original_client = core_module.ollama.Client
    core_module.ollama.Client = FakeClient
    try:
        client = OllamaEmbeddingClient()
        vectors = client.embed(["alpha"])
    finally:
        core_module.ollama.Client = original_client

    assert vectors == [[1.0, 0.0, 0.5]]
    assert captured == {
        "host": "http://ollama",
        "timeout": 12.5,
        "model": "bge-m3",
        "input": ["alpha"],
    }


def test_rag_core_reads_milvus_configuration_from_environment(monkeypatch, tmp_path: Path) -> None:
    milvus_uri = tmp_path / "configured-milvus.db"
    monkeypatch.setenv("MILVUS_URI", str(milvus_uri))
    monkeypatch.setenv("MILVUS_COLLECTION_NAME", "configured_chunks")
    monkeypatch.setenv("MILVUS_TIMEOUT", "9.5")

    core = RAGCore(
        embedding_client=FakeEmbeddingClient(),
        generation_client=FakeGenerationClient(),
        metadata_path=tmp_path / "metadata.db",
        document_storage_dir=tmp_path / "documents",
        storage_mode="local",
    )
    ingested = core.ingest_text(token="token-a", text="alpha beta gamma", source="configured.txt")

    assert ingested.chunk_count == 1
    assert core.vector_store.uri == str(milvus_uri)
    assert core.vector_store.collection_name == "configured_chunks"
    assert core.vector_store.timeout == 9.5
    assert milvus_uri.exists()

    restarted = RAGCore(
        embedding_client=FakeEmbeddingClient(),
        generation_client=FakeGenerationClient(),
        metadata_path=tmp_path / "metadata.db",
        document_storage_dir=tmp_path / "documents",
        storage_mode="local",
    )
    response = restarted.query(token="token-a", question="Where is alpha?", top_k=3)

    assert response.context_chunks
    assert any(chunk.doc_id == ingested.doc_id for chunk in response.context_chunks)


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


def test_ollama_embedding_client_uses_ollama_package_client() -> None:
    captured: dict[str, object] = {}

    class FakeClient:
        def __init__(self, *, host: str, timeout: float) -> None:
            captured["host"] = host
            captured["timeout"] = timeout

        def embed(self, *, model: str, input: list[str]):
            captured["model"] = model
            captured["input"] = input
            return {"embeddings": [[1.0, 0.0, 0.5], [0.0, 1.0, 0.5]]}

    original_client = core_module.ollama.Client
    core_module.ollama.Client = FakeClient
    try:
        client = OllamaEmbeddingClient(model="bge-m3", base_url="http://ollama", timeout=7.0)
        vectors = client.embed(["alpha", "beta"])
    finally:
        core_module.ollama.Client = original_client

    assert vectors == [[1.0, 0.0, 0.5], [0.0, 1.0, 0.5]]
    assert captured == {
        "host": "http://ollama",
        "timeout": 7.0,
        "model": "bge-m3",
        "input": ["alpha", "beta"],
    }


def test_ollama_embedding_client_wraps_ollama_transport_errors() -> None:
    class FakeClient:
        def __init__(self, *, host: str, timeout: float) -> None:
            del host, timeout

        def embed(self, *, model: str, input: list[str]):
            del model, input
            raise ConnectionError("boom")

    original_client = core_module.ollama.Client
    core_module.ollama.Client = FakeClient
    try:
        client = OllamaEmbeddingClient(model="bge-m3", base_url="http://ollama", timeout=7.0)
        try:
            client.embed(["alpha"])
        except RuntimeError as exc:
            assert str(exc) == "Failed to fetch embeddings from Ollama"
            assert isinstance(exc.__cause__, ConnectionError)
        else:
            raise AssertionError("Expected RuntimeError when Ollama embed call fails")
    finally:
        core_module.ollama.Client = original_client


def test_ollama_embedding_client_rejects_malformed_embeddings_response() -> None:
    class FakeClient:
        def __init__(self, *, host: str, timeout: float) -> None:
            del host, timeout

        def embed(self, *, model: str, input: list[str]):
            del model, input
            return {}

    original_client = core_module.ollama.Client
    core_module.ollama.Client = FakeClient
    try:
        client = OllamaEmbeddingClient(model="bge-m3", base_url="http://ollama", timeout=7.0)
        try:
            client.embed(["alpha"])
        except RuntimeError as exc:
            assert str(exc) == "Ollama returned a malformed embeddings response"
            assert isinstance(exc.__cause__, KeyError)
        else:
            raise AssertionError("Expected RuntimeError for malformed Ollama embeddings response")
    finally:
        core_module.ollama.Client = original_client


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
    assert hasattr(core.metadata_store, "IngestionProgressModel")

    inspector = inspect(core.metadata_store.engine)
    assert "documents" in inspector.get_table_names()
    assert "chunks" in inspector.get_table_names()
    assert "ingestion_progress" in inspector.get_table_names()
    chunk_columns = {column["name"] for column in inspector.get_columns("chunks")}
    assert "embedding" not in chunk_columns

    with core.metadata_store.session() as session:
        row = session.get(core.metadata_store.DocumentModel, result.doc_id)

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

    original_client = core_module.MilvusClient
    core_module.MilvusClient = FakeMilvusClient
    try:
        core = create_core(tmp_path)
        result = core.ingest_text(
            token="token-a",
            text="alpha one. beta two. gamma three. delta four. epsilon five.",
            source="milvus-ids.txt",
        )
    finally:
        core_module.MilvusClient = original_client

    assert result.chunk_count == 2
    assert all("chunk_id" not in payload for payload in FakeMilvusClient.inserted_payload)

    with core.metadata_store.session() as session:
        rows = (
            session.query(core.metadata_store.ChunkModel)
            .filter_by(doc_id=result.doc_id)
            .order_by(core.metadata_store.ChunkModel.chunk_index)
            .all()
        )

    assert [row.chunk_id for row in rows] == [str(value) for value in generated_ids]


def test_ingestion_progress_rows_are_persisted_in_pipeline_order(tmp_path: Path) -> None:
    core = create_core(tmp_path)

    result = core.ingest_text(
        token="token-a",
        text="alpha one. beta two. gamma three. delta four. epsilon five.",
        source="pipeline.txt",
    )

    progress_rows = core.list_ingestion_progress(result.doc_id, token="token-a", job_id=result.job_id)
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
    core = create_core(tmp_path)

    result = core.ingest_text(
        token="token-a",
        text="alpha progress state tracking",
        source="stateful.txt",
    )

    progress_rows = core.list_ingestion_progress(result.doc_id, token="token-a")

    assert any(row.status == "running" for row in progress_rows)
    assert any(row.status == "completed" for row in progress_rows)
    assert {row.job_id for row in progress_rows}



def test_ingestion_progress_records_failed_step_when_ingest_errors(tmp_path: Path) -> None:
    core = create_core(tmp_path)

    try:
        core.ingest_text(token="token-a", text="   ", source="blank.txt")
    except ValueError as exc:
        assert str(exc) == "Document must contain non-empty text"
    else:
        raise AssertionError("Expected ValueError for blank document ingestion")

    failed_docs = core.list_documents(token="token-a")
    assert len(failed_docs) == 1
    failed_doc = failed_docs[0]
    progress_rows = core.list_ingestion_progress(failed_doc.doc_id, token="token-a")
    terminal_rows = [row for row in progress_rows if row.status != "running"]

    assert [row.step_name for row in terminal_rows] == ["load", "preprocess", "chunking"]
    assert [row.status for row in terminal_rows] == ["completed", "completed", "failed"]
    assert len({row.job_id for row in progress_rows}) == 1



def test_ingestion_progress_can_be_grouped_by_job_id_for_same_document(tmp_path: Path) -> None:
    core = create_core(tmp_path)
    first = core.ingest_text(token="token-a", text="alpha first ingest", source="same.txt")
    second = core.ingest_text(token="token-a", text="alpha second ingest", source="same.txt")

    first_rows = core.list_ingestion_progress(first.doc_id, token="token-a", job_id=first.job_id)
    second_rows = core.list_ingestion_progress(second.doc_id, token="token-a", job_id=second.job_id)

    assert first.job_id != second.job_id
    assert first_rows
    assert second_rows
    assert all(row.job_id == first.job_id for row in first_rows)
    assert all(row.job_id == second.job_id for row in second_rows)



def test_ingestion_progress_is_limited_to_current_token_scope(tmp_path: Path) -> None:
    core = create_core(tmp_path)
    token_a_result = core.ingest_text(token="token-a", text="alpha scoped pipeline", source="a.txt")
    core.ingest_text(token="token-b", text="beta scoped pipeline", source="b.txt")

    visible = core.list_ingestion_progress(token_a_result.doc_id, token="token-a")
    hidden = core.list_ingestion_progress(token_a_result.doc_id, token="token-b")

    assert visible
    assert all(row.doc_id == token_a_result.doc_id for row in visible)
    assert hidden == []


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
    assert all(row.chunk_id for row in chunk_rows)
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
    assert core.list_ingestion_progress(target.doc_id, token="token-a")

    deleted = core.delete_document(target.doc_id, token="token-a")

    assert deleted is True
    assert core.get_document(target.doc_id, token="token-a") is None
    assert core.list_document_chunks(target.doc_id, token="token-a") == []
    assert core.list_ingestion_progress(target.doc_id, token="token-a") == []
    assert not stored_path.exists()
    assert [doc.doc_id for doc in core.list_documents(token="token-a")] == [survivor.doc_id]

    response = core.query(token="token-a", question="Where is alpha?", top_k=5)
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

    try:
        service.store(chunks, [[1.0, 0.0, 0.0, 5.0]])
    except RuntimeError as exc:
        assert str(exc) == "sqlite write failed"
    else:
        raise AssertionError("Expected RuntimeError when chunk persistence fails")

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

    try:
        service.store(chunks, [[1.0, 0.0, 0.0, 5.0], [0.0, 1.0, 0.0, 4.0]])
    except RuntimeError as exc:
        assert str(exc) == "Milvus returned a mismatched number of chunk ids"
    else:
        raise AssertionError("Expected RuntimeError when Milvus returns a mismatched number of ids")

    assert vector_store.deleted_chunk_ids == [["101"]]
    assert metadata_store.add_chunks_calls == 0


def test_delete_document_leaves_metadata_intact_when_milvus_delete_fails_and_allows_retry(
    monkeypatch, tmp_path: Path
) -> None:
    core = create_core(tmp_path, storage_mode="local")
    ingested = core.ingest_text(token="token-a", text="alpha retry cleanup", source="retry.txt")
    original_delete_document = core.vector_store.delete_document
    attempts = {"count": 0}

    def flaky_delete_document(doc_id: str) -> None:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("milvus delete failed")
        original_delete_document(doc_id)

    monkeypatch.setattr(core.vector_store, "delete_document", flaky_delete_document)

    try:
        core.delete_document(ingested.doc_id, token="token-a")
    except RuntimeError as exc:
        assert str(exc) == "milvus delete failed"
    else:
        raise AssertionError("Expected RuntimeError when Milvus delete fails")

    assert core.get_document(ingested.doc_id, token="token-a") is not None
    assert core.list_document_chunks(ingested.doc_id, token="token-a")

    assert core.delete_document(ingested.doc_id, token="token-a") is True
    assert core.get_document(ingested.doc_id, token="token-a") is None


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
