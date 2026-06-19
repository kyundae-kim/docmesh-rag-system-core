from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag_system_core.composition.auth import resolve_user_id
    from rag_system_core.composition.bootstrap import bootstrap_rag_core_from_docmesh
    from rag_system_core.composition.docmesh_runtime import (
        create_docmesh_service_client,
        create_service_registry,
        load_docmesh_settings,
        resolve_milvus_runtime_settings,
    )
    from rag_system_core.composition.health import run_health_checks

__all__ = [
    "bootstrap_rag_core_from_docmesh",
    "create_docmesh_service_client",
    "create_service_registry",
    "load_docmesh_settings",
    "resolve_milvus_runtime_settings",
    "resolve_user_id",
    "run_health_checks",
]

_LAZY_EXPORTS = {
    "bootstrap_rag_core_from_docmesh": ("rag_system_core.composition.bootstrap", "bootstrap_rag_core_from_docmesh"),
    "create_docmesh_service_client": ("rag_system_core.composition.docmesh_runtime", "create_docmesh_service_client"),
    "create_service_registry": ("rag_system_core.composition.docmesh_runtime", "create_service_registry"),
    "load_docmesh_settings": ("rag_system_core.composition.docmesh_runtime", "load_docmesh_settings"),
    "resolve_milvus_runtime_settings": ("rag_system_core.composition.docmesh_runtime", "resolve_milvus_runtime_settings"),
    "resolve_user_id": ("rag_system_core.composition.auth", "resolve_user_id"),
    "run_health_checks": ("rag_system_core.composition.health", "run_health_checks"),
}


def __getattr__(name: str):
    if name in _LAZY_EXPORTS:
        module_name, attr_name = _LAZY_EXPORTS[name]
        module = import_module(module_name)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
