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
        try:
            return bundle.get_client(service_name)
        except docmesh_py_core.ConfigError:
            return None

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


def resolve_milvus_runtime_settings(
    *,
    fallback_uri: str,
    settings: ServiceConfigs | None = None,
) -> tuple[str, str, float]:
    resolved_settings = settings if settings is not None else load_docmesh_settings(services={"milvus"})
    config = resolved_settings.milvus
    if config is None:
        return fallback_uri, "rag_chunks", 30.0
    return (
        config.uri or fallback_uri,
        config.collection or "rag_chunks",
        float(config.request_timeout_seconds) or 30.0,
    )