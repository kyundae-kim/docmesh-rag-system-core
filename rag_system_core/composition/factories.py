from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Protocol, Self

import dms

import rag_system_core.composition.dms_runtime as dms_runtime
import rag_system_core.composition.docmesh_runtime as docmesh_runtime
from rag_system_core.adapters.chunking import FixedWindowChunker
from rag_system_core.adapters.ollama import OllamaEmbeddingClient, OllamaGenerationClient
from rag_system_core.composition.docmesh_runtime import (
    RAG_SERVICES,
    ServiceBundle,
    build_docmesh_runtime_plan,
    create_docmesh_service_client,
    load_docmesh_settings,
)
from rag_system_core.composition.configuration import OllamaConfig, ServiceConfigs
from rag_system_core.ports import (
    Chunker,
    DocumentAssetStorage,
    EmbeddingClient,
    GenerationClient,
    MetadataRepository,
    VectorStore,
)
from rag_system_core.storage.dms_document_storage import DmsDocumentStorage
from rag_system_core.storage.metadata_store import MetadataStore
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
    model: str | None,
    client: object | None,
) -> tuple[object, OllamaConfig | None]:
    resolved_settings = _resolve_settings(settings=settings, bundle=bundle)
    if resolved_settings is None and (model is None or client is None):
        resolved_settings = load_docmesh_settings(services={"ollama"})
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
        model=model,
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
        model=model,
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
    if resolved_settings is None:
        resolved_settings = load_docmesh_settings(services={"milvus"})
    config = resolved_settings.milvus
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


class RAGServiceFactory(Protocol):
    def create_embedding_client(self) -> EmbeddingClient: ...

    def create_generation_client(self) -> GenerationClient: ...

    def create_vector_store(self) -> VectorStore: ...

    def create_document_storage(self) -> DocumentAssetStorage: ...

    def create_metadata_store(self, *, metadata_path: str | Path) -> MetadataRepository: ...

    def create_chunker(self, *, chunk_size: int, chunk_overlap: int) -> Chunker: ...


@dataclass(slots=True)
class DocmeshRAGServiceFactory:
    settings: ServiceConfigs
    dms_sdk: dms.DefaultDocumentManagementSDK
    bundle: ServiceBundle | None = None
    owns_dms_sdk: bool = False

    @classmethod
    def from_env(
        cls,
        *,
        check_on_startup: bool = False,
        parallel_healthchecks: bool = True,
    ) -> "DocmeshRAGServiceFactory":
        dms_settings = dms_runtime.load_dms_settings()
        plan = build_docmesh_runtime_plan(
            services=RAG_SERVICES,
            required=RAG_SERVICES,
            one_of=(),
            check_on_startup=check_on_startup,
            parallel_healthchecks=parallel_healthchecks,
        )
        bundle = docmesh_runtime.assemble_docmesh_services(plan=plan)
        try:
            dms_sdk = dms_runtime.create_dms_sdk(
                dms_settings,
                check_on_startup=check_on_startup,
            )
        except Exception:
            bundle.close()
            raise
        return cls(
            settings=bundle.configs,
            dms_sdk=dms_sdk,
            bundle=bundle,
            owns_dms_sdk=True,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc_value, traceback
        self.close()

    def close(self) -> None:
        try:
            if self.owns_dms_sdk:
                self.dms_sdk.close()
        finally:
            if self.bundle is not None:
                self.bundle.close()

    def create_embedding_client(self) -> EmbeddingClient:
        return create_rag_embedding_client(settings=self.settings, bundle=self.bundle)

    def create_generation_client(self) -> GenerationClient:
        return create_rag_generation_client(settings=self.settings, bundle=self.bundle)

    def create_vector_store(self) -> VectorStore:
        return create_rag_vector_store(settings=self.settings, bundle=self.bundle)

    def create_document_storage(self) -> DmsDocumentStorage:
        return DmsDocumentStorage(self.dms_sdk)

    def create_metadata_store(self, *, metadata_path: str | Path) -> MetadataStore:
        return MetadataStore(Path(metadata_path))

    def create_chunker(self, *, chunk_size: int, chunk_overlap: int) -> FixedWindowChunker:
        return FixedWindowChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
