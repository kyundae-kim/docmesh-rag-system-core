from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import ollama
from pymilvus import MilvusClient

from rag_system_core.composition.configuration import (
    ConfigError,
    HealthcheckPolicy,
    MilvusConfig,
    OllamaConfig,
    RuntimePlan,
    Service,
    ServiceConfigs,
    ServiceSelection,
    load_available_service_configs,
)

from rag_system_core.composition.health import run_health_checks

RAG_SERVICES = frozenset({"milvus", "ollama"})


def load_docmesh_settings(
    *,
    services: set[str | Service] | None = None,
) -> ServiceConfigs:
    return load_available_service_configs(
        services=set(RAG_SERVICES) if services is None else services,
    )


def build_docmesh_runtime_plan(
    *,
    services: set[str | Service] | None = None,
    required: set[str | Service] | None = None,
    one_of: tuple[set[str | Service], ...] = (),
    check_on_startup: bool = False,
    parallel_healthchecks: bool = False,
) -> RuntimePlan:
    """Build the typed plan consumed by the v0.6 assembly API."""
    selected = tuple(
        Service.parse(service)
        for service in sorted(
            RAG_SERVICES if services is None else {str(service) for service in services}
        )
    )
    required_services = {
        Service.parse(service)
        for service in (required or set())
    }
    alternatives = tuple(
        tuple(Service.parse(service) for service in sorted(group))
        for group in one_of
    )
    return RuntimePlan(
        services=tuple(
            ServiceSelection(service=service, required=service in required_services)
            for service in selected
        ),
        one_of=alternatives,
        healthcheck=HealthcheckPolicy(
            on_startup=check_on_startup,
            parallel=parallel_healthchecks,
        ),
    )


@dataclass
class ServiceBundle:
    configs: ServiceConfigs
    clients: dict[str, object]
    selected_services: frozenset[str]
    required_services: frozenset[str] = frozenset()
    _closed: bool = field(default=False, init=False, repr=False)

    def get_client(self, service: Service | str) -> object:
        service_name = service.value if isinstance(service, Service) else str(service).lower()
        try:
            return self.clients[service_name]
        except KeyError as exc:
            raise ConfigError(f"Service client is not available: {service_name}") from exc

    @property
    def checks(self) -> dict[str, Callable[[], None]]:
        checks: dict[str, Callable[[], None]] = {}
        for service_name, client in self.clients.items():
            if hasattr(client, "check"):
                checks[service_name] = getattr(client, "check")
            elif service_name == "ollama" and hasattr(client, "ps"):
                checks[service_name] = getattr(client, "ps")
            elif service_name == "milvus" and hasattr(client, "list_collections"):
                checks[service_name] = getattr(client, "list_collections")
        return checks

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for client in reversed(tuple(self.clients.values())):
            close = getattr(client, "close", None)
            if close is not None:
                close()


def _create_service_client(service_name: str, config: OllamaConfig | MilvusConfig) -> object:
    if service_name == "ollama":
        return ollama.Client(
            host=config.host,
            timeout=config.request_timeout_seconds,
            verify=config.verify_ssl,
            follow_redirects=config.follow_redirects,
        )
    if service_name == "milvus":
        return MilvusClient(
            uri=config.endpoint,
            token=config.token or "",
            db_name=config.db_name,
            timeout=config.request_timeout_seconds,
            secure=config.secure,
        )
    raise ValueError(f"Unsupported RAG service: {service_name}")


def assemble_docmesh_services(
    *,
    plan: RuntimePlan,
) -> ServiceBundle:
    selected_services = frozenset(service.value for service in plan.selected_services)
    settings = load_docmesh_settings(services=set(selected_services))
    clients: dict[str, object] = {}
    bundle: ServiceBundle | None = None
    try:
        for service_name in selected_services:
            client = create_docmesh_service_client(service_name, settings=settings)
            if client is None:
                raise ConfigError(f"Service configuration is not available: {service_name}")
            clients[service_name] = client
        bundle = ServiceBundle(
            configs=settings,
            clients=clients,
            selected_services=selected_services,
            required_services=frozenset(service.value for service in plan.required_services),
        )
        if plan.healthcheck.on_startup:
            result = run_health_checks(
                bundle.checks,
                required_services=set(bundle.required_services),
                parallel=plan.healthcheck.parallel,
            )
            if not result.ok:
                bundle.close()
                raise RuntimeError("DocMesh service startup health check failed")
        return bundle
    except Exception:
        if bundle is not None:
            bundle.close()
        else:
            for client in reversed(tuple(clients.values())):
                close = getattr(client, "close", None)
                if close is not None:
                    close()
        raise


def create_docmesh_service_client(
    service_name: str,
    *,
    settings: ServiceConfigs | None = None,
    bundle: ServiceBundle | None = None,
) -> object | None:
    service_name = Service.parse(service_name).value
    if bundle is not None:
        try:
            return bundle.get_client(service_name)
        except ConfigError:
            return None

    resolved_settings = settings
    if resolved_settings is None:
        resolved_settings = load_docmesh_settings(services={service_name})
    config = getattr(resolved_settings, service_name, None)
    if config is None:
        return None
    if service_name == "ollama":
        return _create_service_client(service_name, config)
    if service_name == "milvus":
        return _create_service_client(service_name, config)
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
        config.endpoint or fallback_uri,
        config.collection or "rag_chunks",
        float(config.request_timeout_seconds) or 30.0,
    )


__all__ = [
    "RAG_SERVICES",
    "ServiceBundle",
    "assemble_docmesh_services",
    "build_docmesh_runtime_plan",
    "create_docmesh_service_client",
    "load_docmesh_settings",
    "resolve_milvus_runtime_settings",
]