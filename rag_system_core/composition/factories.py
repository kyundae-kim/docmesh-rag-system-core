from __future__ import annotations

from pathlib import Path
from typing import Any

from rag_system_core.adapters.ollama import OllamaEmbeddingClient, OllamaGenerationClient
from rag_system_core.storage.document_storage import DocumentStorage
from rag_system_core.storage.vector_store import MilvusLiteVectorStore
from rag_system_core.composition.docmesh_runtime import create_docmesh_service_client, resolve_milvus_runtime_settings


def create_rag_embedding_client(*, settings: Any | None = None, registry: Any | None = None, **overrides):
    del settings, registry
    return OllamaEmbeddingClient(**overrides)


def create_rag_generation_client(*, settings: Any | None = None, registry: Any | None = None, **overrides):
    del settings, registry
    return OllamaGenerationClient(**overrides)


def create_rag_vector_store(*, metadata_path: str | Path, settings: Any | None = None, registry: Any | None = None, **overrides):
    del registry
    fallback_uri = str(Path(metadata_path).with_suffix('.milvus.db'))
    uri, collection_name, timeout = resolve_milvus_runtime_settings(fallback_uri=fallback_uri, settings=settings)
    client = overrides.pop('client', None)
    if client is None:
        client = create_docmesh_service_client('milvus', settings=settings)
    return MilvusLiteVectorStore(
        uri=overrides.pop('uri', uri),
        collection_name=overrides.pop('collection_name', collection_name),
        timeout=overrides.pop('timeout', timeout),
        client=client,
    )


def create_rag_document_storage(*, storage_mode: str, document_storage_dir: str | Path):
    return DocumentStorage(storage_mode, Path(document_storage_dir))
