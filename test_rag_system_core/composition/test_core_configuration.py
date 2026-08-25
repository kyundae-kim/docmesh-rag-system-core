from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace
from typing import Any, get_type_hints

import rag_system_core.composition.rag_factories as rag_factories_module
from pymilvus import MilvusClient
import pytest
from rag_system_core import RAGCore
from rag_system_core.adapters.chunking import FixedWindowChunker
from rag_system_core.composition.factories import (
    DocmeshRAGServiceFactory,
    create_rag_embedding_client,
    create_rag_generation_client,
    create_rag_vector_store,
)
from rag_system_core.ports import EmbeddingClient, GenerationClient, VectorStore

from test_rag_system_core.support import (
    authenticated_user,
    create_metadata_store,
    FakeDocumentStorage,
    FakeEmbeddingClient,
    FakeGenerationClient,
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


def test_rag_core_uses_explicit_milvus_configuration(tmp_path: Path) -> None:
    milvus_endpoint = tmp_path / "configured-milvus.db"

    def create_core() -> RAGCore:
        return RAGCore(
            embedding_client=FakeEmbeddingClient(),
            generation_client=FakeGenerationClient(),
            vector_store=create_rag_vector_store(
                client=MilvusClient(uri=str(milvus_endpoint)),
                collection_name="configured_chunks",
                timeout=9.0,
            ),
            metadata_store=create_metadata_store(tmp_path),
            document_storage=FakeDocumentStorage("local", tmp_path / "documents"),
            chunker=FixedWindowChunker(chunk_size=512, chunk_overlap=64),
        )

    core = create_core()
    ingested = core.ingest_text(user=USER_A, text="alpha beta gamma", source="configured.txt")

    assert ingested.chunk_count == 1
    assert core.vector_store.collection_name == "configured_chunks"
    assert core.vector_store.timeout == 9.0
    assert milvus_endpoint.exists()

    restarted = create_core()
    response = restarted.query(user=USER_A, question="Where is alpha?", top_k=3)

    assert response.context_chunks
    assert any(chunk.doc_id == ingested.doc_id for chunk in response.context_chunks)


def test_rag_core_integration_uses_explicit_service_settings(monkeypatch, tmp_path: Path) -> None:
    embed_calls: list[dict[str, Any]] = []
    chat_calls: list[dict[str, Any]] = []
    create_service_client = rag_factories_module.create_docmesh_service_client

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
    milvus_client = MilvusClient(uri=str(milvus_endpoint))
    monkeypatch.setattr(
        "rag_system_core.composition.rag_factories.create_docmesh_service_client",
        lambda service_name, *, settings, bundle=None: (
            FakeOllamaClient()
            if service_name == "ollama"
            else create_service_client(service_name, settings=settings, bundle=bundle)
        ),
    )

    core = RAGCore(
        embedding_client=create_rag_embedding_client(settings=settings),
        generation_client=create_rag_generation_client(settings=settings),
        vector_store=create_rag_vector_store(
            client=milvus_client,
            collection_name="configured_chunks",
            timeout=9.0,
        ),
        metadata_store=create_metadata_store(tmp_path),
        document_storage=FakeDocumentStorage("local", tmp_path / "documents"),
        chunker=FixedWindowChunker(chunk_size=512, chunk_overlap=64),
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
        "rag_system_core.composition.rag_factories.create_docmesh_service_client",
        lambda service_name, *, settings=None, bundle=None: None,
    )

    vector_store = create_rag_vector_store(settings=settings, client=client)
    core = RAGCore(
        embedding_client=FakeEmbeddingClient(),
        generation_client=FakeGenerationClient(),
        vector_store=vector_store,
        metadata_store=create_metadata_store(tmp_path),
        document_storage=FakeDocumentStorage("local", tmp_path / "documents"),
        chunker=FixedWindowChunker(chunk_size=512, chunk_overlap=64),
    )

    assert core.vector_store.collection_name == "resolved_chunks"
    assert core.vector_store.timeout == 7.25
    assert core.vector_store._client is client


def test_create_rag_vector_store_requires_explicit_client() -> None:
    with pytest.raises(RuntimeError, match="Failed to create Milvus service client"):
        create_rag_vector_store(
            collection_name="factory_chunks",
            timeout=4.5,
        )
