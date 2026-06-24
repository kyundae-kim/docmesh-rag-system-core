from __future__ import annotations

from rag_system_core.adapters.ollama import (
    OllamaEmbeddingClient,
    OllamaGenerationClient,
)
from rag_system_core.composition.bootstrap import bootstrap_rag_core
from rag_system_core.composition.factories import DocmeshRAGServiceFactory, RAGServiceFactory
from rag_system_core.domain.core import RAGCore
from rag_system_core.types import (
    ChunkRecord,
    DocumentRecord,
    EmbeddingClient,
    GenerationClient,
    IngestionProgressRecord,
    IngestResult,
    QueryResult,
)

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
    "DocmeshRAGServiceFactory",
    "RAGServiceFactory",
]
