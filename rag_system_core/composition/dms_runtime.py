from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

import dms
from sqlalchemy.engine import Engine


@dataclass(frozen=True, slots=True)
class DmsEnvironmentDiagnosis:
    """Secret-safe result produced by the host-owned DMS environment adapter."""

    selected_backend: str | None = None
    missing_required_keys: tuple[str, ...] = ()
    unsupported_keys: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.missing_required_keys and not self.unsupported_keys


@dataclass(frozen=True, slots=True)
class DmsServiceSettings:
    """Host-owned DMS settings parsed from the ``DMS_`` namespace.

    dms-core v0.9 provides the document SDK, not an environment-settings
    model.  Keeping this value object in the host package preserves the
    namespace diagnosis without coupling it to a removed DMS export.
    """

    minio_endpoint: str | None = None
    minio_access_key: str | None = None
    minio_secret_key: str | None = None
    minio_bucket: str | None = None
    minio_secure: bool = False
    sqlite_path: str | None = None
    postgres_host: str | None = None
    postgres_port: int | None = None
    postgres_database: str | None = None
    postgres_user: str | None = None
    postgres_password: str | None = None


def _env_value(env: Mapping[str, str], key: str) -> str | None:
    value = env.get(key)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _env_bool(env: Mapping[str, str], key: str, *, default: bool) -> bool:
    value = _env_value(env, key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _diagnose_environment(env: Mapping[str, str]) -> DmsEnvironmentDiagnosis:
    backend_value = _env_value(env, "DMS_METADATA_BACKEND")
    strict = _env_bool(env, "DMS_CONFIGURATION_STRICT", default=False)
    postgres_keys = (
        "DMS_POSTGRES_HOST",
        "DMS_POSTGRES_DB",
        "DMS_POSTGRES_USER",
        "DMS_POSTGRES_PASSWORD",
    )
    has_postgres_hints = any(_env_value(env, key) is not None for key in postgres_keys)
    has_sqlite_hint = _env_value(env, "DMS_SQLITE_PATH") is not None
    warnings: list[str] = []
    unsupported: list[str] = []

    if backend_value is not None:
        if backend_value not in {"sqlite", "postgresql"}:
            unsupported.append("DMS_METADATA_BACKEND")
            selected_backend = None
        else:
            selected_backend = backend_value
    elif has_postgres_hints and has_sqlite_hint:
        if strict:
            unsupported.append("DMS_METADATA_BACKEND")
            selected_backend = None
        else:
            selected_backend = "postgresql"
            warnings.append("Both DMS PostgreSQL and SQLite settings are present; PostgreSQL was selected")
    elif has_postgres_hints:
        selected_backend = "postgresql"
    elif has_sqlite_hint:
        selected_backend = "sqlite"
    else:
        selected_backend = None

    missing: list[str] = []
    for key in (
        "DMS_MINIO_ENDPOINT",
        "DMS_MINIO_ACCESS_KEY",
        "DMS_MINIO_SECRET_KEY",
        "DMS_MINIO_BUCKET",
    ):
        if _env_value(env, key) is None:
            missing.append(key)

    if selected_backend == "sqlite" and _env_value(env, "DMS_SQLITE_PATH") is None:
        missing.append("DMS_SQLITE_PATH")
    if selected_backend == "postgresql":
        missing.extend(key for key in postgres_keys if _env_value(env, key) is None)
    if selected_backend is None and not unsupported:
        missing.append("DMS_METADATA_BACKEND or DMS_SQLITE_PATH/DMS_POSTGRES_*")

    return DmsEnvironmentDiagnosis(
        selected_backend=selected_backend,
        missing_required_keys=tuple(dict.fromkeys(missing)),
        unsupported_keys=tuple(unsupported),
        warnings=tuple(warnings),
    )


def _format_diagnosis(diagnosis: DmsEnvironmentDiagnosis) -> str:
    parts: list[str] = []
    if diagnosis.missing_required_keys:
        parts.append("Missing required DMS settings: " + ", ".join(diagnosis.missing_required_keys))
    if diagnosis.unsupported_keys:
        parts.append("Unsupported DMS settings: " + ", ".join(diagnosis.unsupported_keys))
    return "; ".join(parts) or "Invalid DMS configuration"


def load_dms_settings(env: Mapping[str, str] | None = None) -> DmsServiceSettings:
    """Load the host-owned, ``DMS_``-prefixed configuration value object."""
    environment = os.environ if env is None else env
    diagnosis = _diagnose_environment(environment)
    if not diagnosis.valid:
        raise dms.ConfigurationError(_format_diagnosis(diagnosis), diagnosis=diagnosis)

    common = {
        "minio_endpoint": _env_value(environment, "DMS_MINIO_ENDPOINT"),
        "minio_access_key": _env_value(environment, "DMS_MINIO_ACCESS_KEY"),
        "minio_secret_key": _env_value(environment, "DMS_MINIO_SECRET_KEY"),
        "minio_bucket": _env_value(environment, "DMS_MINIO_BUCKET"),
        "minio_secure": _env_bool(environment, "DMS_MINIO_SECURE", default=False),
    }
    if diagnosis.selected_backend == "sqlite":
        return DmsServiceSettings(
            **common,
            sqlite_path=_env_value(environment, "DMS_SQLITE_PATH"),
        )
    return DmsServiceSettings(
        **common,
        postgres_host=_env_value(environment, "DMS_POSTGRES_HOST"),
        postgres_port=int(_env_value(environment, "DMS_POSTGRES_PORT") or "5432"),
        postgres_database=_env_value(environment, "DMS_POSTGRES_DB"),
        postgres_user=_env_value(environment, "DMS_POSTGRES_USER"),
        postgres_password=_env_value(environment, "DMS_POSTGRES_PASSWORD"),
    )


def create_dms_sdk_from_clients(
    *,
    engine: Engine,
    minio_client: object,
    bucket_name: str,
) -> dms.DefaultDocumentManagementSDK:
    """Create DMS from host-owned SQLAlchemy and MinIO clients.

    The injected clients remain caller-owned; this helper does not register
    them as SDK-owned resources.
    """
    return dms.DocumentManagementSDKFactory(
        engine=engine,
        minio_client=minio_client,
        bucket_name=bucket_name,
    ).create()


__all__ = [
    "DmsEnvironmentDiagnosis",
    "DmsServiceSettings",
    "create_dms_sdk_from_clients",
    "load_dms_settings",
]
