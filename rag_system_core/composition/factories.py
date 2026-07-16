from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from docmesh_py_core import ServiceBundle, ServiceConfigs

import rag_system_core.composition.docmesh_runtime as docmesh_runtime
from rag_system_core.adapters.chunking import FixedWindowChunker
from rag_system_core.adapters.ollama import OllamaEmbeddingClient, OllamaGenerationClient
from rag_system_core.composition.docmesh_runtime import (
    create_docmesh_service_client,
    load_docmesh_settings,
    read_docmesh_ollama_settings,
    resolve_milvus_runtime_settings,
)
from rag_system_core.storage.document_storage import DocumentStorage
from rag_system_core.storage.metadata_store import MetadataStore
from rag_system_core.storage.vector_store import MilvusLiteVectorStore, VectorStore
from rag_system_core.types import EmbeddingClient, GenerationClient


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


def _resolve_ollama_settings(
    *,
    settings: ServiceConfigs | None,
    bundle: ServiceBundle | None,
    model: str | None,
    client: object | None,
) -> ServiceConfigs | None:
    resolved_settings = _resolve_settings(settings=settings, bundle=bundle)
    if resolved_settings is None and (model is None or client is None):
        return load_docmesh_settings(services={"ollama"})
    return resolved_settings


def _require_ollama_client(
    *,
    settings: ServiceConfigs | None = None,
    bundle: ServiceBundle | None = None,
    client: object | None = None,
) -> object:
    if client is not None:
        return client
    resolved_client = create_docmesh_service_client("ollama", settings=settings, bundle=bundle)
    if resolved_client is None:
        raise RuntimeError("Failed to create Ollama service client")
    return resolved_client


def create_rag_embedding_client(
    *,
    settings: ServiceConfigs | None = None,
    bundle: ServiceBundle | None = None,
    model: str | None = None,
    client: object | None = None,
) -> EmbeddingClient:
    resolved_settings = _resolve_ollama_settings(
        settings=settings,
        bundle=bundle,
        model=model,
        client=client,
    )
    _, configured_model, _, _ = read_docmesh_ollama_settings(resolved_settings)
    resolved_model = configured_model if model is None else model
    return OllamaEmbeddingClient(
        client=_require_ollama_client(settings=resolved_settings, bundle=bundle, client=client),
        model=resolved_model if resolved_model is not None else "",
    )


def create_rag_generation_client(
    *,
    settings: ServiceConfigs | None = None,
    bundle: ServiceBundle | None = None,
    model: str | None = None,
    client: object | None = None,
) -> GenerationClient:
    resolved_settings = _resolve_ollama_settings(
        settings=settings,
        bundle=bundle,
        model=model,
        client=client,
    )
    _, _, configured_model, _ = read_docmesh_ollama_settings(resolved_settings)
    resolved_model = configured_model if model is None else model
    return OllamaGenerationClient(
        client=_require_ollama_client(settings=resolved_settings, bundle=bundle, client=client),
        model=resolved_model if resolved_model is not None else "",
    )


def create_rag_vector_store(
    *,
    metadata_path: str | Path,
    settings: ServiceConfigs | None = None,
    bundle: ServiceBundle | None = None,
    uri: str | None = None,
    collection_name: str | None = None,
    timeout: float | None = None,
    client: object | None = None,
) -> VectorStore:
    fallback_uri = str(Path(metadata_path).with_suffix(".milvus.db"))
    resolved_settings = _resolve_settings(settings=settings, bundle=bundle)
    if resolved_settings is None:
        resolved_settings = load_docmesh_settings(services={"milvus"})
    _, configured_collection_name, configured_timeout = resolve_milvus_runtime_settings(
        fallback_uri=fallback_uri,
        settings=resolved_settings,
    )
    resolved_collection_name = configured_collection_name if collection_name is None else collection_name
    resolved_timeout = configured_timeout if timeout is None else timeout
    if client is None:
        client = create_docmesh_service_client("milvus", settings=resolved_settings, bundle=bundle)
    if client is None:
        raise RuntimeError("Failed to create Milvus service client")
    return MilvusLiteVectorStore(
        collection_name=resolved_collection_name,
        timeout=resolved_timeout,
        client=client,
    )


class RAGServiceFactory(Protocol):
    def create_embedding_client(self) -> EmbeddingClient: ...

    def create_generation_client(self) -> GenerationClient: ...

    def create_vector_store(self, *, metadata_path: str | Path) -> VectorStore: ...

    def create_document_storage(self, *, storage_mode: str, document_storage_dir: str | Path) -> DocumentStorage: ...

    def create_metadata_store(self, *, metadata_path: str | Path) -> MetadataStore: ...

    def create_chunker(self, *, chunk_size: int, chunk_overlap: int) -> FixedWindowChunker: ...


@dataclass(slots=True)
class DocmeshRAGServiceFactory:
    settings: ServiceConfigs
    bundle: ServiceBundle | None = None

    @classmethod
    def from_env(
        cls,
        env: dict[str, str] | None = None,
        *,
        check_on_startup: bool = False,
    ) -> "DocmeshRAGServiceFactory":
        bundle = docmesh_runtime.assemble_docmesh_services(
            env,
            required={"ollama"},
            check_on_startup=check_on_startup,
        )
        return cls(settings=bundle.configs, bundle=bundle)

    def close(self) -> None:
        if self.bundle is not None:
            self.bundle.close()

    def create_embedding_client(self) -> EmbeddingClient:
        return create_rag_embedding_client(settings=self.settings, bundle=self.bundle)

    def create_generation_client(self) -> GenerationClient:
        return create_rag_generation_client(settings=self.settings, bundle=self.bundle)

    def create_vector_store(self, *, metadata_path: str | Path) -> VectorStore:
        return create_rag_vector_store(metadata_path=metadata_path, settings=self.settings, bundle=self.bundle)

    def create_document_storage(self, *, storage_mode: str, document_storage_dir: str | Path) -> DocumentStorage:
        return DocumentStorage(storage_mode, Path(document_storage_dir))

    def create_metadata_store(self, *, metadata_path: str | Path) -> MetadataStore:
        return MetadataStore(Path(metadata_path))

    def create_chunker(self, *, chunk_size: int, chunk_overlap: int) -> FixedWindowChunker:
        return FixedWindowChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
