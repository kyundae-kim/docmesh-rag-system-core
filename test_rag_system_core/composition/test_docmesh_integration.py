from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import dms
import pytest

from rag_system_core import RAGCore
from rag_system_core.adapters.chunking import FixedWindowChunker
from rag_system_core.adapters.ollama import OllamaEmbeddingClient, OllamaGenerationClient
from rag_system_core.composition.dms_runtime import load_dms_settings
import rag_system_core.composition.docmesh_runtime as docmesh_runtime
from rag_system_core.composition.docmesh_runtime import (
    assemble_docmesh_services,
    build_docmesh_runtime_plan,
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
from rag_system_core.storage.vector_store import MilvusLiteVectorStore
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
            endpoint="/tmp/docmesh-milvus.db",
            collection="docmesh_chunks",
            request_timeout_seconds=9.5,
        ),
    )


def test_load_docmesh_settings_uses_docmesh_runtime_keyword_only_api(monkeypatch) -> None:
    records: dict[str, object] = {}
    expected_settings = object()

    def fake_load_available_service_configs(*, services):
        records["services"] = services
        return expected_settings

    monkeypatch.setattr(
        docmesh_runtime,
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

    assert settings.minio_endpoint == "dms-minio:9000"
    assert settings.minio_bucket == "dms-documents"
    if service_name == "sqlite":
        assert settings.sqlite_path == "/tmp/dms-prefixed.db"
        assert settings.postgres_host is None
    else:
        assert settings.postgres_host == "dms-postgres"
        assert settings.sqlite_path is None


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


def test_assemble_docmesh_services_uses_runtime_plan_api(monkeypatch) -> None:
    records: dict[str, object] = {}
    expected_settings = make_settings()

    class FakeServiceClient:
        def check(self) -> None:
            return None

    expected_clients = {"milvus": FakeServiceClient(), "ollama": FakeServiceClient()}

    def fake_load_docmesh_settings(*, services):
        records["services"] = services
        return expected_settings

    def fake_create_docmesh_service_client(service_name, *, settings, bundle=None):
        records.setdefault("settings", settings)
        del bundle
        return expected_clients[service_name]

    monkeypatch.setattr(docmesh_runtime, "load_docmesh_settings", fake_load_docmesh_settings)
    monkeypatch.setattr(
        docmesh_runtime,
        "create_docmesh_service_client",
        fake_create_docmesh_service_client,
    )

    plan = build_docmesh_runtime_plan(
        services={"milvus", "ollama"},
        required={"ollama"},
        check_on_startup=True,
        parallel_healthchecks=True,
    )
    bundle = assemble_docmesh_services(plan=plan)

    assert bundle.configs is expected_settings
    assert bundle.clients == expected_clients
    assert records == {"services": {"milvus", "ollama"}, "settings": expected_settings}
    assert plan.required_services == {"ollama"}
    assert plan.healthcheck.on_startup is True
    assert plan.healthcheck.parallel is True


def test_ollama_factories_use_clients_from_service_bundle() -> None:
    settings = make_settings()
    ollama = FakeDocmeshOllamaWrapper()
    bundle = SimpleNamespace(get_client=lambda service: ollama)

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
        docmesh_runtime,
        "load_available_service_configs",
        fake_load_available_service_configs,
    )
    monkeypatch.setattr(
        "rag_system_core.composition.factories.create_docmesh_service_client",
        lambda service_name, *, settings=None, bundle=None: ollama,
    )

    client = create_rag_embedding_client()

    assert client.model == "bge-m3"
    assert records["loads"] == 1


def test_docmesh_factory_context_manager_closes_owned_resources() -> None:
    records: list[str] = []
    factory = DocmeshRAGServiceFactory(
        dms_sdk=SimpleNamespace(close=lambda: records.append("dms")),
        owns_dms_sdk=True,
    )

    with factory as entered:
        assert entered is factory
        assert records == []

    assert records == ["dms"]


def test_ollama_factories_require_models_from_settings() -> None:
    settings = make_settings()
    settings.ollama.embedding_model = ""

    with pytest.raises(ValueError, match="Ollama embed model must be configured"):
        create_rag_embedding_client(
            settings=settings,
            bundle=SimpleNamespace(get_client=lambda service: FakeDocmeshOllamaWrapper()),
        )


def test_rag_core_health_check_uses_docmesh_aggregate(tmp_path: Path) -> None:
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

    result = core.health_check()

    assert result.ok is True
    assert sorted(status.service_name for status in result.services) == [
        "dms",
        "embedding",
        "generation",
        "metadata",
        "milvus",
    ]


def test_vector_store_requires_client_when_milvus_is_not_configured(tmp_path: Path) -> None:
    settings = SimpleNamespace(milvus=None)

    with pytest.raises(RuntimeError, match="Failed to create Milvus service client"):
        create_rag_vector_store(
            settings=settings,
        )


def test_vector_store_explicit_client_values_do_not_load_docmesh_settings(monkeypatch) -> None:
    monkeypatch.setattr(
        "rag_system_core.composition.factories.load_docmesh_settings",
        lambda **kwargs: pytest.fail("explicit vector-store clients must not load DocMesh settings"),
    )
    client = object()

    vector_store = create_rag_vector_store(
        client=client,
        collection_name="direct_chunks",
        timeout=4.0,
    )

    assert vector_store.collection_name == "direct_chunks"
    assert vector_store.timeout == 4.0


def test_create_dms_sdk_from_clients_forwards_host_owned_clients(monkeypatch) -> None:
    from rag_system_core.composition.dms_runtime import create_dms_sdk_from_clients

    engine = object()
    minio_client = object()
    plan = object()
    expected_sdk = object()
    records: dict[str, object] = {}

    def fake_create_sdk_from_clients(*, engine, minio_client, bucket_name, plan):
        records.update(
            engine=engine,
            minio_client=minio_client,
            bucket_name=bucket_name,
            plan=plan,
        )
        return expected_sdk

    monkeypatch.setattr(dms, "create_sdk_from_clients", fake_create_sdk_from_clients)

    sdk = create_dms_sdk_from_clients(
        engine=engine,
        minio_client=minio_client,
        bucket_name="documents",
        plan=plan,
    )

    assert sdk is expected_sdk
    assert records == {
        "engine": engine,
        "minio_client": minio_client,
        "bucket_name": "documents",
        "plan": plan,
    }


def test_docmesh_factory_from_clients_uses_injected_clients_without_runtime_settings(monkeypatch) -> None:
    engine = object()
    minio_client = object()
    embedding_client = object()
    generation_client = object()
    vector_store = object()
    dms_sdk = SimpleNamespace(close=lambda: None)
    records: dict[str, object] = {}

    monkeypatch.setattr(
        "rag_system_core.composition.docmesh_runtime.assemble_docmesh_services",
        lambda **kwargs: pytest.fail("client assembly must not load DocMesh settings"),
    )
    monkeypatch.setattr(
        "rag_system_core.composition.docmesh_runtime.load_docmesh_settings",
        lambda **kwargs: pytest.fail("client assembly must not load DocMesh settings"),
    )
    monkeypatch.setattr(
        "rag_system_core.composition.factories.load_docmesh_settings",
        lambda **kwargs: pytest.fail("client assembly must not load DocMesh settings"),
    )
    monkeypatch.setattr(
        "rag_system_core.composition.factories.dms_runtime.load_dms_settings",
        lambda **kwargs: pytest.fail("client assembly must not load DMS settings"),
    )

    def fake_create_dms_sdk_from_clients(*, engine, minio_client, bucket_name, plan):
        records.update(
            engine=engine,
            minio_client=minio_client,
            bucket_name=bucket_name,
            plan=plan,
        )
        return dms_sdk

    monkeypatch.setattr(
        "rag_system_core.composition.factories.dms_runtime.create_dms_sdk_from_clients",
        fake_create_dms_sdk_from_clients,
    )

    factory = DocmeshRAGServiceFactory.from_clients(
        engine=engine,
        minio_client=minio_client,
        bucket_name="documents",
        embedding_client=embedding_client,
        generation_client=generation_client,
        vector_store=vector_store,
        check_on_startup=True,
    )

    assert not hasattr(factory, "settings")
    assert not hasattr(factory, "bundle")
    assert factory.dms_sdk is dms_sdk
    assert factory.create_embedding_client() is embedding_client
    assert factory.create_generation_client() is generation_client
    assert factory.create_vector_store() is vector_store
    assert records["engine"] is engine
    assert records["minio_client"] is minio_client
    assert records["bucket_name"] == "documents"
    assert records["plan"].check_on_startup is True


def test_docmesh_factory_from_host_clients_builds_rag_adapters_without_runtime_settings(monkeypatch) -> None:
    engine = object()
    minio_client = object()
    ollama_client = object()
    milvus_client = object()
    dms_sdk = SimpleNamespace(close=lambda: None)
    records: dict[str, object] = {}

    monkeypatch.setattr(
        "rag_system_core.composition.docmesh_runtime.assemble_docmesh_services",
        lambda **kwargs: pytest.fail("host-client assembly must not load DocMesh settings"),
    )
    monkeypatch.setattr(
        "rag_system_core.composition.docmesh_runtime.load_docmesh_settings",
        lambda **kwargs: pytest.fail("host-client assembly must not load DocMesh settings"),
    )
    monkeypatch.setattr(
        "rag_system_core.composition.factories.load_docmesh_settings",
        lambda **kwargs: pytest.fail("host-client assembly must not load DocMesh settings"),
    )
    monkeypatch.setattr(
        "rag_system_core.composition.factories.dms_runtime.load_dms_settings",
        lambda **kwargs: pytest.fail("host-client assembly must not load DMS settings"),
    )

    def fake_create_dms_sdk_from_clients(*, engine, minio_client, bucket_name, plan):
        records.update(
            engine=engine,
            minio_client=minio_client,
            bucket_name=bucket_name,
            plan=plan,
        )
        return dms_sdk

    monkeypatch.setattr(
        "rag_system_core.composition.factories.dms_runtime.create_dms_sdk_from_clients",
        fake_create_dms_sdk_from_clients,
    )

    factory = DocmeshRAGServiceFactory.from_host_clients(
        engine=engine,
        minio_client=minio_client,
        bucket_name="documents",
        ollama_client=ollama_client,
        milvus_client=milvus_client,
        embedding_model="bge-m3",
        generation_model="gpt-oss:20b",
        collection_name="host_chunks",
        timeout=4.0,
        check_on_startup=True,
    )

    assert factory.dms_sdk is dms_sdk
    assert factory.owns_dms_sdk is True
    embedding_adapter = factory.create_embedding_client()
    generation_adapter = factory.create_generation_client()
    vector_adapter = factory.create_vector_store()
    assert isinstance(embedding_adapter, OllamaEmbeddingClient)
    assert embedding_adapter.model == "bge-m3"
    assert embedding_adapter._client is ollama_client
    assert isinstance(generation_adapter, OllamaGenerationClient)
    assert generation_adapter.model == "gpt-oss:20b"
    assert generation_adapter._client is ollama_client
    assert isinstance(vector_adapter, MilvusLiteVectorStore)
    assert vector_adapter.collection_name == "host_chunks"
    assert vector_adapter.timeout == 4.0
    assert vector_adapter._client is milvus_client
    assert records["engine"] is engine
    assert records["minio_client"] is minio_client
    assert records["bucket_name"] == "documents"
    assert records["plan"].check_on_startup is True


def test_docmesh_factory_create_rag_core_assembles_core_and_closes_created_metadata_store(
    monkeypatch,
    tmp_path: Path,
) -> None:
    import rag_system_core.composition.factories as factories_module

    records: list[object] = []

    class FakeMetadataStore:
        def __init__(self, path: Path) -> None:
            self.path = path

        def close(self) -> None:
            records.append("metadata")

    dms_sdk = SimpleNamespace(close=lambda: records.append("dms"))
    embedding_client = object()
    generation_client = object()
    vector_store = object()
    monkeypatch.setattr(factories_module, "MetadataStore", FakeMetadataStore)

    factory = DocmeshRAGServiceFactory(
        dms_sdk=dms_sdk,
        owns_dms_sdk=True,
        embedding_client=embedding_client,
        generation_client=generation_client,
        vector_store=vector_store,
    )

    core = factory.create_rag_core(
        metadata_path=tmp_path / "metadata.db",
        chunk_size=64,
        chunk_overlap=8,
    )

    assert core.embedding_client is embedding_client
    assert core.generation_client is generation_client
    assert core.vector_store is vector_store
    assert core.metadata_store.path == tmp_path / "metadata.db"
    assert core.document_storage.sdk is dms_sdk
    assert core.chunker.chunk_size == 64
    assert core.chunker.chunk_overlap == 8
    assert core.health_check_runner is run_health_checks

    factory.close()

    assert records == ["metadata", "dms"]


def test_metadata_store_close_disposes_sqlalchemy_engine(monkeypatch, tmp_path: Path) -> None:
    store = MetadataStore(tmp_path / "metadata.db")
    records: list[str] = []
    monkeypatch.setattr(store.engine, "dispose", lambda: records.append("disposed"))

    store.close()

    assert records == ["disposed"]
