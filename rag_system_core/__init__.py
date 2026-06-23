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
        OllamaEmbeddingClient,
        OllamaGenerationClient,
    )
    from rag_system_core.composition.bootstrap import bootstrap_rag_core, bootstrap_rag_core_from_docmesh
    from rag_system_core.composition.factories import DocmeshRAGServiceFactory, RAGServiceFactory
    from rag_system_core.domain.core import RAGCore

__all__ = [
    "ChunkRecord",
    "DocumentRecord",
    "EmbeddingClient",
    "GenerationClient",
    "IngestionProgressRecord",
    "IngestResult",
    "OllamaEmbeddingClient",
    "OllamaGenerationClient",
    "QueryResult",
    "RAGCore",
    "bootstrap_rag_core",
    "bootstrap_rag_core_from_docmesh",
    "DocmeshRAGServiceFactory",
    "RAGServiceFactory",
]

_LAZY_EXPORTS = {
    "RAGCore": ("rag_system_core.domain.core", "RAGCore"),
    "OllamaEmbeddingClient": ("rag_system_core.adapters.ollama", "OllamaEmbeddingClient"),
    "OllamaGenerationClient": ("rag_system_core.adapters.ollama", "OllamaGenerationClient"),
    "bootstrap_rag_core": ("rag_system_core.composition.bootstrap", "bootstrap_rag_core"),
    "bootstrap_rag_core_from_docmesh": (
        "rag_system_core.composition.bootstrap",
        "bootstrap_rag_core_from_docmesh",
    ),
    "DocmeshRAGServiceFactory": ("rag_system_core.composition.factories", "DocmeshRAGServiceFactory"),
    "RAGServiceFactory": ("rag_system_core.composition.factories", "RAGServiceFactory"),
}


def __getattr__(name: str):
    if name in _LAZY_EXPORTS:
        module_name, attr_name = _LAZY_EXPORTS[name]
        module = import_module(module_name)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
