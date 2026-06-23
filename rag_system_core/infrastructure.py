from __future__ import annotations

from typing import Any

try:
    from docmesh_py_core import KeycloakAuthService, ServiceFactoryRegistry, check_all_services, load_settings, Settings
except ModuleNotFoundError as exc:  # pragma: no cover - exercised in environments without docmesh_py_core
    _DOCMESH_IMPORT_ERROR = exc

    class _MissingDocmeshDependency:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs
            raise ModuleNotFoundError("docmesh_py_core is required for this operation") from _DOCMESH_IMPORT_ERROR

    def _missing_docmesh_function(*args, **kwargs):
        del args, kwargs
        raise ModuleNotFoundError("docmesh_py_core is required for this operation") from _DOCMESH_IMPORT_ERROR

    KeycloakAuthService = _MissingDocmeshDependency
    ServiceFactoryRegistry = _MissingDocmeshDependency
    check_all_services = _missing_docmesh_function
    load_settings = _missing_docmesh_function
    Settings = Any

from rag_system_core.adapters.chunking import FixedWindowChunker
from rag_system_core.composition.auth import AuthSettings, DEFAULT_SINGLE_USER_ID, resolve_user_id
from rag_system_core.composition.docmesh_runtime import (
    load_docmesh_settings,
    read_docmesh_milvus_settings,
    resolve_milvus_runtime_settings,
)
from rag_system_core.composition.health import LocalHealthCheckResult, LocalHealthServiceResult, run_health_checks
from rag_system_core.storage.document_storage import DocumentStorage, extract_doc_id_from_storage_path
from rag_system_core.storage.vector_store import escape_milvus_string


# Compatibility aliases for older imports.
def _load_docmesh_settings(env: dict[str, str] | None = None) -> Settings:
    return load_docmesh_settings(env)


def _read_docmesh_milvus_settings(settings: Settings | None = None) -> tuple[str | None, str | None, float | None]:
    return read_docmesh_milvus_settings(settings)


__all__ = [
    "AuthSettings",
    "DEFAULT_SINGLE_USER_ID",
    "DocumentStorage",
    "FixedWindowChunker",
    "KeycloakAuthService",
    "LocalHealthCheckResult",
    "LocalHealthServiceResult",
    "ServiceFactoryRegistry",
    "Settings",
    "_load_docmesh_settings",
    "_read_docmesh_milvus_settings",
    "check_all_services",
    "escape_milvus_string",
    "extract_doc_id_from_storage_path",
    "load_docmesh_settings",
    "load_settings",
    "read_docmesh_milvus_settings",
    "resolve_milvus_runtime_settings",
    "resolve_user_id",
    "run_health_checks",
]
