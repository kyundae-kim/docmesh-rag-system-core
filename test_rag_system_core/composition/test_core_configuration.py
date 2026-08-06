from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
from types import SimpleNamespace
from typing import Any, get_type_hints

import rag_system_core.composition.factories as factories_module
import rag_system_core.storage as storage_module
import pytest
from rag_system_core import RAGCore
from rag_system_core.adapters.chunking import FixedWindowChunker
from rag_system_core.composition.factories import (
    DocmeshRAGServiceFactory,
    create_rag_embedding_client,
    create_rag_generation_client,
    create_rag_vector_store,
)
from rag_system_core.composition.health import run_health_checks
from rag_system_core.ports import EmbeddingClient, GenerationClient, VectorStore
from rag_system_core.storage.metadata_store import MetadataStore

from test_rag_system_core.support import (
    authenticated_user,
    FakeDocumentStorage,
    FakeEmbeddingClient,
    FakeGenerationClient,
    create_test_rig,
)

USER_A = authenticated_user("user-a")


def test_configurable_factories_expose_only_explicit_keyword_parameters() -> None:
    factories = (
        create_rag_embedding_client,
        create_rag_generation_client,
        create_rag_vector_store,
    )

    for factory in factories:
        parameters = inspect.signature(factory).parameters.values()
        assert all(parameter.kind is not inspect.Parameter.VAR_KEYWORD for parameter in parameters)


def test_factory_functions_declare_composition_contract_return_types() -> None:
    expected_return_types = {
        create_rag_embedding_client: EmbeddingClient,
        create_rag_generation_client: GenerationClient,
        create_rag_vector_store: VectorStore,
    }

    for factory, expected_return_type in expected_return_types.items():
        assert get_type_hints(factory)["return"] is expected_return_type


def test_rag_core_reads_milvus_configuration_from_environment(monkeypatch, tmp_path: Path) -> None:
    milvus_endpoint = tmp_path / "configured-milvus.db"
    monkeypatch.setenv("MILVUS_ENDPOINT", str(milvus_endpoint))
    monkeypatch.setenv("MILVUS_COLLECTION", "configured_chunks")
    monkeypatch.setenv("MILVUS_REQUEST_TIMEOUT_SECONDS", "9")

    rig = create_test_rig(tmp_path)
    ingested = rig.core.ingest_text(user=USER_A, text="alpha beta gamma", source="configured.txt")

    assert ingested.chunk_count == 1
    assert rig.core.vector_store.collection_name == "configured_chunks"
    assert rig.core.vector_store.timeout == 9.0
    assert milvus_endpoint.exists()

    restarted = RAGCore(
        embedding_client=FakeEmbeddingClient(),
        generation_client=FakeGenerationClient(),
        vector_store=create_rag_vector_store(),
        metadata_store=MetadataStore(tmp_path / "metadata.db"),
        document_storage=FakeDocumentStorage("local", tmp_path / "documents"),
        chunker=FixedWindowChunker(chunk_size=512, chunk_overlap=64),
        health_check_runner=run_health_checks,
    )
    response = restarted.query(user=USER_A, question="Where is alpha?", top_k=3)

    assert response.context_chunks
    assert any(chunk.doc_id == ingested.doc_id for chunk in response.context_chunks)


def test_rag_core_integration_uses_docmesh_environment(monkeypatch, tmp_path: Path) -> None:
    embed_calls: list[dict[str, Any]] = []
    chat_calls: list[dict[str, Any]] = []
    create_service_client = factories_module.create_docmesh_service_client

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
    milvus_endpoint = tmp_path / "configured-milvus.db"
    monkeypatch.setenv("MILVUS_ENDPOINT", str(milvus_endpoint))
    monkeypatch.setenv("MILVUS_COLLECTION", "configured_chunks")
    monkeypatch.setenv("MILVUS_REQUEST_TIMEOUT_SECONDS", "9")
    monkeypatch.setattr(
        "rag_system_core.composition.factories.create_docmesh_service_client",
        lambda service_name, *, settings, bundle=None: (
            FakeOllamaClient()
            if service_name == "ollama"
            else create_service_client(service_name, settings=settings, bundle=bundle)
        ),
    )

    core = RAGCore(
        embedding_client=create_rag_embedding_client(settings=settings),
        generation_client=create_rag_generation_client(settings=settings),
        vector_store=create_rag_vector_store(),
        metadata_store=MetadataStore(tmp_path / "metadata.db"),
        document_storage=FakeDocumentStorage("local", tmp_path / "documents"),
        chunker=FixedWindowChunker(chunk_size=512, chunk_overlap=64),
        health_check_runner=run_health_checks,
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
    class FakeMilvusClient:
        pass

    client = FakeMilvusClient()
    settings = SimpleNamespace(
        milvus=SimpleNamespace(
            collection="resolved_chunks",
            request_timeout_seconds=7.25,
        )
    )
    monkeypatch.setattr(
        "rag_system_core.composition.factories.create_docmesh_service_client",
        lambda service_name, *, settings=None, bundle=None: None,
    )

    vector_store = create_rag_vector_store(settings=settings, client=client)
    core = RAGCore(
        embedding_client=FakeEmbeddingClient(),
        generation_client=FakeGenerationClient(),
        vector_store=vector_store,
        metadata_store=MetadataStore(tmp_path / "metadata.db"),
        document_storage=FakeDocumentStorage("local", tmp_path / "documents"),
        chunker=FixedWindowChunker(chunk_size=512, chunk_overlap=64),
        health_check_runner=run_health_checks,
    )

    assert core.vector_store.collection_name == "resolved_chunks"
    assert core.vector_store.timeout == 7.25
    assert core.vector_store._client is client


def test_create_rag_vector_store_requires_docmesh_or_explicit_client(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "rag_system_core.composition.factories.create_docmesh_service_client",
        lambda service_name, *, settings=None, bundle=None: None,
    )

    with pytest.raises(RuntimeError, match="Failed to create Milvus service client"):
        create_rag_vector_store(
            collection_name="factory_chunks",
            timeout=4.5,
        )
