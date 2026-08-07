from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, TypeVar

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


@dataclass(frozen=True, slots=True)
class ConfigIssue:
    """Secret-safe description of one invalid environment setting."""

    service: str
    env_key: str | None
    reason: str


class ConfigError(ValueError):
    """Raised when the selected RAG service configuration is invalid."""

    def __init__(self, message: str, *, issues: tuple[ConfigIssue, ...] = ()) -> None:
        super().__init__(message)
        self.issues = issues
        self.errors = issues
        self.env_keys = tuple(
            dict.fromkeys(issue.env_key for issue in issues if issue.env_key is not None)
        )


class _EnvironmentSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    @field_validator("*", mode="before")
    @classmethod
    def strip_strings(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class CommonConfig(_EnvironmentSettings):
    model_config = SettingsConfigDict(env_prefix="DOCMESH_", extra="ignore", case_sensitive=False)

    env: str = "development"
    security_mode: Literal["development", "production"] | None = None

    @property
    def is_production(self) -> bool:
        if self.security_mode is not None:
            return self.security_mode == "production"
        return self.env.lower() in {"prod", "production"}


class MilvusConfig(_EnvironmentSettings):
    model_config = SettingsConfigDict(env_prefix="MILVUS_", extra="ignore", case_sensitive=False)

    endpoint: str = Field(repr=False)
    token: str | None = Field(default=None, repr=False)
    db_name: str = "default"
    collection: str | None = None
    secure: bool = False
    connect_timeout_seconds: int = Field(default=10, ge=1)
    request_timeout_seconds: int = Field(default=30, ge=1)
    max_retries: int = Field(default=3, ge=0)


class OllamaConfig(_EnvironmentSettings):
    model_config = SettingsConfigDict(env_prefix="OLLAMA_", extra="ignore", case_sensitive=False)

    host: str = Field(repr=False)
    verify_ssl: bool = True
    follow_redirects: bool = True
    generation_model: str | None = None
    embedding_model: str | None = None
    request_timeout_seconds: int = Field(default=120, ge=1)
    max_retries: int = Field(default=2, ge=0)


@dataclass
class ServiceConfigs:
    """Common settings plus the selected optional RAG service settings."""

    common: CommonConfig
    milvus: MilvusConfig | None = None
    ollama: OllamaConfig | None = None

    @property
    def docmesh_env(self) -> str:
        return self.common.env


SettingsT = TypeVar("SettingsT", bound=_EnvironmentSettings)


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
    required: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.required, bool):
            raise ConfigError("Service selection required flag must be boolean")
        object.__setattr__(self, "service", Service.parse(self.service))


@dataclass(frozen=True, slots=True)
class HealthcheckPolicy:
    on_startup: bool = False
    parallel: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.on_startup, bool) or not isinstance(self.parallel, bool):
            raise ConfigError("Healthcheck policy flags must be boolean")


@dataclass(frozen=True, slots=True)
class RuntimePlan:
    services: tuple[ServiceSelection | Service, ...]
    one_of: tuple[tuple[Service, ...], ...] = ()
    healthcheck: HealthcheckPolicy = HealthcheckPolicy()

    def __post_init__(self) -> None:
        if not self.services:
            raise ConfigError("Runtime plan must select at least one service")
        if not isinstance(self.healthcheck, HealthcheckPolicy):
            raise ConfigError("Runtime plan healthcheck must be a HealthcheckPolicy")

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

    @property
    def required_services(self) -> frozenset[Service]:
        return frozenset(selection.service for selection in self.services if selection.required)


def _normalize_requested_services(services: set[str | Service] | None) -> set[str]:
    if services is None:
        return {service.value for service in Service}
    return {Service.parse(service).value for service in services}


def _has_environment_values(settings_cls: type[_EnvironmentSettings], env: Mapping[str, str]) -> bool:
    prefix = str(settings_cls.model_config.get("env_prefix", "")).upper()
    return any(key.upper().startswith(prefix) for key in env)


def _format_validation_error(
    settings_cls: type[_EnvironmentSettings],
    exc: ValidationError,
) -> ConfigError:
    prefix = str(settings_cls.model_config.get("env_prefix", ""))
    service = prefix.rstrip("_").lower() or "common"
    issues: list[ConfigIssue] = []
    messages: list[str] = []
    for error in exc.errors(include_input=False, include_url=False):
        location = error.get("loc", ())
        field_name = location[0] if location else None
        env_key = f"{prefix}{str(field_name).upper()}" if field_name else None
        reason = str(error.get("msg", "Invalid configuration"))
        issue = ConfigIssue(service=service, env_key=env_key, reason=reason)
        issues.append(issue)
        messages.append(f"{env_key}: {reason}" if env_key else reason)
    return ConfigError("\n".join(messages) or "Invalid configuration", issues=tuple(issues))


def _load_settings(settings_cls: type[SettingsT]) -> SettingsT:
    try:
        return settings_cls()
    except ValidationError as exc:
        raise _format_validation_error(settings_cls, exc) from None


def load_service_configs(*, services: set[str | Service] | None = None) -> ServiceConfigs:
    """Load selected RAG settings directly from the process environment."""
    common = _load_settings(CommonConfig)
    selected = _normalize_requested_services(services)
    configs = ServiceConfigs(common=common)
    if Service.MILVUS.value in selected:
        configs.milvus = _load_settings(MilvusConfig)
    if Service.OLLAMA.value in selected:
        configs.ollama = _load_settings(OllamaConfig)
    return configs


def load_available_service_configs(
    *, services: set[str | Service] | None = None
) -> ServiceConfigs:
    """Load only selected services that have at least one environment value."""
    selected = _normalize_requested_services(services)
    available = {
        service
        for service in selected
        if _has_environment_values(
            MilvusConfig if service == Service.MILVUS.value else OllamaConfig,
            os.environ,
        )
    }
    return load_service_configs(services=available)


__all__ = [
    "CommonConfig",
    "ConfigError",
    "ConfigIssue",
    "HealthcheckPolicy",
    "MilvusConfig",
    "OllamaConfig",
    "RuntimePlan",
    "Service",
    "ServiceConfigs",
    "ServiceSelection",
    "load_available_service_configs",
    "load_service_configs",
]
