from __future__ import annotations

import os

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


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOCMESH_", env_file=".env", extra="ignore")

    auth_mode: str = "token"


def resolve_user_id(token: str | None) -> str:
    if token is None:
        return "single-user"

    normalized = token.strip()
    if not normalized:
        return "single-user"

    auth_mode = AuthSettings().auth_mode.strip().lower()
    if auth_mode != "keycloak":
        return normalized

    import rag_system_core.infrastructure as infrastructure_module

    settings = infrastructure_module.load_settings()
    auth_service = infrastructure_module.KeycloakAuthService(settings, allowed_algorithms=["RS256"])
    user = auth_service.extract_user_info(normalized)
    subject = getattr(user, "sub", None)
    if subject is not None and str(subject).strip():
        return str(subject)
    preferred_username = getattr(user, "preferred_username", None)
    if preferred_username is not None and str(preferred_username).strip():
        return str(preferred_username)
    raise RuntimeError("Keycloak user info did not include a usable subject")
