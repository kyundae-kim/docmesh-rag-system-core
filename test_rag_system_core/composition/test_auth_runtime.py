from __future__ import annotations

from types import SimpleNamespace


def test_auth_and_runtime_modules_exist_and_export_expected_symbols():
    from rag_system_core.composition.auth import resolve_user_id
    from rag_system_core.composition.docmesh_runtime import (
        create_service_registry,
        load_docmesh_settings,
        resolve_milvus_runtime_settings,
    )
    from rag_system_core.composition.health import run_health_checks

    assert callable(resolve_user_id)
    assert callable(load_docmesh_settings)
    assert callable(create_service_registry)
    assert callable(resolve_milvus_runtime_settings)
    assert callable(run_health_checks)


def test_resolve_user_id_defaults_to_single_user() -> None:
    from rag_system_core.composition.auth import resolve_user_id

    assert resolve_user_id(None) == "single-user"
    assert resolve_user_id("   ") == "single-user"


def test_resolve_user_id_uses_raw_token_when_keycloak_disabled(monkeypatch) -> None:
    from rag_system_core.composition import auth as auth_module

    monkeypatch.setattr(auth_module, "AuthSettings", lambda: SimpleNamespace(auth_mode="token"))
    assert auth_module.resolve_user_id(" bearer-token ") == "bearer-token"
