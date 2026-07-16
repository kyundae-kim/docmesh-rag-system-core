from __future__ import annotations

import ast
from pathlib import Path


DOMAIN_PATH = Path("rag_system_core/domain")


def test_domain_modules_depend_only_on_domain_ports_and_types() -> None:
    forbidden_prefixes = (
        "rag_system_core.storage",
        "rag_system_core.adapters",
        "rag_system_core.composition",
    )
    violations: list[str] = []

    for path in sorted(DOMAIN_PATH.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                if node.module.startswith(forbidden_prefixes):
                    violations.append(f"{path}:{node.lineno}:{node.module}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(forbidden_prefixes):
                        violations.append(f"{path}:{node.lineno}:{alias.name}")

    assert violations == []
