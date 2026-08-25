from __future__ import annotations

from dataclasses import dataclass, field

import ollama
from pymilvus import MilvusClient

from rag_system_core.composition.configuration import (
    ConfigError,
    MilvusConfig,
    OllamaConfig,
    RuntimePlan,
    Service,
    ServiceConfigs,
    ServiceSelection,
)

RAG_SERVICES = frozenset({"milvus", "ollama"})


def build_docmesh_runtime_plan(
    *,
    services: set[str | Service] | None = None,
    one_of: tuple[set[str | Service], ...] = (),
) -> RuntimePlan:
    """Build the typed plan consumed by the v0.6 assembly API."""
    selected = tuple(
        Service.parse(service)
        for service in sorted(
            RAG_SERVICES if services is None else {str(service) for service in services}
        )
    )
    alternatives = tuple(
        tuple(Service.parse(service) for service in sorted(group))
        for group in one_of
    )
    return RuntimePlan(
        services=tuple(
            ServiceSelection(service=service)
            for service in selected
        ),
        one_of=alternatives,
    )


@dataclass
class ServiceBundle:
    configs: ServiceConfigs
    clients: dict[str, object]
    selected_services: frozenset[str]
    _closed: bool = field(default=False, init=False, repr=False)

    def get_client(self, service: Service | str) -> object:
        service_name = service.value if isinstance(service, Service) else str(service).lower()
        try:
            return self.clients[service_name]
        except KeyError as exc:
            raise ConfigError(f"Service client is not available: {service_name}") from exc

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
    settings: ServiceConfigs,
) -> ServiceBundle:
    selected_services = frozenset(service.value for service in plan.selected_services)
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
        )
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

    if settings is None:
        return None
    config = getattr(settings, service_name, None)
    if config is None:
        return None
    return _create_service_client(service_name, config)


__all__ = [
    "RAG_SERVICES",
    "ServiceBundle",
    "assemble_docmesh_services",
    "build_docmesh_runtime_plan",
    "create_docmesh_service_client",
]
