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
    from rag_system_core.core import RAGCore
    from rag_system_core.helpers import (
        MilvusSettings,
        OllamaEmbeddingClient,
        OllamaEmbedSettings,
        OllamaGenerationClient,
        OllamaGenerateSettings,
        OllamaSettings,
    )

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
]

_LAZY_EXPORTS = {
    "RAGCore": ("rag_system_core.core", "RAGCore"),
    "MilvusSettings": ("rag_system_core.helpers", "MilvusSettings"),
    "OllamaEmbeddingClient": ("rag_system_core.helpers", "OllamaEmbeddingClient"),
    "OllamaEmbedSettings": ("rag_system_core.helpers", "OllamaEmbedSettings"),
    "OllamaGenerationClient": ("rag_system_core.helpers", "OllamaGenerationClient"),
    "OllamaGenerateSettings": ("rag_system_core.helpers", "OllamaGenerateSettings"),
    "OllamaSettings": ("rag_system_core.helpers", "OllamaSettings"),
}


def __getattr__(name: str):
    if name in _LAZY_EXPORTS:
        module_name, attr_name = _LAZY_EXPORTS[name]
        module = import_module(module_name)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
