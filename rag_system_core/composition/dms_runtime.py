from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import replace

import dms
from docmesh_py_core import (
    CommonConfig,
    MinioConfig,
    PostgresConfig,
    ServiceConfigs,
    SqliteConfig,
)
from pydantic_settings import SettingsConfigDict

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


__all__ = ["load_dms_settings"]
