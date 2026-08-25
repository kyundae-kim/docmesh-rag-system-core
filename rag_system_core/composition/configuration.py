from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ConfigError(ValueError):
    """Raised when explicit RAG configuration or a runtime plan is invalid."""


class MilvusConfig(BaseModel):
    """Explicit Milvus client configuration supplied by the host."""

    model_config = ConfigDict(extra="ignore")

    endpoint: str = Field(repr=False)
    token: str | None = Field(default=None, repr=False)
    db_name: str = "default"
    collection: str | None = None
    secure: bool = False
    connect_timeout_seconds: int = Field(default=10, ge=1)
    request_timeout_seconds: int = Field(default=30, ge=1)
    max_retries: int = Field(default=3, ge=0)


class OllamaConfig(BaseModel):
    """Explicit Ollama client configuration supplied by the host."""

    model_config = ConfigDict(extra="ignore")

    host: str = Field(repr=False)
    verify_ssl: bool = True
    follow_redirects: bool = True
    generation_model: str | None = None
    embedding_model: str | None = None
    request_timeout_seconds: int = Field(default=120, ge=1)
    max_retries: int = Field(default=2, ge=0)


@dataclass
class ServiceConfigs:
    """Explicit settings for the selected optional RAG services."""

    milvus: MilvusConfig | None = None
    ollama: OllamaConfig | None = None


class Service(StrEnum):
    MILVUS = "milvus"
    OLLAMA = "ollama"

    @classmethod
    def parse(cls, value: Service | str) -> Service:
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).lower())
        except ValueError as exc:
            raise ConfigError(f"Unsupported RAG service requested: {value}") from exc


@dataclass(frozen=True, slots=True)
class ServiceSelection:
    service: Service

    def __post_init__(self) -> None:
        object.__setattr__(self, "service", Service.parse(self.service))


@dataclass(frozen=True, slots=True)
class RuntimePlan:
    services: tuple[ServiceSelection | Service, ...]
    one_of: tuple[tuple[Service, ...], ...] = ()

    def __post_init__(self) -> None:
        if not self.services:
            raise ConfigError("Runtime plan must select at least one service")
        normalized = tuple(
            item if isinstance(item, ServiceSelection) else ServiceSelection(Service.parse(item))
            for item in self.services
        )
        selected = tuple(item.service for item in normalized)
        if len(set(selected)) != len(selected):
            raise ConfigError("Runtime plan contains a duplicate service selection")

        normalized_alternatives: list[tuple[Service, ...]] = []
        selected_set = frozenset(selected)
        for raw_group in self.one_of:
            if not raw_group:
                raise ConfigError("Service alternative group cannot be empty")
            group = tuple(Service.parse(service) for service in raw_group)
            if not frozenset(group).issubset(selected_set):
                missing = ", ".join(sorted(service.value for service in frozenset(group) - selected_set))
                raise ConfigError(f"Alternative services are not selected: {missing}")
            normalized_alternatives.append(group)

        object.__setattr__(self, "services", normalized)
        object.__setattr__(self, "one_of", tuple(normalized_alternatives))

    @property
    def selected_services(self) -> frozenset[Service]:
        return frozenset(selection.service for selection in self.services)

__all__ = [
    "ConfigError",
    "MilvusConfig",
    "OllamaConfig",
    "RuntimePlan",
    "Service",
    "ServiceConfigs",
    "ServiceSelection",
]
