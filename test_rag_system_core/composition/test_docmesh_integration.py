from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import dms
import docmesh_py_core
import pytest

from rag_system_core import RAGCore
from rag_system_core.adapters.chunking import FixedWindowChunker
from rag_system_core.composition.docmesh_runtime import (
    assemble_docmesh_services,
    load_dms_settings,
    load_docmesh_settings,
)
from rag_system_core.composition.factories import (
    DocmeshRAGServiceFactory,
    create_rag_embedding_client,
    create_rag_generation_client,
    create_rag_vector_store,
)
from rag_system_core.composition.health import run_health_checks
from rag_system_core.storage.metadata_store import MetadataStore
from test_rag_system_core.support import FakeDocumentStorage, FakeEmbeddingClient, FakeGenerationClient


def test_infrastructure_has_no_package_root_facade_module() -> None:
    assert importlib.util.find_spec("rag_system_core.infrastructure") is None


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


def test_load_docmesh_settings_uses_v050_keyword_only_api(monkeypatch) -> None:
    records: dict[str, object] = {}
    expected_settings = object()

    def fake_load_available_service_configs(*, services):
        records["services"] = services
        return expected_settings

    monkeypatch.setattr(
        docmesh_py_core,
        "load_available_service_configs",
        fake_load_available_service_configs,
    )

    settings = load_docmesh_settings(services={"milvus"})

    assert settings is expected_settings
    assert records == {"services": {"milvus"}}


@pytest.mark.parametrize(
    ("backend", "service_environment", "service_name"),
    [
        (
            "sqlite",
            {
                "DMS_SQLITE_PATH": "/tmp/dms-prefixed.db",
                "DMS_SQLITE_ENABLE_WAL": "true",
            },
            "sqlite",
        ),
        (
            "postgresql",
            {
                "DMS_POSTGRES_HOST": "dms-postgres",
                "DMS_POSTGRES_DB": "dms",
                "DMS_POSTGRES_USER": "dms-user",
                "DMS_POSTGRES_PASSWORD": "dms-password",
            },
            "postgres",
        ),
    ],
)
def test_load_dms_settings_uses_dms_prefixed_service_environment(
    monkeypatch,
    backend: str,
    service_environment: dict[str, str],
    service_name: str,
) -> None:
    monkeypatch.setenv("DMS_METADATA_BACKEND", backend)
    monkeypatch.setenv("DMS_DOCMESH_ENV", "dms-development")
    monkeypatch.setenv("DMS_MINIO_ENDPOINT", "dms-minio:9000")
    monkeypatch.setenv("DMS_MINIO_ACCESS_KEY", "dms-access-key")
    monkeypatch.setenv("DMS_MINIO_SECRET_KEY", "dms-secret-key")
    monkeypatch.setenv("DMS_MINIO_BUCKET", "dms-documents")
    monkeypatch.setenv("MINIO_ENDPOINT", "shared-minio:9000")
    monkeypatch.setenv("SQLITE_PATH", "/tmp/shared.db")
    for key, value in service_environment.items():
        monkeypatch.setenv(key, value)

    settings = load_dms_settings()

    assert settings.common.env == "dms-development"
    assert settings.minio is not None
    assert settings.minio.endpoint == "dms-minio:9000"
    assert settings.minio.bucket == "dms-documents"
    selected_service = getattr(settings, service_name)
    assert selected_service is not None
    if service_name == "sqlite":
        assert selected_service.path == "/tmp/dms-prefixed.db"
        assert selected_service.enable_wal is True
        assert settings.postgres is None
    else:
        assert selected_service.host == "dms-postgres"
        assert settings.sqlite is None


def test_load_dms_settings_reports_prefixed_missing_environment_keys(monkeypatch) -> None:
    monkeypatch.setenv("DMS_METADATA_BACKEND", "sqlite")
    monkeypatch.setenv("DMS_SQLITE_PATH", "/tmp/dms-prefixed.db")
    monkeypatch.setenv("MINIO_ENDPOINT", "shared-minio:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "shared-access-key")
    monkeypatch.setenv("MINIO_SECRET_KEY", "shared-secret-key")
    monkeypatch.setenv("MINIO_BUCKET", "shared-documents")
    for key in (
        "DMS_MINIO_ENDPOINT",
        "DMS_MINIO_ACCESS_KEY",
        "DMS_MINIO_SECRET_KEY",
        "DMS_MINIO_BUCKET",
    ):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(dms.ConfigurationError) as exc_info:
        load_dms_settings()

    assert "DMS_MINIO_ENDPOINT" in str(exc_info.value)
    assert "MINIO_ENDPOINT" not in exc_info.value.diagnosis.missing_required_keys
    assert "DMS_MINIO_ENDPOINT" in exc_info.value.diagnosis.missing_required_keys


def test_assemble_docmesh_services_uses_v050_keyword_only_api(monkeypatch) -> None:
    records: dict[str, object] = {}
    expected_bundle = object()

    def fake_assemble_services(**kwargs):
        records.update(kwargs)
        return expected_bundle

    monkeypatch.setattr(docmesh_py_core, "assemble_services", fake_assemble_services)

    bundle = assemble_docmesh_services(
        required={"ollama"},
        check_on_startup=True,
        parallel_healthchecks=True,
    )

    assert bundle is expected_bundle
    assert records == {
        "services": {"milvus", "ollama"},
        "required": {"ollama"},
        "one_of": (),
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


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (create_rag_embedding_client, "Ollama embed model must be configured"),
        (create_rag_generation_client, "Ollama generation model must be configured"),
    ],
)
def test_ollama_factories_do_not_replace_an_explicit_empty_model(factory, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        factory(
            settings=make_settings(),
            model="",
            client=FakeDocmeshOllamaWrapper(),
        )


@pytest.mark.parametrize(
    ("factory", "expected_model"),
    [
        (create_rag_embedding_client, "explicit-embedding"),
        (create_rag_generation_client, "explicit-generation"),
    ],
)
def test_ollama_factories_prefer_an_explicit_model(factory, expected_model: str) -> None:
    client = factory(
        settings=make_settings(),
        model=expected_model,
        client=FakeDocmeshOllamaWrapper(),
    )

    assert client.model == expected_model


def test_direct_ollama_factory_loads_v050_service_config_once(monkeypatch) -> None:
    settings = make_settings()
    ollama = FakeDocmeshOllamaWrapper()
    records = {"loads": 0}

    def fake_load_available_service_configs(*, services):
        assert services == {"ollama"}
        records["loads"] += 1
        return settings

    monkeypatch.setattr(
        docmesh_py_core,
        "load_available_service_configs",
        fake_load_available_service_configs,
    )
    monkeypatch.setattr(docmesh_py_core, "create_ollama_client", lambda config: ollama)

    client = create_rag_embedding_client()

    assert client.model == "bge-m3"
    assert records["loads"] == 1


def test_docmesh_factory_from_env_owns_bundle_lifecycle(monkeypatch) -> None:
    settings = make_settings()
    dms_settings = SimpleNamespace()
    records: dict[str, object] = {"bundle_closed": False, "dms_closed": False}
    bundle = SimpleNamespace(
        configs=settings,
        clients={"ollama": FakeDocmeshOllamaWrapper()},
        close=lambda: records.update(bundle_closed=True),
    )
    dms_sdk = SimpleNamespace(close=lambda: records.update(dms_closed=True))

    def fake_assemble_docmesh_services(*, services, required, one_of, check_on_startup):
        records["assembly"] = {
            "services": services,
            "required": required,
            "one_of": one_of,
            "check_on_startup": check_on_startup,
        }
        return bundle

    monkeypatch.setattr(
        "rag_system_core.composition.docmesh_runtime.assemble_docmesh_services",
        fake_assemble_docmesh_services,
    )
    monkeypatch.setattr(
        "rag_system_core.composition.docmesh_runtime.load_dms_settings",
        lambda: dms_settings,
    )

    def fake_create_dms_sdk(configs, *, check_on_startup):
        records["dms_configs"] = configs
        records["dms_check_on_startup"] = check_on_startup
        return dms_sdk

    monkeypatch.setattr(
        "rag_system_core.composition.factories.dms.create_sdk_from_service_configs",
        fake_create_dms_sdk,
    )

    factory = DocmeshRAGServiceFactory.from_env(check_on_startup=True)
    storage = factory.create_document_storage()
    factory.close()

    assert factory.settings is settings
    assert factory.bundle is bundle
    assert storage.sdk is dms_sdk
    assert records == {
        "assembly": {
            "services": {"milvus", "ollama"},
            "required": {"milvus", "ollama"},
            "one_of": (),
            "check_on_startup": True,
        },
        "bundle_closed": True,
        "dms_check_on_startup": True,
        "dms_closed": True,
        "dms_configs": dms_settings,
    }


def test_docmesh_factory_from_env_closes_bundle_when_dms_assembly_fails(monkeypatch) -> None:
    settings = make_settings()
    dms_settings = SimpleNamespace()
    records = {"bundle_closed": False}
    bundle = SimpleNamespace(
        configs=settings,
        clients={},
        close=lambda: records.update(bundle_closed=True),
    )

    monkeypatch.setattr(
        "rag_system_core.composition.docmesh_runtime.assemble_docmesh_services",
        lambda *, services, required, one_of, check_on_startup: bundle,
    )
    monkeypatch.setattr(
        "rag_system_core.composition.docmesh_runtime.load_dms_settings",
        lambda: dms_settings,
    )

    def fail_dms_assembly(configs, *, check_on_startup):
        assert configs is dms_settings
        del check_on_startup
        raise RuntimeError("dms assembly failed")

    monkeypatch.setattr(
        "rag_system_core.composition.factories.dms.create_sdk_from_service_configs",
        fail_dms_assembly,
    )

    with pytest.raises(RuntimeError, match="dms assembly failed"):
        DocmeshRAGServiceFactory.from_env(check_on_startup=True)

    assert records["bundle_closed"] is True


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

    monkeypatch.setattr(docmesh_py_core, "check_all_services", fake_check_all_services)

    class CheckedEmbedding(FakeEmbeddingClient):
        def check(self) -> None:
            return None

    class CheckedGeneration(FakeGenerationClient):
        def check(self) -> None:
            return None

    class CheckedDocumentStorage(FakeDocumentStorage):
        def check(self) -> None:
            return None

    core = RAGCore(
        embedding_client=CheckedEmbedding(),
        generation_client=CheckedGeneration(),
        vector_store=create_rag_vector_store(),
        metadata_store=MetadataStore(tmp_path / "metadata.db"),
        document_storage=CheckedDocumentStorage("local", tmp_path / "documents"),
        chunker=FixedWindowChunker(chunk_size=512, chunk_overlap=64),
        health_check_runner=run_health_checks,
    )

    assert core.health_check().ok is True
    assert records["services"] == ["dms", "embedding", "generation", "metadata", "milvus"]


def test_vector_store_requires_client_when_milvus_is_not_configured(tmp_path: Path) -> None:
    settings = SimpleNamespace(milvus=None)

    with pytest.raises(RuntimeError, match="Failed to create Milvus service client"):
        create_rag_vector_store(
            settings=settings,
        )