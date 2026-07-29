from __future__ import annotations

from collections.abc import Callable

import docmesh_py_core


def run_health_checks(
    service_checks: dict[str, Callable[[], None]],
    required_services: set[str] | None = None,
) -> docmesh_py_core.HealthCheckResult:
    return docmesh_py_core.check_all_services(
        service_checks,
        required_services=required_services,
    )
