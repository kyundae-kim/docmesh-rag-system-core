from __future__ import annotations

from pathlib import Path

from rag_system_core import RAGCore

from test_rag_system_core.support import FakeEmbeddingClient, FakeGenerationClient, create_test_rig


def test_rag_core_reads_milvus_configuration_from_environment(monkeypatch, tmp_path: Path) -> None:
    milvus_uri = tmp_path / "configured-milvus.db"
    monkeypatch.setenv("MILVUS_URI", str(milvus_uri))
    monkeypatch.setenv("MILVUS_COLLECTION_NAME", "configured_chunks")
    monkeypatch.setenv("MILVUS_TIMEOUT", "9.5")

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
