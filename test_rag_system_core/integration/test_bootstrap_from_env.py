from __future__ import annotations

import os
from pathlib import Path

import pytest

from rag_system_core import RAGCore, bootstrap_rag_core_from_env


pytestmark = [
    pytest.mark.integration,
]


def test_bootstrap_from_env_creates_rag_core_instance(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OLLAMA_HOST", "http://ollama:11434")
    monkeypatch.setenv("OLLAMA_EMBEDDING_MODEL", "bge-m3")
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "llama3.2")
    monkeypatch.setenv("MILVUS_URI", str(tmp_path / "milvus.db"))
    monkeypatch.setenv("DMS_SQLITE_PATH", str(tmp_path / "dms.db"))

    with bootstrap_rag_core_from_env(metadata_path=tmp_path / "rag.db") as core:
        assert isinstance(core, RAGCore)