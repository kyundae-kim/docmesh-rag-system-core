from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from rag_system_core import RAGCore
from rag_system_core.composition.factories import (
    create_rag_chunker,
    create_rag_document_storage,
    create_rag_embedding_client,
    create_rag_generation_client,
    create_rag_metadata_store,
    create_rag_vector_store,
)

from test_rag_system_core.support import (
    authenticated_user,
    FakeEmbeddingClient,
    FakeGenerationClient,
    create_test_rig,
)

USER_A = authenticated_user("user-a")


def test_rag_core_reads_milvus_configuration_from_environment(monkeypatch, tmp_path: Path) -> None:
    milvus_uri = tmp_path / "configured-milvus.db"
    monkeypatch.setenv("MILVUS_URI", str(milvus_uri))
    monkeypatch.setenv("MILVUS_COLLECTION", "configured_chunks")
    monkeypatch.setenv("MILVUS_REQUEST_TIMEOUT_SECONDS", "9")

    rig = create_test_rig(tmp_path)
    ingested = rig.core.ingest_text(user=USER_A, text="alpha beta gamma", source="configured.txt")

    assert ingested.chunk_count == 1
    assert rig.core.vector_store.collection_name == "configured_chunks"
    assert rig.core.vector_store.timeout == 9.0
    assert milvus_uri.exists()

    restarted = RAGCore(
        embedding_client=FakeEmbeddingClient(),
        generation_client=FakeGenerationClient(),
        vector_store=create_rag_vector_store(metadata_path=tmp_path / "metadata.db"),
        metadata_store=create_rag_metadata_store(metadata_path=tmp_path / "metadata.db"),
        document_storage=create_rag_document_storage(
            storage_mode="local",
            document_storage_dir=tmp_path / "documents",
        ),
        chunker=create_rag_chunker(chunk_size=512, chunk_overlap=64),
    )
    response = restarted.query(user=USER_A, question="Where is alpha?", top_k=3)

    assert response.context_chunks
    assert any(chunk.doc_id == ingested.doc_id for chunk in response.context_chunks)


def test_rag_core_integration_uses_docmesh_environment(monkeypatch, tmp_path: Path) -> None:
    embed_calls: list[dict[str, Any]] = []
    chat_calls: list[dict[str, Any]] = []

    class FakeOllamaClient:
        def embed(self, *, model: str, input: list[str]) -> dict[str, list[list[float]]]:
            embed_calls.append({"model": model, "input": list(input)})
            return {"embeddings": [[float(len(text)), float(text.lower().count("alpha"))] for text in input]}

        def chat(self, *, model: str, messages: list[dict[str, str]]) -> dict[str, dict[str, str]]:
            chat_calls.append({"model": model, "messages": messages})
            return {"message": {"content": f"generated::{messages[0]['content'].splitlines()[-1]}"}}

    settings = SimpleNamespace(
        ollama=SimpleNamespace(
            host="http://shared-ollama",
            embedding_model="bge-m3",
            generation_model="gpt-oss:20b",
            request_timeout_seconds=18.5,
        )
    )
    milvus_uri = tmp_path / "configured-milvus.db"
    monkeypatch.setenv("MILVUS_URI", str(milvus_uri))
    monkeypatch.setenv("MILVUS_COLLECTION", "configured_chunks")
    monkeypatch.setenv("MILVUS_REQUEST_TIMEOUT_SECONDS", "9")
    monkeypatch.setattr(
        "rag_system_core.composition.factories.create_docmesh_service_client",
        lambda service_name, *, settings, bundle=None: FakeOllamaClient() if service_name == "ollama" else None,
    )

    core = RAGCore(
        embedding_client=create_rag_embedding_client(settings=settings),
        generation_client=create_rag_generation_client(settings=settings),
        vector_store=create_rag_vector_store(metadata_path=tmp_path / "metadata.db"),
        metadata_store=create_rag_metadata_store(metadata_path=tmp_path / "metadata.db"),
        document_storage=create_rag_document_storage(
            storage_mode="local",
            document_storage_dir=tmp_path / "documents",
        ),
        chunker=create_rag_chunker(chunk_size=512, chunk_overlap=64),
    )

    ingested = core.ingest_text(user=USER_A, text="alpha beta gamma", source="configured.txt")
    response = core.query(user=USER_A, question="Where is alpha?", top_k=3)

    assert ingested.chunk_count == 1
    assert response.answer == "generated::Where is alpha?"
    assert core.vector_store.collection_name == "configured_chunks"
    assert core.vector_store.timeout == 9.0
    assert embed_calls == [
        {"model": "bge-m3", "input": ["alpha beta gamma"]},
        {"model": "bge-m3", "input": ["Where is alpha?"]},
    ]
    assert chat_calls == [
        {
            "model": "gpt-oss:20b",
            "messages": [{"role": "user", "content": response.prompt}],
        }
    ]


def test_rag_core_uses_explicitly_constructed_vector_store(monkeypatch, tmp_path: Path) -> None:
    records: dict[str, object] = {}

    class FakeMilvusClient:
        def __init__(self, *, uri: str, timeout: float) -> None:
            records["uri"] = uri
            records["timeout"] = timeout

    monkeypatch.setattr("rag_system_core.composition.factories.MilvusClient", FakeMilvusClient)
    monkeypatch.setattr(
        "rag_system_core.composition.factories.resolve_milvus_runtime_settings",
        lambda *, fallback_uri, settings=None: (str(tmp_path / "external-milvus.db"), "resolved_chunks", 7.25),
    )
    monkeypatch.setattr(
        "rag_system_core.composition.factories.create_docmesh_service_client",
        lambda service_name, *, settings=None, bundle=None: None,
    )

    vector_store = create_rag_vector_store(metadata_path=tmp_path / "metadata.db")
    core = RAGCore(
        embedding_client=FakeEmbeddingClient(),
        generation_client=FakeGenerationClient(),
        vector_store=vector_store,
        metadata_store=create_rag_metadata_store(metadata_path=tmp_path / "metadata.db"),
        document_storage=create_rag_document_storage(
            storage_mode="local",
            document_storage_dir=tmp_path / "documents",
        ),
        chunker=create_rag_chunker(chunk_size=512, chunk_overlap=64),
    )

    assert records == {"uri": str(tmp_path / "external-milvus.db"), "timeout": 7.25}
    assert core.vector_store.collection_name == "resolved_chunks"
    assert core.vector_store.timeout == 7.25
    assert isinstance(core.vector_store._client, FakeMilvusClient)


def test_create_rag_vector_store_requires_external_client_construction(monkeypatch, tmp_path: Path) -> None:
    records: dict[str, object] = {}

    class FakeMilvusClient:
        def __init__(self, *, uri: str, timeout: float) -> None:
            records["uri"] = uri
            records["timeout"] = timeout

    monkeypatch.setattr("rag_system_core.composition.factories.MilvusClient", FakeMilvusClient)
    monkeypatch.setattr(
        "rag_system_core.composition.factories.create_docmesh_service_client",
        lambda service_name, *, settings=None, bundle=None: None,
    )

    store = create_rag_vector_store(
        metadata_path=tmp_path / "metadata.db",
        uri=str(tmp_path / "factory-milvus.db"),
        collection_name="factory_chunks",
        timeout=4.5,
    )

    assert records == {"uri": str(tmp_path / "factory-milvus.db"), "timeout": 4.5}
    assert store.collection_name == "factory_chunks"
    assert store.timeout == 4.5
    assert isinstance(store._client, FakeMilvusClient)
