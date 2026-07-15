from __future__ import annotations

import os

from rag_system_core.runtime import docmesh_sdk

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError:  # pragma: no cover - exercised in minimal test envs
    class BaseSettings:
        model_config: dict[str, object] = {}

        def __init__(self, **overrides) -> None:
            prefix = str(getattr(self, "model_config", {}).get("env_prefix", ""))
            annotations = getattr(type(self), "__annotations__", {})
            for field_name in annotations:
                if field_name in overrides:
                    value = overrides[field_name]
                else:
                    env_name = f"{prefix}{field_name}".upper()
                    value = os.environ.get(env_name, getattr(type(self), field_name))
                setattr(self, field_name, value)

    def SettingsConfigDict(**kwargs):
        return dict(kwargs)


DEFAULT_SINGLE_USER_ID = "single-user"


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOCMESH_", env_file=".env", extra="ignore")

    auth_mode: str = "token"


def resolve_user_id(token: str | None) -> str:
    if token is None:
        return DEFAULT_SINGLE_USER_ID

    normalized = token.strip()
    if not normalized:
        return DEFAULT_SINGLE_USER_ID

    auth_mode = AuthSettings().auth_mode.strip().lower()
    if auth_mode != "keycloak":
        return normalized

    settings = docmesh_sdk.load_service_configs(os.environ, services={"keycloak"})
    auth_service = docmesh_sdk.KeycloakAuthService(
        settings.require_keycloak(),
        allowed_algorithms=["RS256"],
    )
    user = auth_service.extract_user_info(normalized)
    subject = getattr(user, "sub", None)
    if subject is not None and str(subject).strip():
        return str(subject)
    preferred_username = getattr(user, "preferred_username", None)
    if preferred_username is not None and str(preferred_username).strip():
        return str(preferred_username)
    raise RuntimeError("Keycloak user info did not include a usable subject")
