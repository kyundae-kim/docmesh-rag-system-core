from __future__ import annotations

from rag_system_core.adapters.ollama import OllamaEmbeddingClient, OllamaGenerationClient
from rag_system_core.composition.docmesh_runtime import (
    ServiceBundle,
    create_docmesh_service_client,
)
from rag_system_core.composition.configuration import OllamaConfig, ServiceConfigs
from rag_system_core.ports import EmbeddingClient, GenerationClient, VectorStore
from rag_system_core.storage.vector_store import MilvusLiteVectorStore


def _resolve_settings(
    *,
    settings: ServiceConfigs | None,
    bundle: ServiceBundle | None,
) -> ServiceConfigs | None:
    if settings is not None:
        return settings
    if bundle is not None:
        return bundle.configs
    return None


def _resolve_ollama(
    *,
    settings: ServiceConfigs | None,
    bundle: ServiceBundle | None,
    client: object | None,
) -> tuple[object, OllamaConfig | None]:
    resolved_settings = _resolve_settings(settings=settings, bundle=bundle)
    if client is None:
        client = create_docmesh_service_client("ollama", settings=resolved_settings, bundle=bundle)
    if client is None:
        raise RuntimeError("Failed to create Ollama service client")
    config = resolved_settings.ollama if resolved_settings is not None else None
    return client, config


def create_rag_embedding_client(
    *,
    settings: ServiceConfigs | None = None,
    bundle: ServiceBundle | None = None,
    model: str | None = None,
    client: object | None = None,
) -> EmbeddingClient:
    resolved_client, config = _resolve_ollama(
        settings=settings,
        bundle=bundle,
        client=client,
    )
    return OllamaEmbeddingClient(
        client=resolved_client,
        model=(config.embedding_model if model is None and config is not None else model) or "",
    )


def create_rag_generation_client(
    *,
    settings: ServiceConfigs | None = None,
    bundle: ServiceBundle | None = None,
    model: str | None = None,
    client: object | None = None,
) -> GenerationClient:
    resolved_client, config = _resolve_ollama(
        settings=settings,
        bundle=bundle,
        client=client,
    )
    return OllamaGenerationClient(
        client=resolved_client,
        model=(config.generation_model if model is None and config is not None else model) or "",
    )


def create_rag_vector_store(
    *,
    settings: ServiceConfigs | None = None,
    bundle: ServiceBundle | None = None,
    collection_name: str | None = None,
    timeout: float | None = None,
    client: object | None = None,
) -> VectorStore:
    resolved_settings = _resolve_settings(settings=settings, bundle=bundle)
    config = resolved_settings.milvus if resolved_settings is not None else None
    configured_collection_name = config.collection if config is not None else None
    configured_timeout = float(config.request_timeout_seconds) if config is not None else None
    resolved_collection_name = collection_name
    if resolved_collection_name is None:
        resolved_collection_name = configured_collection_name if configured_collection_name is not None else "rag_chunks"
    resolved_timeout = timeout
    if resolved_timeout is None:
        resolved_timeout = configured_timeout if configured_timeout is not None else 30.0
    if client is None:
        client = create_docmesh_service_client("milvus", settings=resolved_settings, bundle=bundle)
    if client is None:
        raise RuntimeError("Failed to create Milvus service client")
    return MilvusLiteVectorStore(
        collection_name=resolved_collection_name,
        timeout=resolved_timeout,
        client=client,
    )


__all__ = [
    "create_rag_embedding_client",
    "create_rag_generation_client",
    "create_rag_vector_store",
]
