from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


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
