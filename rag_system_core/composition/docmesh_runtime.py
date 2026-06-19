from __future__ import annotations

import os
from typing import Any


def _infrastructure_module():
    import rag_system_core.infrastructure as infrastructure_module

    return infrastructure_module


def load_docmesh_settings(env: dict[str, str] | None = None) -> Any:
    infrastructure_module = _infrastructure_module()
    return infrastructure_module.load_settings(env or os.environ)


def create_service_registry(settings: Any) -> Any:
    infrastructure_module = _infrastructure_module()
    return infrastructure_module.ServiceFactoryRegistry(settings)


def create_docmesh_service_client(service_name: str, *, settings: Any | None = None, registry: Any | None = None) -> Any | None:
    resolved_settings = settings if settings is not None else load_docmesh_settings()
    resolved_registry = registry if registry is not None else create_service_registry(resolved_settings)
    return resolved_registry.create_client(service_name)


def read_docmesh_ollama_settings(settings: Any | None = None) -> tuple[str | None, str | None, str | None, float | None]:
    resolved_settings = settings if settings is not None else load_docmesh_settings()
    ollama_settings = getattr(resolved_settings, "ollama", None)
    if ollama_settings is None:
        return None, None, None, None

    host = getattr(ollama_settings, "host", None)
    embedding_model = getattr(ollama_settings, "embedding_model", None)
    generation_model = getattr(ollama_settings, "generation_model", None)
    timeout = getattr(ollama_settings, "request_timeout_seconds", None)
    return host, embedding_model, generation_model, float(timeout) if timeout is not None else None


def read_docmesh_milvus_settings(settings: Any | None = None) -> tuple[str | None, str | None, float | None]:
    resolved_settings = settings if settings is not None else load_docmesh_settings()
    milvus_settings = getattr(resolved_settings, "milvus", None)
    if milvus_settings is None:
        return None, None, None

    uri = getattr(milvus_settings, "uri", None)
    collection_name = getattr(milvus_settings, "collection", None) or getattr(
        milvus_settings, "collection_name", None
    )
    timeout = getattr(milvus_settings, "request_timeout_seconds", None)
    if timeout is None:
        timeout = getattr(milvus_settings, "connect_timeout_seconds", None)
    return uri, collection_name, float(timeout) if timeout is not None else None


def resolve_milvus_runtime_settings(*, fallback_uri: str, settings: Any | None = None) -> tuple[str, str, float]:
    from rag_system_core.adapters.ollama import MilvusSettings

    local_settings = MilvusSettings()
    resolved_settings = settings if settings is not None else load_docmesh_settings()
    docmesh_uri, docmesh_collection_name, docmesh_timeout = read_docmesh_milvus_settings(resolved_settings)
    resolved_uri = local_settings.uri or docmesh_uri or fallback_uri
    resolved_collection_name = local_settings.collection_name or docmesh_collection_name or "rag_chunks"
    resolved_timeout = local_settings.timeout if local_settings.timeout is not None else (docmesh_timeout or 30.0)
    return resolved_uri, resolved_collection_name, resolved_timeout
