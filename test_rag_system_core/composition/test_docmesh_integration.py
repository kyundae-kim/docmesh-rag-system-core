from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import rag_system_core.infrastructure as infrastructure_module
from rag_system_core import OllamaEmbeddingClient, OllamaGenerationClient, RAGCore
from rag_system_core.infrastructure import resolve_user_id

from test_rag_system_core.support import FakeEmbeddingClient, FakeGenerationClient


class FakeDocmeshOllamaWrapper:
    def __init__(self, *, answer: str = "docmesh answer") -> None:
        self.embed_calls: list[dict[str, object]] = []
        self.chat_calls: list[dict[str, object]] = []
        self.check_calls = 0
        self.answer = answer

    def embed(self, *, model: str, input: list[str]) -> dict[str, list[list[float]]]:
        self.embed_calls.append({"model": model, "input": list(input)})
        return {"embeddings": [[float(len(text)), float(text.lower().count("alpha"))] for text in input]}

    def chat(self, *, model: str, messages: list[dict[str, str]]) -> dict[str, dict[str, str]]:
        self.chat_calls.append({"model": model, "messages": messages})
        return {"message": {"content": self.answer}}

    def check(self) -> None:
        self.check_calls += 1


class FakeDocmeshMilvusWrapper:
    def __init__(self) -> None:
        self.check_calls = 0

    def check(self) -> None:
        self.check_calls += 1


def install_fake_docmesh(monkeypatch, *, ollama_wrapper: FakeDocmeshOllamaWrapper | None = None) -> tuple[dict[str, object], FakeDocmeshMilvusWrapper]:
    records: dict[str, object] = {"settings_calls": 0, "registry_settings": []}
    fake_ollama = ollama_wrapper or FakeDocmeshOllamaWrapper()
    fake_milvus = FakeDocmeshMilvusWrapper()
    settings = SimpleNamespace(
        ollama=SimpleNamespace(
            host="http://docmesh-ollama",
            embedding_model="bge-m3",
            generation_model="gpt-oss:20b",
            request_timeout_seconds=12.5,
        ),
        milvus=SimpleNamespace(
            uri="/tmp/docmesh-milvus.db",
            collection="docmesh_chunks",
            request_timeout_seconds=9.5,
            connect_timeout_seconds=7.0,
        ),
    )

    class FakeRegistry:
        def __init__(self, loaded_settings) -> None:
            records["registry_settings"].append(loaded_settings)

        def create_client(self, service_name: str):
            records.setdefault("created_services", []).append(service_name)
            if service_name == "ollama":
                return fake_ollama
            if service_name == "milvus":
                return fake_milvus
            raise KeyError(service_name)

        def close_all(self) -> None:
            records["closed"] = True

    def fake_load_settings(env) -> object:
        records["settings_calls"] += 1
        records["last_env_type"] = type(env).__name__
        return settings

    def fake_check_all_services(service_checks, required_services=None):
        service_names = sorted(service_checks)
        records["health_checked_services"] = service_names
        for check in service_checks.values():
            check()
        return SimpleNamespace(ok=True, services=service_names, required_services=required_services)

    class FakeKeycloakAuthService:
        def __init__(self, loaded_settings, allowed_algorithms=None) -> None:
            records["keycloak_settings"] = loaded_settings
            records["allowed_algorithms"] = allowed_algorithms

        def extract_user_info(self, token: str):
            records["validated_token"] = token
            return SimpleNamespace(sub="user-from-keycloak", preferred_username="alice")

    monkeypatch.setattr(infrastructure_module, "load_settings", fake_load_settings)
    monkeypatch.setattr(infrastructure_module, "ServiceFactoryRegistry", FakeRegistry)
    monkeypatch.setattr(infrastructure_module, "check_all_services", fake_check_all_services)
    monkeypatch.setattr(infrastructure_module, "KeycloakAuthService", FakeKeycloakAuthService)
    return records, fake_milvus


def test_ollama_clients_use_docmesh_service_factory_when_available(monkeypatch) -> None:
    records, _ = install_fake_docmesh(monkeypatch)

    embedding_client = OllamaEmbeddingClient()
    generation_client = OllamaGenerationClient()

    vectors = embedding_client.embed(["alpha", "beta"])
    answer = generation_client.generate("Summarize alpha")

    assert vectors == [[5.0, 1.0], [4.0, 0.0]]
    assert answer == "docmesh answer"
    assert records["settings_calls"] == 2
    assert records["created_services"] == ["ollama", "ollama"]


def test_rag_core_health_check_uses_docmesh_aggregate_when_available(monkeypatch, tmp_path: Path) -> None:
    records, fake_milvus = install_fake_docmesh(monkeypatch)

    class HealthCheckedEmbeddingClient(FakeEmbeddingClient):
        def __init__(self) -> None:
            super().__init__()
            self.check_calls = 0

        def check(self) -> None:
            self.check_calls += 1

    class HealthCheckedGenerationClient(FakeGenerationClient):
        def __init__(self) -> None:
            super().__init__()
            self.check_calls = 0

        def check(self) -> None:
            self.check_calls += 1

    embedding_client = HealthCheckedEmbeddingClient()
    generation_client = HealthCheckedGenerationClient()
    core = RAGCore(
        embedding_client=embedding_client,
        generation_client=generation_client,
        metadata_path=tmp_path / "metadata.db",
        document_storage_dir=tmp_path / "documents",
        storage_mode="local",
    )

    result = core.health_check()

    assert result.ok is True
    assert records["health_checked_services"] == ["embedding", "generation", "metadata", "milvus"]
    assert embedding_client.check_calls == 1
    assert generation_client.check_calls == 1
    assert fake_milvus.check_calls == 1


def test_resolve_user_id_uses_keycloak_when_auth_mode_enabled(monkeypatch) -> None:
    records, _ = install_fake_docmesh(monkeypatch)
    monkeypatch.setenv("DOCMESH_AUTH_MODE", "keycloak")

    resolved = resolve_user_id("Bearer abc.def.ghi")

    assert resolved == "user-from-keycloak"
    assert records["validated_token"] == "Bearer abc.def.ghi"


def test_ollama_embedding_client_requires_valid_docmesh_settings_even_with_explicit_overrides(monkeypatch) -> None:
    def broken_load_settings(env) -> object:
        del env
        raise RuntimeError("invalid docmesh settings")

    monkeypatch.setattr(infrastructure_module, "load_settings", broken_load_settings)

    with pytest.raises(RuntimeError, match="invalid docmesh settings"):
        OllamaEmbeddingClient(model="bge-m3", base_url="http://ollama", timeout=7.0)


def test_rag_core_requires_valid_docmesh_settings_for_milvus_runtime(monkeypatch, tmp_path: Path) -> None:
    def broken_load_settings(env) -> object:
        del env
        raise RuntimeError("invalid docmesh settings")

    monkeypatch.setattr(infrastructure_module, "load_settings", broken_load_settings)

    with pytest.raises(RuntimeError, match="invalid docmesh settings"):
        RAGCore(
            embedding_client=FakeEmbeddingClient(),
            generation_client=FakeGenerationClient(),
            metadata_path=tmp_path / "metadata.db",
            document_storage_dir=tmp_path / "documents",
            storage_mode="local",
        )
