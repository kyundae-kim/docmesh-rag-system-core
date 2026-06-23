from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from rag_system_core.adapters.chunking import FixedWindowChunker
from rag_system_core.adapters.ollama import OllamaEmbeddingClient, OllamaGenerationClient
from rag_system_core.composition.docmesh_runtime import (
    create_docmesh_service_client,
    read_docmesh_ollama_settings,
    resolve_milvus_runtime_settings,
)
from rag_system_core.storage.document_storage import DocumentStorage
from rag_system_core.storage.metadata_store import MetadataStore
from rag_system_core.storage.vector_store import MilvusClient, MilvusLiteVectorStore, VectorStore
from rag_system_core.types import EmbeddingClient, GenerationClient


def _require_ollama_client(*, settings: Any | None = None, registry: Any | None = None, client: Any | None = None) -> Any:
    if client is not None:
        return client
    resolved_client = create_docmesh_service_client("ollama", settings=settings, registry=registry)
    if resolved_client is None:
        raise RuntimeError("Failed to create Ollama service client")
    return resolved_client


def create_rag_embedding_client(*, settings: Any | None = None, registry: Any | None = None, **overrides):
    model = overrides.pop("model", None)
    client = overrides.pop("client", None)
    _, configured_model, _, _ = read_docmesh_ollama_settings(settings)
    resolved_model = model or configured_model
    return OllamaEmbeddingClient(
        client=_require_ollama_client(settings=settings, registry=registry, client=client),
        model=resolved_model or "",
    )


def create_rag_generation_client(*, settings: Any | None = None, registry: Any | None = None, **overrides):
    model = overrides.pop("model", None)
    client = overrides.pop("client", None)
    _, _, configured_model, _ = read_docmesh_ollama_settings(settings)
    resolved_model = model or configured_model
    return OllamaGenerationClient(
        client=_require_ollama_client(settings=settings, registry=registry, client=client),
        model=resolved_model or "",
    )


def create_rag_vector_store(*, metadata_path: str | Path, settings: Any | None = None, registry: Any | None = None, **overrides):
    del registry
    fallback_uri = str(Path(metadata_path).with_suffix('.milvus.db'))
    uri, collection_name, timeout = resolve_milvus_runtime_settings(fallback_uri=fallback_uri, settings=settings)
    client = overrides.pop('client', None)
    if client is None:
        client = create_docmesh_service_client('milvus', settings=settings)
    if client is None:
        client = MilvusClient(
            uri=overrides.get('uri', uri),
            timeout=overrides.get('timeout', timeout),
        )
    return MilvusLiteVectorStore(
        collection_name=overrides.pop('collection_name', collection_name),
        timeout=overrides.pop('timeout', timeout),
        client=client,
    )


def create_rag_document_storage(*, storage_mode: str, document_storage_dir: str | Path):
    return DocumentStorage(storage_mode, Path(document_storage_dir))


def create_rag_metadata_store(*, metadata_path: str | Path):
    return MetadataStore(Path(metadata_path))


def create_rag_chunker(*, chunk_size: int, chunk_overlap: int):
    return FixedWindowChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)


class RAGServiceFactory(Protocol):
    def create_embedding_client(self) -> EmbeddingClient: ...

    def create_generation_client(self) -> GenerationClient: ...

    def create_vector_store(self, *, metadata_path: str | Path) -> VectorStore: ...

    def create_document_storage(self, *, storage_mode: str, document_storage_dir: str | Path) -> DocumentStorage: ...

    def create_metadata_store(self, *, metadata_path: str | Path) -> MetadataStore: ...

    def create_chunker(self, *, chunk_size: int, chunk_overlap: int) -> FixedWindowChunker: ...


@dataclass(slots=True)
class DocmeshRAGServiceFactory:
    settings: Any
    registry: Any | None = None

    def create_embedding_client(self) -> EmbeddingClient:
        return create_rag_embedding_client(settings=self.settings, registry=self.registry)

    def create_generation_client(self) -> GenerationClient:
        return create_rag_generation_client(settings=self.settings, registry=self.registry)

    def create_vector_store(self, *, metadata_path: str | Path) -> VectorStore:
        return create_rag_vector_store(metadata_path=metadata_path, settings=self.settings, registry=self.registry)

    def create_document_storage(self, *, storage_mode: str, document_storage_dir: str | Path) -> DocumentStorage:
        return create_rag_document_storage(storage_mode=storage_mode, document_storage_dir=document_storage_dir)

    def create_metadata_store(self, *, metadata_path: str | Path) -> MetadataStore:
        return create_rag_metadata_store(metadata_path=metadata_path)

    def create_chunker(self, *, chunk_size: int, chunk_overlap: int) -> FixedWindowChunker:
        return create_rag_chunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
