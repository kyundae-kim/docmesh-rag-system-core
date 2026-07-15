from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rag_system_core.runtime import docmesh_sdk


@dataclass(slots=True)
class LocalHealthServiceResult:
    service: str
    ok: bool
    error: str | None = None


@dataclass(slots=True)
class LocalHealthCheckResult:
    ok: bool
    services: list[LocalHealthServiceResult]


def run_health_checks(service_checks: dict[str, Any], required_services: set[str] | None = None) -> Any:
    return docmesh_sdk.check_all_services(
        service_checks,
        required_services=required_services,
    )
