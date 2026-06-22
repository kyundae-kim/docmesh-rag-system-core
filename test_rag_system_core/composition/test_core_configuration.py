from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import rag_system_core.core as core_module
from rag_system_core import RAGCore
from rag_system_core.composition.factories import create_rag_embedding_client, create_rag_generation_client

from test_rag_system_core.support import FakeEmbeddingClient, FakeGenerationClient, create_test_rig


def test_rag_core_reads_milvus_configuration_from_environment(monkeypatch, tmp_path: Path) -> None:
    milvus_uri = tmp_path / "configured-milvus.db"
    monkeypatch.setenv("MILVUS_URI", str(milvus_uri))
    monkeypatch.setenv("MILVUS_COLLECTION", "configured_chunks")
    monkeypatch.setenv("MILVUS_REQUEST_TIMEOUT_SECONDS", "9.5")

    rig = create_test_rig(tmp_path)
    ingested = rig.core.ingest_text(token="token-a", text="alpha beta gamma", source="configured.txt")

    assert ingested.chunk_count == 1
    assert rig.core.vector_store.uri == str(milvus_uri)
    assert rig.core.vector_store.collection_name == "configured_chunks"
    assert rig.core.vector_store.timeout == 9.5
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
    monkeypatch.setenv("MILVUS_REQUEST_TIMEOUT_SECONDS", "9.5")
    monkeypatch.setattr(
        "rag_system_core.composition.factories.create_docmesh_service_client",
        lambda service_name, *, settings, registry=None: FakeOllamaClient() if service_name == "ollama" else None,
    )

    core = RAGCore(
        embedding_client=create_rag_embedding_client(settings=settings),
        generation_client=create_rag_generation_client(settings=settings),
        metadata_path=tmp_path / "metadata.db",
        document_storage_dir=tmp_path / "documents",
        storage_mode="local",
    )

    ingested = core.ingest_text(token="token-a", text="alpha beta gamma", source="configured.txt")
    response = core.query(token="token-a", question="Where is alpha?", top_k=3)

    assert ingested.chunk_count == 1
    assert response.answer == "generated::Where is alpha?"
    assert core.vector_store.uri == str(milvus_uri)
    assert core.vector_store.collection_name == "configured_chunks"
    assert core.vector_store.timeout == 9.5
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
