from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from rag_system_core import RAGCore
from rag_system_core.composition.docmesh_runtime import assemble_docmesh_services
from rag_system_core.composition.factories import (
    DocmeshRAGServiceFactory,
    create_rag_chunker,
    create_rag_document_storage,
    create_rag_embedding_client,
    create_rag_generation_client,
    create_rag_metadata_store,
    create_rag_vector_store,
)
from rag_system_core.infrastructure import resolve_user_id
from rag_system_core.runtime import docmesh_sdk
from test_rag_system_core.support import FakeEmbeddingClient, FakeGenerationClient


class FakeDocmeshOllamaWrapper:
    def __init__(self, *, answer: str = "docmesh answer") -> None:
        self.embed_calls: list[dict[str, object]] = []
        self.chat_calls: list[dict[str, object]] = []
        self.answer = answer

    def embed(self, *, model: str, input: list[str]) -> dict[str, list[list[float]]]:
        self.embed_calls.append({"model": model, "input": list(input)})
        return {"embeddings": [[float(len(text)), float(text.lower().count("alpha"))] for text in input]}

    def chat(self, *, model: str, messages: list[dict[str, str]]) -> dict[str, dict[str, str]]:
        self.chat_calls.append({"model": model, "messages": messages})
        return {"message": {"content": self.answer}}


class FakeDocmeshMilvusWrapper:
    def __init__(self) -> None:
        self.check_calls = 0

    def check(self) -> None:
        self.check_calls += 1


def make_settings() -> SimpleNamespace:
    return SimpleNamespace(
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
        ),
    )


def test_assemble_docmesh_services_uses_v020_assembly_api(monkeypatch) -> None:
    records: dict[str, object] = {}
    expected_bundle = object()

    def fake_assemble_services(env, **kwargs):
        records["env"] = env
        records.update(kwargs)
        return expected_bundle

    monkeypatch.setattr(docmesh_sdk, "assemble_services", fake_assemble_services)
    env = {"OLLAMA_HOST": "http://ollama"}

    bundle = assemble_docmesh_services(
        env,
        required={"ollama"},
        check_on_startup=True,
        parallel_healthchecks=True,
    )

    assert bundle is expected_bundle
    assert records == {
        "env": env,
        "services": {"milvus", "ollama"},
        "required": {"ollama"},
        "check_on_startup": True,
        "parallel_healthchecks": True,
    }


def test_ollama_factories_use_clients_from_service_bundle() -> None:
    settings = make_settings()
    ollama = FakeDocmeshOllamaWrapper()
    bundle = SimpleNamespace(clients={"ollama": ollama})

    embedding_client = create_rag_embedding_client(settings=settings, bundle=bundle)
    generation_client = create_rag_generation_client(settings=settings, bundle=bundle)

    assert embedding_client.embed(["alpha", "beta"]) == [[5.0, 1.0], [4.0, 0.0]]
    assert generation_client.generate("Summarize alpha") == "docmesh answer"


def test_direct_ollama_factory_loads_v020_service_config_once(monkeypatch) -> None:
    settings = make_settings()
    ollama = FakeDocmeshOllamaWrapper()
    records = {"loads": 0}

    def fake_load_available_service_configs(env, *, services):
        del env
        assert services == {"ollama"}
        records["loads"] += 1
        return settings

    monkeypatch.setattr(
        docmesh_sdk,
        "load_available_service_configs",
        fake_load_available_service_configs,
    )
    monkeypatch.setattr(docmesh_sdk, "create_ollama_client", lambda config: ollama)

    client = create_rag_embedding_client()

    assert client.model == "bge-m3"
    assert records["loads"] == 1


def test_docmesh_factory_from_env_owns_bundle_lifecycle(monkeypatch) -> None:
    settings = make_settings()
    records: dict[str, object] = {"closed": False}
    bundle = SimpleNamespace(
        configs=settings,
        clients={"ollama": FakeDocmeshOllamaWrapper()},
        close=lambda: records.update(closed=True),
    )

    monkeypatch.setattr(
        "rag_system_core.composition.docmesh_runtime.assemble_docmesh_services",
        lambda env, *, required, check_on_startup: bundle,
    )

    factory = DocmeshRAGServiceFactory.from_env(
        {"OLLAMA_HOST": "http://ollama"},
        check_on_startup=True,
    )
    factory.close()

    assert factory.settings is settings
    assert factory.bundle is bundle
    assert records["closed"] is True


def test_ollama_factories_require_models_from_settings() -> None:
    settings = make_settings()
    settings.ollama.embedding_model = ""

    with pytest.raises(ValueError, match="Ollama embed model must be configured"):
        create_rag_embedding_client(
            settings=settings,
            bundle=SimpleNamespace(clients={"ollama": FakeDocmeshOllamaWrapper()}),
        )


def test_rag_core_health_check_uses_docmesh_aggregate(monkeypatch, tmp_path: Path) -> None:
    records: dict[str, object] = {}

    def fake_check_all_services(service_checks, *, required_services=None):
        records["services"] = sorted(service_checks)
        records["required"] = required_services
        for check in service_checks.values():
            check()
        return SimpleNamespace(ok=True)

    monkeypatch.setattr(docmesh_sdk, "check_all_services", fake_check_all_services)

    class CheckedEmbedding(FakeEmbeddingClient):
        def check(self) -> None:
            return None

    class CheckedGeneration(FakeGenerationClient):
        def check(self) -> None:
            return None

    core = RAGCore(
        embedding_client=CheckedEmbedding(),
        generation_client=CheckedGeneration(),
        vector_store=create_rag_vector_store(metadata_path=tmp_path / "metadata.db"),
        metadata_store=create_rag_metadata_store(metadata_path=tmp_path / "metadata.db"),
        document_storage=create_rag_document_storage(
            storage_mode="local",
            document_storage_dir=tmp_path / "documents",
        ),
        chunker=create_rag_chunker(chunk_size=512, chunk_overlap=64),
    )

    assert core.health_check().ok is True
    assert records["services"] == ["embedding", "generation", "metadata", "milvus"]


def test_resolve_user_id_uses_keycloak_service_config(monkeypatch) -> None:
    records: dict[str, object] = {}
    keycloak_config = object()
    configs = SimpleNamespace(require_keycloak=lambda: keycloak_config)

    def fake_load_service_configs(env, *, services):
        records["services"] = services
        return configs

    class FakeKeycloakAuthService:
        def __init__(self, config, allowed_algorithms=None) -> None:
            records["config"] = config
            records["allowed_algorithms"] = allowed_algorithms

        def extract_user_info(self, token: str):
            records["token"] = token
            return SimpleNamespace(sub="user-from-keycloak")

    monkeypatch.setattr(docmesh_sdk, "load_service_configs", fake_load_service_configs)
    monkeypatch.setattr(docmesh_sdk, "KeycloakAuthService", FakeKeycloakAuthService)
    monkeypatch.setenv("DOCMESH_AUTH_MODE", "keycloak")

    assert resolve_user_id("Bearer abc.def.ghi") == "user-from-keycloak"
    assert records == {
        "services": {"keycloak"},
        "config": keycloak_config,
        "allowed_algorithms": ["RS256"],
        "token": "Bearer abc.def.ghi",
    }


def test_vector_store_uses_local_fallback_when_milvus_is_not_configured(monkeypatch, tmp_path: Path) -> None:
    records: dict[str, object] = {}

    class FakeMilvusClient:
        def __init__(self, *, uri: str, timeout: float) -> None:
            records.update(uri=uri, timeout=timeout)

    monkeypatch.setattr("rag_system_core.composition.factories.MilvusClient", FakeMilvusClient)
    settings = SimpleNamespace(milvus=None)

    store = create_rag_vector_store(
        metadata_path=tmp_path / "metadata.db",
        settings=settings,
    )

    expected_uri = str((tmp_path / "metadata.db").with_suffix(".milvus.db"))
    assert records == {"uri": expected_uri, "timeout": 30.0}
    assert store.collection_name == "rag_chunks"