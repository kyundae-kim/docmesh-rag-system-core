from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


def test_composition_package_exports_bootstrap_helper():
    from rag_system_core.composition import bootstrap_rag_core

    assert callable(bootstrap_rag_core)


def test_package_root_exports_bootstrap_helper():
    from rag_system_core import bootstrap_rag_core

    assert callable(bootstrap_rag_core)


def test_package_root_exports_environment_bootstrap_helper():
    from rag_system_core import bootstrap_rag_core_from_env

    assert callable(bootstrap_rag_core_from_env)


def test_bootstrap_rag_core_builds_core_from_service_factory(tmp_path: Path) -> None:
    from rag_system_core.composition.bootstrap import bootstrap_rag_core
    from rag_system_core.storage.metadata_store import MetadataStore
    from rag_system_core.storage.vector_store import MilvusLiteVectorStore
    from test_rag_system_core.support import FakeDocumentStorage, FakeEmbeddingClient, FakeGenerationClient

    records: dict[str, object] = {}
    fake_embedding_client = FakeEmbeddingClient()
    fake_generation_client = FakeGenerationClient()
    fake_vector_store = MilvusLiteVectorStore(collection_name="test", timeout=1.0, client=SimpleNamespace())

    class FakeServiceFactory:
        def create_embedding_client(self):
            records["embedding"] = True
            return fake_embedding_client

        def create_generation_client(self):
            records["generation"] = True
            return fake_generation_client

        def create_vector_store(self):
            return fake_vector_store

        def create_document_storage(self):
            records["document_storage"] = True
            return FakeDocumentStorage("memory", tmp_path / "documents")

        def create_metadata_store(self, *, metadata_path):
            records["metadata_store_path"] = Path(metadata_path)
            return MetadataStore(Path(metadata_path))

        def create_chunker(self, *, chunk_size, chunk_overlap):
            from rag_system_core.adapters.chunking import FixedWindowChunker

            records["chunk_size"] = chunk_size
            records["chunk_overlap"] = chunk_overlap
            return FixedWindowChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    core = bootstrap_rag_core(
        service_factory=FakeServiceFactory(),
        metadata_path=tmp_path / "metadata.db",
        chunk_size=32,
        chunk_overlap=4,
    )

    assert records == {
        "embedding": True,
        "generation": True,
        "metadata_store_path": tmp_path / "metadata.db",
        "document_storage": True,
        "chunk_size": 32,
        "chunk_overlap": 4,
    }
    assert core.embedding_client is fake_embedding_client
    assert core.generation_client is fake_generation_client
    assert core.vector_store is fake_vector_store


def test_bootstrap_rag_core_from_env_owns_factory_lifecycle(monkeypatch, tmp_path: Path) -> None:
    import rag_system_core.composition.bootstrap as bootstrap_module
    from rag_system_core.composition.bootstrap import bootstrap_rag_core_from_env

    records: dict[str, object] = {}
    expected_core = object()

    class FakeFactory:
        @classmethod
        def from_env(cls, *, check_on_startup, parallel_healthchecks):
            records["from_env"] = {
                "check_on_startup": check_on_startup,
                "parallel_healthchecks": parallel_healthchecks,
            }
            return cls()

        def __enter__(self):
            records["entered"] = True
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            records["exited"] = True

    def fake_bootstrap_rag_core(*, service_factory, metadata_path, chunk_size, chunk_overlap):
        records["bootstrap"] = {
            "service_factory": service_factory,
            "metadata_path": metadata_path,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        }
        return expected_core

    monkeypatch.setattr(bootstrap_module, "DocmeshRAGServiceFactory", FakeFactory)
    monkeypatch.setattr(bootstrap_module, "bootstrap_rag_core", fake_bootstrap_rag_core)

    with bootstrap_rag_core_from_env(
        metadata_path=tmp_path / "metadata.db",
        chunk_size=64,
        chunk_overlap=8,
    ) as core:
        assert core is expected_core
        assert records["entered"] is True
        assert "exited" not in records

    assert records["from_env"] == {
        "check_on_startup": True,
        "parallel_healthchecks": True,
    }
    bootstrap_record = records["bootstrap"]
    assert isinstance(bootstrap_record, dict)
    assert bootstrap_record["metadata_path"] == tmp_path / "metadata.db"
    assert bootstrap_record["chunk_size"] == 64
    assert bootstrap_record["chunk_overlap"] == 8
    assert records["exited"] is True
