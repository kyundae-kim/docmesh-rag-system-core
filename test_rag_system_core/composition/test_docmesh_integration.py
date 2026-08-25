from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import dms
import pytest

import rag_system_core.composition.service_factory as service_factory_module
from rag_system_core.adapters.ollama import (
    OllamaEmbeddingClient,
    OllamaGenerationClient,
)
from rag_system_core.composition import dms_runtime, docmesh_runtime
from rag_system_core.composition.docmesh_runtime import (
    assemble_docmesh_services,
    build_docmesh_runtime_plan,
)
from rag_system_core.composition.factories import (
    DocmeshRAGServiceFactory,
    create_rag_embedding_client,
    create_rag_generation_client,
    create_rag_vector_store,
)
from rag_system_core.storage.vector_store import MilvusLiteVectorStore
from test_rag_system_core.support import (
    create_metadata_store,
)


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


def test_dms_runtime_does_not_expose_environment_settings_api() -> None:
    assert not hasattr(dms_runtime, "DmsEnvironmentDiagnosis")
    assert not hasattr(dms_runtime, "DmsServiceSettings")
    assert not hasattr(dms_runtime, "load_dms_settings")


def test_assemble_docmesh_services_uses_runtime_plan_api(monkeypatch) -> None:
    records: dict[str, object] = {}
    expected_settings = make_settings()

    class FakeServiceClient:
        pass

    expected_clients = {"milvus": FakeServiceClient(), "ollama": FakeServiceClient()}

    def fake_create_docmesh_service_client(service_name, *, settings, bundle=None):
        records.setdefault("settings", settings)
        del bundle
        return expected_clients[service_name]

    monkeypatch.setattr(
        docmesh_runtime,
        "create_docmesh_service_client",
        fake_create_docmesh_service_client,
    )

    plan = build_docmesh_runtime_plan(
        services={"milvus", "ollama"},
    )
    bundle = assemble_docmesh_services(plan=plan, settings=expected_settings)

    assert bundle.configs is expected_settings
    assert bundle.clients == expected_clients
    assert records == {"settings": expected_settings}


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


def test_direct_ollama_factory_requires_explicit_client() -> None:
    with pytest.raises(RuntimeError, match="Failed to create Ollama service client"):
        create_rag_embedding_client(model="bge-m3")


def test_docmesh_factory_context_manager_does_not_close_dms_sdk() -> None:
    records: list[str] = []
    factory = DocmeshRAGServiceFactory(
        dms_sdk=SimpleNamespace(close=lambda: records.append("dms")),
        owns_dms_sdk=True,
    )

    with factory as entered:
        assert entered is factory
        assert records == []

    assert records == []


def test_ollama_factories_require_models_from_settings() -> None:
    settings = make_settings()
    settings.ollama.embedding_model = ""

    with pytest.raises(ValueError, match="Ollama embed model must be configured"):
        create_rag_embedding_client(
            settings=settings,
            bundle=SimpleNamespace(get_client=lambda service: FakeDocmeshOllamaWrapper()),
        )


def test_vector_store_requires_client_when_milvus_is_not_configured() -> None:
    settings = SimpleNamespace(milvus=None)

    with pytest.raises(RuntimeError, match="Failed to create Milvus service client"):
        create_rag_vector_store(
            settings=settings,
        )


def test_vector_store_uses_explicit_client_values() -> None:
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
    expected_sdk = object()
    records: dict[str, object] = {}

    class FakeDocumentManagementSDKFactory:
        def __init__(self, *, engine, minio_client, bucket_name):
            records.update(
                engine=engine,
                minio_client=minio_client,
                bucket_name=bucket_name,
            )

        def create(self):
            return expected_sdk

    monkeypatch.setattr(
        dms,
        "DocumentManagementSDKFactory",
        FakeDocumentManagementSDKFactory,
    )

    sdk = create_dms_sdk_from_clients(
        engine=engine,
        minio_client=minio_client,
        bucket_name="documents",
    )

    assert sdk is expected_sdk
    assert records == {
        "engine": engine,
        "minio_client": minio_client,
        "bucket_name": "documents",
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

    def fake_create_dms_sdk_from_clients(*, engine, minio_client, bucket_name):
        records.update(
            engine=engine,
            minio_client=minio_client,
            bucket_name=bucket_name,
        )
        return dms_sdk

    monkeypatch.setattr(
        "rag_system_core.composition.service_factory.dms_runtime.create_dms_sdk_from_clients",
        fake_create_dms_sdk_from_clients,
    )

    factory = DocmeshRAGServiceFactory.from_clients(
        engine=engine,
        minio_client=minio_client,
        bucket_name="documents",
        embedding_client=embedding_client,
        generation_client=generation_client,
        vector_store=vector_store,
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


def test_docmesh_factory_from_host_clients_builds_rag_adapters_without_runtime_settings(monkeypatch) -> None:
    engine = object()
    metadata_engine = object()
    minio_client = object()
    ollama_client = object()
    milvus_client = object()
    dms_sdk = SimpleNamespace(close=lambda: None)
    records: dict[str, object] = {}

    monkeypatch.setattr(
        "rag_system_core.composition.docmesh_runtime.assemble_docmesh_services",
        lambda **kwargs: pytest.fail("host-client assembly must not load DocMesh settings"),
    )

    def fake_create_dms_sdk_from_clients(*, engine, minio_client, bucket_name):
        records.update(
            engine=engine,
            minio_client=minio_client,
            bucket_name=bucket_name,
        )
        return dms_sdk

    monkeypatch.setattr(
        "rag_system_core.composition.service_factory.dms_runtime.create_dms_sdk_from_clients",
        fake_create_dms_sdk_from_clients,
    )

    factory = DocmeshRAGServiceFactory.from_host_clients(
        engine=engine,
        metadata_engine=metadata_engine,
        minio_client=minio_client,
        bucket_name="documents",
        ollama_client=ollama_client,
        milvus_client=milvus_client,
        embedding_model="bge-m3",
        generation_model="gpt-oss:20b",
        collection_name="host_chunks",
        timeout=4.0,
    )

    assert factory.dms_sdk is dms_sdk
    assert factory.owns_dms_sdk is False
    assert factory.metadata_engine is metadata_engine
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


def test_docmesh_factory_uses_host_owned_metadata_engine_for_metadata_store(monkeypatch, tmp_path: Path) -> None:
    metadata_engine = object()
    records: list[str] = []

    class FakeMetadataStore:
        def __init__(self, engine) -> None:
            self.engine = engine

        def close(self) -> None:
            records.append("metadata")

    monkeypatch.setattr(service_factory_module, "MetadataStore", FakeMetadataStore)
    factory = DocmeshRAGServiceFactory(
        dms_sdk=SimpleNamespace(close=lambda: records.append("dms")),
        owns_dms_sdk=True,
        embedding_client=object(),
        generation_client=object(),
        vector_store=object(),
        metadata_engine=metadata_engine,
    )

    metadata_store = factory.create_metadata_store()

    assert metadata_store.engine is metadata_engine
    assert not (tmp_path / "metadata.db").exists()

    factory.close()

    assert records == []


def test_docmesh_factory_create_rag_core_uses_host_owned_metadata_engine(
    monkeypatch,
) -> None:
    records: list[object] = []
    metadata_engine = object()

    class FakeMetadataStore:
        def __init__(self, engine) -> None:
            self.engine = engine

        def close(self) -> None:
            records.append("metadata")

    dms_sdk = SimpleNamespace(close=lambda: records.append("dms"))
    embedding_client = object()
    generation_client = object()
    vector_store = object()
    monkeypatch.setattr(service_factory_module, "MetadataStore", FakeMetadataStore)

    factory = DocmeshRAGServiceFactory(
        dms_sdk=dms_sdk,
        owns_dms_sdk=True,
        embedding_client=embedding_client,
        generation_client=generation_client,
        vector_store=vector_store,
        metadata_engine=metadata_engine,
    )

    core = factory.create_rag_core(
        chunk_size=64,
        chunk_overlap=8,
    )

    assert "metadata_path" not in inspect.signature(factory.create_rag_core).parameters
    assert core.embedding_client is embedding_client
    assert core.generation_client is generation_client
    assert core.vector_store is vector_store
    assert core.metadata_store.engine is metadata_engine
    assert core.document_storage.sdk is dms_sdk
    assert core.chunker.chunk_size == 64
    assert core.chunker.chunk_overlap == 8

    factory.close()

    assert records == []


def test_docmesh_factory_create_metadata_store_keeps_path_compatibility(
    monkeypatch,
    tmp_path: Path,
) -> None:
    records: list[str] = []

    class FakeMetadataStore:
        def __init__(self, engine) -> None:
            self.engine = engine

        def close(self) -> None:
            records.append("metadata")

    dms_sdk = SimpleNamespace(close=lambda: records.append("dms"))
    monkeypatch.setattr(service_factory_module, "MetadataStore", FakeMetadataStore)

    factory = DocmeshRAGServiceFactory(dms_sdk=dms_sdk, owns_dms_sdk=True)
    metadata_store = factory.create_metadata_store(metadata_path=tmp_path / "metadata.db")

    assert metadata_store.engine.url.database == str(tmp_path / "metadata.db")

    factory.close()

    assert records == ["metadata"]


def test_metadata_store_close_disposes_sqlalchemy_engine(monkeypatch, tmp_path: Path) -> None:
    store = create_metadata_store(tmp_path)
    records: list[str] = []
    monkeypatch.setattr(store.engine, "dispose", lambda: records.append("disposed"))

    store.close()

    assert records == ["disposed"]
