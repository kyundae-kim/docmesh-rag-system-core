from __future__ import annotations

import os
from pathlib import Path

import pytest
from minio import Minio

from rag_system_core import RAGCore, bootstrap_rag_core_from_env
from test_rag_system_core.support import authenticated_user


pytestmark = [
    pytest.mark.integration,
]


def _ensure_dms_bucket_exists() -> None:
    client = Minio(
        os.environ["DMS_MINIO_ENDPOINT"],
        access_key=os.environ["DMS_MINIO_ACCESS_KEY"],
        secret_key=os.environ["DMS_MINIO_SECRET_KEY"],
        secure=os.environ.get("DMS_MINIO_SECURE", "false").lower() == "true",
    )
    bucket = os.environ["DMS_MINIO_BUCKET"]
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def test_bootstrap_from_env_creates_rag_core_instance(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "http://ollama:11434")
    monkeypatch.setenv("OLLAMA_EMBEDDING_MODEL", "bge-m3")
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "llama3.2")
    monkeypatch.setenv("MILVUS_ENDPOINT", str(tmp_path / "milvus.db"))
    monkeypatch.setenv("DMS_SQLITE_PATH", str(tmp_path / "dms.db"))

    with bootstrap_rag_core_from_env(metadata_path=tmp_path / "rag.db") as core:
        assert isinstance(core, RAGCore)


def test_ingest_query_and_delete_work_across_integrated_services(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "http://ollama:11434")
    monkeypatch.setenv("OLLAMA_EMBEDDING_MODEL", "bge-m3")
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "llama3.2")
    monkeypatch.setenv("MILVUS_ENDPOINT", str(tmp_path / "milvus.db"))
    monkeypatch.setenv("DMS_SQLITE_PATH", str(tmp_path / "dms.db"))
    user = authenticated_user("integration-user")
    text = "The integration verification code is cobalt-orchid-2718."
    _ensure_dms_bucket_exists()

    with bootstrap_rag_core_from_env(metadata_path=tmp_path / "rag.db") as core:
        result = core.ingest_text(user=user, text=text, source="integration.txt")

        document = core.get_document(result.doc_id, user=user)
        assert document is not None
        assert core.document_storage.load(document) == text

        response = core.query(
            user=user,
            question="What is the integration verification code?",
            top_k=1,
        )

        assert [chunk.content for chunk in response.context_chunks] == [text]
        assert response.answer.strip()

        assert core.delete_document(result.doc_id, user=user) is True
        assert core.get_document(result.doc_id, user=user) is None
        assert core.document_storage.load(document) is None
