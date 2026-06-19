from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
    import rag_system_core.infrastructure as infrastructure_module

    try:
        return infrastructure_module.check_all_services(service_checks, required_services=required_services)
    except Exception:
        pass

    services: list[LocalHealthServiceResult] = []
    ok = True
    for service_name, check in service_checks.items():
        try:
            check()
            services.append(LocalHealthServiceResult(service=service_name, ok=True, error=None))
        except Exception as exc:
            ok = False
            services.append(LocalHealthServiceResult(service=service_name, ok=False, error=str(exc)))
            if required_services is not None and service_name in required_services:
                break
    return LocalHealthCheckResult(ok=ok, services=services)
