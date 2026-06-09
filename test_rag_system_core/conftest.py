from __future__ import annotations

from types import SimpleNamespace

import pytest

import rag_system_core.infrastructure as infrastructure_module


def _optional_float(value: str | None) -> float | None:
    if value is None or not str(value).strip():
        return None
    return float(value)


@pytest.fixture(autouse=True)
def isolate_docmesh_environment(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("MILVUS__URI", str(tmp_path / "test.milvus.db"))
    monkeypatch.delenv("MILVUS_URI", raising=False)
    monkeypatch.delenv("MILVUS_COLLECTION_NAME", raising=False)
    monkeypatch.delenv("MILVUS_TIMEOUT", raising=False)

    def fake_load_settings(env) -> object:
        return SimpleNamespace(
            ollama=SimpleNamespace(
                host=env.get("OLLAMA_HOST"),
                embedding_model=env.get("OLLAMA_EMBEDDING_MODEL"),
                generation_model=env.get("OLLAMA_GENERATION_MODEL"),
                request_timeout_seconds=_optional_float(env.get("OLLAMA_REQUEST_TIMEOUT_SECONDS")),
            ),
            milvus=SimpleNamespace(
                uri=env.get("MILVUS_URI"),
                collection=env.get("MILVUS_COLLECTION") or env.get("MILVUS_COLLECTION_NAME"),
                request_timeout_seconds=_optional_float(env.get("MILVUS_REQUEST_TIMEOUT_SECONDS")),
                connect_timeout_seconds=_optional_float(env.get("MILVUS_CONNECT_TIMEOUT_SECONDS")),
            ),
        )

    class FakeRegistry:
        def __init__(self, loaded_settings) -> None:
            self.loaded_settings = loaded_settings

        def create_client(self, service_name: str):
            del service_name
            return None

        def close_all(self) -> None:
            return None

    monkeypatch.setattr(infrastructure_module, "load_settings", fake_load_settings)
    monkeypatch.setattr(infrastructure_module, "ServiceFactoryRegistry", FakeRegistry)
