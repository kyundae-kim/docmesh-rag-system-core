from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

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
from rag_system_core.storage.vector_store import MilvusClient, MilvusLiteVectorStore, VectorStore
from rag_system_core.types import EmbeddingClient, GenerationClient


def _require_ollama_client(*, settings: Any | None = None, bundle: Any | None = None, client: Any | None = None) -> Any:
    if client is not None:
        return client
    resolved_client = create_docmesh_service_client("ollama", settings=settings, bundle=bundle)
    if resolved_client is None:
        raise RuntimeError("Failed to create Ollama service client")
    return resolved_client


def create_rag_embedding_client(
    *,
    settings: Any | None = None,
    bundle: Any | None = None,
    model: str | None = None,
    client: Any | None = None,
):
    resolved_settings = settings
    if resolved_settings is None and bundle is not None:
        resolved_settings = bundle.configs
    if resolved_settings is None and (model is None or client is None):
        resolved_settings = load_docmesh_settings(services={"ollama"})
    _, configured_model, _, _ = read_docmesh_ollama_settings(resolved_settings)
    resolved_model = model or configured_model
    return OllamaEmbeddingClient(
        client=_require_ollama_client(settings=resolved_settings, bundle=bundle, client=client),
        model=resolved_model or "",
    )


def create_rag_generation_client(
    *,
    settings: Any | None = None,
    bundle: Any | None = None,
    model: str | None = None,
    client: Any | None = None,
):
    resolved_settings = settings
    if resolved_settings is None and bundle is not None:
        resolved_settings = bundle.configs
    if resolved_settings is None and (model is None or client is None):
        resolved_settings = load_docmesh_settings(services={"ollama"})
    _, _, configured_model, _ = read_docmesh_ollama_settings(resolved_settings)
    resolved_model = model or configured_model
    return OllamaGenerationClient(
        client=_require_ollama_client(settings=resolved_settings, bundle=bundle, client=client),
        model=resolved_model or "",
    )


def create_rag_vector_store(
    *,
    metadata_path: str | Path,
    settings: Any | None = None,
    bundle: Any | None = None,
    uri: str | None = None,
    collection_name: str | None = None,
    timeout: float | None = None,
    client: Any | None = None,
):
    fallback_uri = str(Path(metadata_path).with_suffix('.milvus.db'))
    resolved_settings = settings
    if resolved_settings is None and bundle is not None:
        resolved_settings = bundle.configs
    if resolved_settings is None:
        resolved_settings = load_docmesh_settings(services={"milvus"})
    configured_uri, configured_collection_name, configured_timeout = resolve_milvus_runtime_settings(
        fallback_uri=fallback_uri,
        settings=resolved_settings,
    )
    resolved_uri = configured_uri if uri is None else uri
    resolved_collection_name = configured_collection_name if collection_name is None else collection_name
    resolved_timeout = configured_timeout if timeout is None else timeout
    if client is None:
        client = create_docmesh_service_client('milvus', settings=resolved_settings, bundle=bundle)
    if client is None:
        client = MilvusClient(
            uri=resolved_uri,
            timeout=resolved_timeout,
        )
    return MilvusLiteVectorStore(
        collection_name=resolved_collection_name,
        timeout=resolved_timeout,
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
    bundle: Any | None = None

    @classmethod
    def from_env(
        cls,
        env: dict[str, str] | None = None,
        *,
        check_on_startup: bool = False,
    ) -> "DocmeshRAGServiceFactory":
        from rag_system_core.composition.docmesh_runtime import assemble_docmesh_services

        bundle = assemble_docmesh_services(
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
        return create_rag_document_storage(storage_mode=storage_mode, document_storage_dir=document_storage_dir)

    def create_metadata_store(self, *, metadata_path: str | Path) -> MetadataStore:
        return create_rag_metadata_store(metadata_path=metadata_path)

    def create_chunker(self, *, chunk_size: int, chunk_overlap: int) -> FixedWindowChunker:
        return create_rag_chunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
