from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

from rag_system_core.types import (
    ChunkRecord,
    DocumentRecord,
    EmbeddingClient,
    GenerationClient,
    IngestionProgressRecord,
    IngestResult,
    QueryResult,
)

if TYPE_CHECKING:
    from rag_system_core.adapters.ollama import (
        MilvusSettings,
        OllamaEmbeddingClient,
        OllamaEmbedSettings,
        OllamaGenerationClient,
        OllamaGenerateSettings,
        OllamaSettings,
    )
    from rag_system_core.composition.bootstrap import bootstrap_rag_core_from_docmesh
    from rag_system_core.domain.core import RAGCore

__all__ = [
    "ChunkRecord",
    "DocumentRecord",
    "EmbeddingClient",
    "GenerationClient",
    "IngestionProgressRecord",
    "IngestResult",
    "MilvusSettings",
    "OllamaEmbeddingClient",
    "OllamaEmbedSettings",
    "OllamaGenerationClient",
    "OllamaGenerateSettings",
    "OllamaSettings",
    "QueryResult",
    "RAGCore",
    "bootstrap_rag_core_from_docmesh",
]

_LAZY_EXPORTS = {
    "RAGCore": ("rag_system_core.domain.core", "RAGCore"),
    "MilvusSettings": ("rag_system_core.adapters.ollama", "MilvusSettings"),
    "OllamaEmbeddingClient": ("rag_system_core.adapters.ollama", "OllamaEmbeddingClient"),
    "OllamaEmbedSettings": ("rag_system_core.adapters.ollama", "OllamaEmbedSettings"),
    "OllamaGenerationClient": ("rag_system_core.adapters.ollama", "OllamaGenerationClient"),
    "OllamaGenerateSettings": ("rag_system_core.adapters.ollama", "OllamaGenerateSettings"),
    "OllamaSettings": ("rag_system_core.adapters.ollama", "OllamaSettings"),
    "bootstrap_rag_core_from_docmesh": (
        "rag_system_core.composition.bootstrap",
        "bootstrap_rag_core_from_docmesh",
    ),
}


def __getattr__(name: str):
    if name in _LAZY_EXPORTS:
        module_name, attr_name = _LAZY_EXPORTS[name]
        module = import_module(module_name)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
