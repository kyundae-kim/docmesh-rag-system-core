from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest


def test_composition_package_exports_bootstrap_helper():
    from rag_system_core.composition import bootstrap_rag_core_from_docmesh

    assert callable(bootstrap_rag_core_from_docmesh)


def test_package_root_exports_bootstrap_helper():
    from rag_system_core import bootstrap_rag_core_from_docmesh

    assert callable(bootstrap_rag_core_from_docmesh)


def test_bootstrap_rag_core_from_docmesh_uses_docmesh_runtime(monkeypatch, tmp_path: Path) -> None:
    from rag_system_core.composition import bootstrap_rag_core_from_docmesh
    from test_rag_system_core.support import FakeEmbeddingClient, FakeGenerationClient

    records: dict[str, object] = {}
    fake_settings = SimpleNamespace(name="settings")
    fake_registry = SimpleNamespace(name="registry")
    fake_embedding_client = FakeEmbeddingClient()
    fake_generation_client = FakeGenerationClient()

    def fake_load_docmesh_settings(env=None):
        records["env"] = env
        return fake_settings

    def fake_create_service_registry(settings):
        records["registry_settings"] = settings
        return fake_registry

    def fake_create_rag_embedding_client(*, settings, registry):
        records["embedding_settings"] = settings
        records["embedding_registry"] = registry
        return fake_embedding_client

    def fake_create_rag_generation_client(*, settings, registry):
        records["generation_settings"] = settings
        records["generation_registry"] = registry
        return fake_generation_client

    monkeypatch.setattr("rag_system_core.composition.bootstrap.load_docmesh_settings", fake_load_docmesh_settings)
    monkeypatch.setattr("rag_system_core.composition.bootstrap.create_service_registry", fake_create_service_registry)
    monkeypatch.setattr(
        "rag_system_core.composition.bootstrap.create_rag_embedding_client",
        fake_create_rag_embedding_client,
    )
    monkeypatch.setattr(
        "rag_system_core.composition.bootstrap.create_rag_generation_client",
        fake_create_rag_generation_client,
    )

    core = bootstrap_rag_core_from_docmesh(
        metadata_path=tmp_path / "metadata.db",
        document_storage_dir=tmp_path / "documents",
        storage_mode="local",
        chunk_size=32,
        chunk_overlap=4,
    )

    assert records == {
        "env": None,
        "registry_settings": fake_settings,
        "embedding_settings": fake_settings,
        "embedding_registry": fake_registry,
        "generation_settings": fake_settings,
        "generation_registry": fake_registry,
    }
    assert core.embedding_client is fake_embedding_client
    assert core.generation_client is fake_generation_client
