from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_milvus_environment(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("MILVUS__URI", str(tmp_path / "test.milvus.db"))
    monkeypatch.delenv("MILVUS_URI", raising=False)
    monkeypatch.delenv("MILVUS_COLLECTION_NAME", raising=False)
    monkeypatch.delenv("MILVUS_TIMEOUT", raising=False)
