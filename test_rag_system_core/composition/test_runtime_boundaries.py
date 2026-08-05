from __future__ import annotations

import ast
from pathlib import Path
from typing import get_type_hints

import rag_system_core.composition.health as health_module


COMPOSITION_PATH = Path("rag_system_core/composition")


def _top_level_definitions(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    return imported


def test_dms_and_rag_runtime_adaptation_have_separate_module_owners() -> None:
    dms_runtime_path = COMPOSITION_PATH / "dms_runtime.py"
    docmesh_runtime_path = COMPOSITION_PATH / "docmesh_runtime.py"

    assert dms_runtime_path.exists()
    assert "load_dms_settings" in _top_level_definitions(dms_runtime_path)
    assert "dms" in _imported_modules(dms_runtime_path)

    assert "load_dms_settings" not in _top_level_definitions(docmesh_runtime_path)
    assert "dms" not in _imported_modules(docmesh_runtime_path)


def test_health_module_exposes_only_the_docmesh_aggregate_boundary() -> None:
    assert not hasattr(health_module, "LocalHealthServiceResult")
    assert not hasattr(health_module, "LocalHealthCheckResult")
    assert get_type_hints(health_module.run_health_checks)["return"] is health_module.HealthCheckResult


def test_active_runtime_has_no_docmesh_py_core_reference() -> None:
    runtime_files = Path("rag_system_core").rglob("*.py")

    references = [
        str(path)
        for path in runtime_files
        if "docmesh_py_core" in path.read_text(encoding="utf-8")
    ]

    assert references == []


def test_active_runtime_has_no_external_docmesh_config_reference() -> None:
    runtime_files = Path("rag_system_core").rglob("*.py")

    references = [
        str(path)
        for path in runtime_files
        if "docmesh_config" in path.read_text(encoding="utf-8")
    ]

    assert references == []