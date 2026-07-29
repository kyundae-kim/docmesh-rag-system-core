from __future__ import annotations

import ast
from pathlib import Path
from typing import get_type_hints

import rag_system_core
import rag_system_core.ports as ports_module
import rag_system_core.storage.vector_store as vector_store_module
import rag_system_core.types as types_module


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


def test_protocols_have_one_canonical_owner_in_ports_module() -> None:
    assert ports_module.EmbeddingClient.__module__ == "rag_system_core.ports"
    assert ports_module.GenerationClient.__module__ == "rag_system_core.ports"
    assert types_module.EmbeddingClient is ports_module.EmbeddingClient
    assert types_module.GenerationClient is ports_module.GenerationClient
    assert rag_system_core.EmbeddingClient is ports_module.EmbeddingClient
    assert rag_system_core.GenerationClient is ports_module.GenerationClient
    assert not hasattr(vector_store_module, "VectorStore")


def test_port_annotations_are_runtime_resolvable() -> None:
    assert get_type_hints(ports_module.VectorStore.add)["chunks"] == list[types_module.ChunkRecord]
    assert get_type_hints(ports_module.MetadataRepository.add_document)["document"] is types_module.DocumentRecord
