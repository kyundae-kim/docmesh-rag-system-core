from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True, slots=True)
class ServiceHealthStatus:
    service_name: str
    ok: bool
    duration_seconds: float
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "service": self.service_name,
            "ok": self.ok,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class HealthCheckResult:
    ok: bool
    services: list[ServiceHealthStatus]

    def to_dict(self) -> dict[str, object]:
        return {"ok": self.ok, "services": [status.to_dict() for status in self.services]}


def _run_service_check(service_name: str, check: Callable[[], None]) -> ServiceHealthStatus:
    started = perf_counter()
    try:
        check()
    except Exception as exc:
        return ServiceHealthStatus(
            service_name=service_name,
            ok=False,
            duration_seconds=perf_counter() - started,
            error=str(exc),
        )
    return ServiceHealthStatus(
        service_name=service_name,
        ok=True,
        duration_seconds=perf_counter() - started,
    )


def run_health_checks(
    service_checks: Mapping[str, Callable[[], None]],
    required_services: set[str] | None = None,
    *,
    parallel: bool = False,
) -> HealthCheckResult:
    checks = list(service_checks.items())
    if parallel and checks:
        with ThreadPoolExecutor(max_workers=len(checks)) as executor:
            statuses = list(executor.map(lambda item: _run_service_check(*item), checks))
    else:
        statuses = [_run_service_check(service_name, check) for service_name, check in checks]

    required = required_services or set()
    checked_names = {status.service_name for status in statuses}
    missing_required = required - checked_names
    statuses.extend(
        ServiceHealthStatus(
            service_name=service_name,
            ok=False,
            duration_seconds=0.0,
            error="required health check is not configured",
        )
        for service_name in sorted(missing_required)
    )
    return HealthCheckResult(
        ok=not missing_required and all(
            status.ok for status in statuses if status.service_name in required
        ),
        services=statuses,
    )


__all__ = ["HealthCheckResult", "ServiceHealthStatus", "run_health_checks"]
