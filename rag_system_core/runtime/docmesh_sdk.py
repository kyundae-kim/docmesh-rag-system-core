from __future__ import annotations

from typing import Any

try:
    from docmesh_py_core import (
        KeycloakAuthService,
        ServiceFactoryRegistry,
        Settings,
        check_all_services,
        load_settings,
    )
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


__all__ = [
    "KeycloakAuthService",
    "ServiceFactoryRegistry",
    "Settings",
    "check_all_services",
    "load_settings",
]
