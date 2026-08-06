from __future__ import annotations


def test_removed_bootstrap_helpers_are_absent_from_public_exports():
    import rag_system_core
    import rag_system_core.composition as composition
    import rag_system_core.composition.bootstrap as bootstrap_module

    for name in (
        "bootstrap_rag_core",
        "bootstrap_rag_core_from_env",
        "bootstrap_rag_core_from_clients",
    ):
        assert not hasattr(rag_system_core, name)
        assert not hasattr(composition, name)
        assert not hasattr(bootstrap_module, name)
