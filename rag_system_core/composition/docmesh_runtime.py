from __future__ import annotations

import docmesh_py_core
from docmesh_py_core import (
    ServiceBundle,
    ServiceConfigs,
)

RAG_SERVICES = {"milvus", "ollama"}


def load_docmesh_settings(
    *,
    services: set[str] | None = None,
) -> ServiceConfigs:
    return docmesh_py_core.load_available_service_configs(
        services=RAG_SERVICES if services is None else services,
    )


def assemble_docmesh_services(
    *,
    services: set[str] | None = None,
    required: set[str] | None = None,
    one_of: tuple[set[str], ...] = (),
    check_on_startup: bool = False,
    parallel_healthchecks: bool = False,
) -> ServiceBundle:
    return docmesh_py_core.assemble_services(
        services=RAG_SERVICES if services is None else services,
        required=required,
        one_of=one_of,
        check_on_startup=check_on_startup,
        parallel_healthchecks=parallel_healthchecks,
    )


def create_docmesh_service_client(
    service_name: str,
    *,
    settings: ServiceConfigs | None = None,
    bundle: ServiceBundle | None = None,
) -> object | None:
    if bundle is not None:
        return bundle.clients.get(service_name)

    resolved_settings = settings
    if resolved_settings is None:
        resolved_settings = load_docmesh_settings(services={service_name})
    config = getattr(resolved_settings, service_name, None)
    if config is None:
        return None
    if service_name == "ollama":
        return docmesh_py_core.create_ollama_client(config)
    if service_name == "milvus":
        return docmesh_py_core.create_milvus_client(config)
    raise ValueError(f"Unsupported RAG service: {service_name}")


def read_docmesh_ollama_settings(
    settings: ServiceConfigs | None = None,
) -> tuple[str | None, str | None, str | None, float | None]:
    if settings is None or getattr(settings, "ollama", None) is None:
        return None, None, None, None
    ollama_settings = settings.ollama
    return (
        ollama_settings.host,
        ollama_settings.embedding_model,
        ollama_settings.generation_model,
        float(ollama_settings.request_timeout_seconds),
    )


def read_docmesh_milvus_settings(
    settings: ServiceConfigs | None = None,
) -> tuple[str | None, str | None, float | None]:
    if settings is None or getattr(settings, "milvus", None) is None:
        return None, None, None
    milvus_settings = settings.milvus
    return (
        milvus_settings.uri,
        milvus_settings.collection,
        float(milvus_settings.request_timeout_seconds),
    )


def resolve_milvus_runtime_settings(
    *,
    fallback_uri: str,
    settings: ServiceConfigs | None = None,
) -> tuple[str, str, float]:
    resolved_settings = settings if settings is not None else load_docmesh_settings(services={"milvus"})
    docmesh_uri, docmesh_collection_name, docmesh_timeout = read_docmesh_milvus_settings(resolved_settings)
    return (
        docmesh_uri or fallback_uri,
        docmesh_collection_name or "rag_chunks",
        docmesh_timeout or 30.0,
    )