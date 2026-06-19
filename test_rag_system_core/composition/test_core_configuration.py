from __future__ import annotations

from pathlib import Path
from typing import Any

import rag_system_core.core as core_module
from rag_system_core import OllamaEmbeddingClient, OllamaGenerationClient, RAGCore

from test_rag_system_core.support import FakeEmbeddingClient, FakeGenerationClient, create_test_rig


def test_rag_core_reads_milvus_configuration_from_environment(monkeypatch, tmp_path: Path) -> None:
    milvus_uri = tmp_path / "configured-milvus.db"
    monkeypatch.setenv("MILVUS__URI", str(milvus_uri))
    monkeypatch.setenv("MILVUS__COLLECTION_NAME", "configured_chunks")
    monkeypatch.setenv("MILVUS__TIMEOUT", "9.5")

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


def test_rag_core_integration_uses_split_ollama_and_milvus_environment(monkeypatch, tmp_path: Path) -> None:
    client_inits: list[dict[str, Any]] = []
    embed_calls: list[dict[str, Any]] = []
    chat_calls: list[dict[str, Any]] = []

    class FakeOllamaClient:
        def __init__(self, *, host: str, timeout: float, headers: dict[str, str] | None = None) -> None:
            client_inits.append({"host": host, "timeout": timeout, "headers": headers})

        def embed(self, *, model: str, input: list[str]) -> dict[str, list[list[float]]]:
            embed_calls.append({"model": model, "input": list(input)})
            return {"embeddings": [[float(len(text)), float(text.lower().count("alpha"))] for text in input]}

        def chat(self, *, model: str, messages: list[dict[str, str]]) -> dict[str, dict[str, str]]:
            chat_calls.append({"model": model, "messages": messages})
            return {"message": {"content": f"generated::{messages[0]['content'].splitlines()[-1]}"}}

    milvus_uri = tmp_path / "configured-milvus.db"
    monkeypatch.setenv("OLLAMA_EMBED__BASE_URL", "http://embed-ollama")
    monkeypatch.setenv("OLLAMA_EMBED__MODEL", "bge-m3")
    monkeypatch.setenv("OLLAMA_EMBED__TIMEOUT", "12.5")
    monkeypatch.setenv("OLLAMA_GENERATE__BASE_URL", "https://generate-ollama")
    monkeypatch.setenv("OLLAMA_GENERATE__MODEL", "gpt-oss:20b")
    monkeypatch.setenv("OLLAMA_GENERATE__TIMEOUT", "18.5")
    monkeypatch.setenv("OLLAMA_GENERATE__API_KEY", "test-api-key")
    monkeypatch.setenv("MILVUS__URI", str(milvus_uri))
    monkeypatch.setenv("MILVUS__COLLECTION_NAME", "configured_chunks")
    monkeypatch.setenv("MILVUS__TIMEOUT", "9.5")
    monkeypatch.setattr(core_module.ollama, "Client", FakeOllamaClient)

    core = RAGCore(
        embedding_client=OllamaEmbeddingClient(),
        generation_client=OllamaGenerationClient(),
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
    assert client_inits == [
        {"host": "http://embed-ollama", "timeout": 12.5, "headers": None},
        {
            "host": "https://generate-ollama",
            "timeout": 18.5,
            "headers": {"Authorization": "Bearer test-api-key"},
        },
    ]
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
