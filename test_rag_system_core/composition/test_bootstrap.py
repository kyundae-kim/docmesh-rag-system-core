from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


def test_composition_package_exports_bootstrap_helper():
    from rag_system_core.composition import bootstrap_rag_core

    assert callable(bootstrap_rag_core)


def test_package_root_exports_bootstrap_helper():
    from rag_system_core import bootstrap_rag_core

    assert callable(bootstrap_rag_core)


def test_bootstrap_rag_core_builds_core_from_service_factory(tmp_path: Path) -> None:
    from rag_system_core.composition.bootstrap import bootstrap_rag_core
    from rag_system_core.storage.document_storage import DocumentStorage
    from rag_system_core.storage.metadata_store import MetadataStore
    from rag_system_core.storage.vector_store import MilvusLiteVectorStore
    from test_rag_system_core.support import FakeEmbeddingClient, FakeGenerationClient

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

        def create_document_storage(self, *, storage_mode, document_storage_dir):
            records["storage_mode"] = storage_mode
            records["document_storage_dir"] = Path(document_storage_dir)
            return DocumentStorage(storage_mode, Path(document_storage_dir))

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
        document_storage_dir=tmp_path / "documents",
        storage_mode="local",
        chunk_size=32,
        chunk_overlap=4,
    )

    assert records == {
        "embedding": True,
        "generation": True,
        "metadata_store_path": tmp_path / "metadata.db",
        "storage_mode": "local",
        "document_storage_dir": tmp_path / "documents",
        "chunk_size": 32,
        "chunk_overlap": 4,
    }
    assert core.embedding_client is fake_embedding_client
    assert core.generation_client is fake_generation_client
    assert core.vector_store is fake_vector_store
