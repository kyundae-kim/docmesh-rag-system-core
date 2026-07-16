from __future__ import annotations

import rag_system_core.metadata_store as metadata_store_module
import rag_system_core.storage.vector_store as vector_store_module
from rag_system_core.adapters.chunking import FixedWindowChunker
from rag_system_core.adapters.ollama import (
    OllamaEmbeddingClient,
    OllamaGenerationClient,
    ollama,
)
from rag_system_core.domain.core import RAGCore
from rag_system_core.domain.generation import GenerationService
from rag_system_core.domain.ingestion import IngestionService
from rag_system_core.domain.retrieval import RetrievalService
from rag_system_core.storage.document_storage import DocumentStorage
from rag_system_core.storage.metadata_store import ChunkModel, DocumentModel, IngestionProgressModel, MetadataStore
from rag_system_core.storage.vector_store import MilvusClient, MilvusLiteVectorStore, VectorStore
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
    "ChunkModel",
    "ChunkRecord",
    "DocumentModel",
    "DocumentRecord",
    "DocumentStorage",
    "EmbeddingClient",
    "FixedWindowChunker",
    "GenerationClient",
    "GenerationService",
    "IngestionProgressModel",
    "IngestionProgressRecord",
    "IngestionService",
    "IngestResult",
    "MetadataStore",
    "MilvusClient",
    "MilvusLiteVectorStore",
    "OllamaEmbeddingClient",
    "OllamaGenerationClient",
    "QueryResult",
    "RAGCore",
    "RetrievalService",
    "VectorStore",
    "metadata_store_module",
    "ollama",
    "vector_store_module",
]
