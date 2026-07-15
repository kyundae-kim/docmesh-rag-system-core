from __future__ import annotations

from rag_system_core.runtime.docmesh_sdk import (
    ServiceBundle,
    ServiceConfigs,
    assemble_services,
    check_all_services,
    load_available_service_configs,
)

from rag_system_core.adapters.chunking import FixedWindowChunker
from rag_system_core.composition.docmesh_runtime import (
    assemble_docmesh_services,
    load_docmesh_settings,
    read_docmesh_milvus_settings,
    resolve_milvus_runtime_settings,
)
from rag_system_core.composition.health import LocalHealthCheckResult, LocalHealthServiceResult, run_health_checks
from rag_system_core.storage.document_storage import DocumentStorage, extract_doc_id_from_storage_path
from rag_system_core.storage.vector_store import escape_milvus_string


def _load_docmesh_settings(env: dict[str, str] | None = None) -> ServiceConfigs:
    return load_docmesh_settings(env)


def _read_docmesh_milvus_settings(settings: ServiceConfigs | None = None) -> tuple[str | None, str | None, float | None]:
    return read_docmesh_milvus_settings(settings)


__all__ = [
    "DocumentStorage",
    "FixedWindowChunker",
    "LocalHealthCheckResult",
    "LocalHealthServiceResult",
    "ServiceBundle",
    "ServiceConfigs",
    "_load_docmesh_settings",
    "_read_docmesh_milvus_settings",
    "assemble_docmesh_services",
    "assemble_services",
    "check_all_services",
    "escape_milvus_string",
    "extract_doc_id_from_storage_path",
    "load_available_service_configs",
    "load_docmesh_settings",
    "read_docmesh_milvus_settings",
    "resolve_milvus_runtime_settings",
    "run_health_checks",
]