from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_docmesh_environment(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("MILVUS_ENDPOINT", str(tmp_path / "test.milvus.db"))
    monkeypatch.delenv("MILVUS_COLLECTION", raising=False)
    monkeypatch.delenv("MILVUS_REQUEST_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("MILVUS_CONNECT_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)
    monkeypatch.delenv("OLLAMA_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_GENERATION_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_REQUEST_TIMEOUT_SECONDS", raising=False)