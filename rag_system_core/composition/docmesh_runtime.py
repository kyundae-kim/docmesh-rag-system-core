from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import replace

import dms
import docmesh_py_core
from docmesh_py_core import (
    CommonConfig,
    MinioConfig,
    PostgresConfig,
    ServiceBundle,
    ServiceConfigs,
    SqliteConfig,
)
from pydantic_settings import SettingsConfigDict

RAG_SERVICES = {"milvus", "ollama"}

_DMS_SHARED_ENV_PREFIXES = ("DOCMESH_", "POSTGRES_", "SQLITE_", "MINIO_")
_DMS_CONTROL_ENV_KEYS = {"DMS_CONFIGURATION_STRICT", "DMS_METADATA_BACKEND"}


class _DmsCommonConfig(CommonConfig):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, env_prefix="DMS_DOCMESH_")


class _DmsPostgresConfig(PostgresConfig):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, env_prefix="DMS_POSTGRES_")


class _DmsSqliteConfig(SqliteConfig):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, env_prefix="DMS_SQLITE_")


class _DmsMinioConfig(MinioConfig):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False, env_prefix="DMS_MINIO_")


def _canonical_dms_environment(env: Mapping[str, str]) -> dict[str, str]:
    canonical: dict[str, str] = {}
    for key, value in env.items():
        if key in _DMS_CONTROL_ENV_KEYS:
            canonical[key] = value
            continue
        if not key.startswith("DMS_"):
            continue
        unprefixed = key.removeprefix("DMS_")
        if unprefixed.startswith(_DMS_SHARED_ENV_PREFIXES):
            canonical[unprefixed] = value
    return canonical


def _prefix_dms_diagnostic_text(text: str) -> str:
    for prefix in _DMS_SHARED_ENV_PREFIXES:
        text = text.replace(prefix, f"DMS_{prefix}")
    return text


def _prefix_dms_diagnosis(diagnosis: dms.EnvironmentDiagnosis) -> dms.EnvironmentDiagnosis:
    return replace(
        diagnosis,
        missing_required_keys=tuple(
            _prefix_dms_diagnostic_text(key) for key in diagnosis.missing_required_keys
        ),
        unsupported_keys=tuple(_prefix_dms_diagnostic_text(key) for key in diagnosis.unsupported_keys),
        warnings=tuple(_prefix_dms_diagnostic_text(warning) for warning in diagnosis.warnings),
    )


def load_dms_settings() -> ServiceConfigs:
    diagnosis = dms.diagnose_environment(_canonical_dms_environment(os.environ))
    if not diagnosis.valid:
        prefixed_diagnosis = _prefix_dms_diagnosis(diagnosis)
        raise dms.ConfigurationError(
            dms.format_environment_diagnosis(prefixed_diagnosis),
            diagnosis=prefixed_diagnosis,
        )

    postgres = _DmsPostgresConfig() if diagnosis.metadata_backend == "postgresql" else None
    sqlite = _DmsSqliteConfig() if diagnosis.metadata_backend == "sqlite" else None
    return ServiceConfigs(
        common=_DmsCommonConfig(),
        postgres=postgres,
        sqlite=sqlite,
        minio=_DmsMinioConfig(),
    )


def load_docmesh_settings(
    *,
    services: set[str] | None = None,
) -> ServiceConfigs:
    return docmesh_py_core.load_available_service_configs(
        services=RAG_SERVICES if services is None else services,
    )


def assemble_docmesh_services(
    *,
    services: set[str] | None = None,
    required: set[str] | None = None,
    one_of: tuple[set[str], ...] = (),
    check_on_startup: bool = False,
    parallel_healthchecks: bool = False,
) -> ServiceBundle:
    return docmesh_py_core.assemble_services(
        services=RAG_SERVICES if services is None else services,
        required=required,
        one_of=one_of,
        check_on_startup=check_on_startup,
        parallel_healthchecks=parallel_healthchecks,
    )


def create_docmesh_service_client(
    service_name: str,
    *,
    settings: ServiceConfigs | None = None,
    bundle: ServiceBundle | None = None,
) -> object | None:
    if bundle is not None:
        return bundle.clients.get(service_name)

    resolved_settings = settings
    if resolved_settings is None:
        resolved_settings = load_docmesh_settings(services={service_name})
    config = getattr(resolved_settings, service_name, None)
    if config is None:
        return None
    if service_name == "ollama":
        return docmesh_py_core.create_ollama_client(config)
    if service_name == "milvus":
        return docmesh_py_core.create_milvus_client(config)
    raise ValueError(f"Unsupported RAG service: {service_name}")


def read_docmesh_ollama_settings(
    settings: ServiceConfigs | None = None,
) -> tuple[str | None, str | None, str | None, float | None]:
    if settings is None or getattr(settings, "ollama", None) is None:
        return None, None, None, None
    ollama_settings = settings.ollama
    return (
        ollama_settings.host,
        ollama_settings.embedding_model,
        ollama_settings.generation_model,
        float(ollama_settings.request_timeout_seconds),
    )


def read_docmesh_milvus_settings(
    settings: ServiceConfigs | None = None,
) -> tuple[str | None, str | None, float | None]:
    if settings is None or getattr(settings, "milvus", None) is None:
        return None, None, None
    milvus_settings = settings.milvus
    return (
        milvus_settings.uri,
        milvus_settings.collection,
        float(milvus_settings.request_timeout_seconds),
    )


def resolve_milvus_runtime_settings(
    *,
    fallback_uri: str,
    settings: ServiceConfigs | None = None,
) -> tuple[str, str, float]:
    resolved_settings = settings if settings is not None else load_docmesh_settings(services={"milvus"})
    docmesh_uri, docmesh_collection_name, docmesh_timeout = read_docmesh_milvus_settings(resolved_settings)
    return (
        docmesh_uri or fallback_uri,
        docmesh_collection_name or "rag_chunks",
        docmesh_timeout or 30.0,
    )