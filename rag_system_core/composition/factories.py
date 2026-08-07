from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import NoReturn, Protocol, Self

import dms
from minio import Minio as _Minio
from ollama import Client as _OllamaClient
from pymilvus import MilvusClient as _MilvusClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

import rag_system_core.composition.dms_runtime as dms_runtime
from rag_system_core.adapters.chunking import FixedWindowChunker
from rag_system_core.adapters.ollama import OllamaEmbeddingClient, OllamaGenerationClient
from rag_system_core.composition.docmesh_runtime import (
    ServiceBundle,
    create_docmesh_service_client,
    load_docmesh_settings,
)
from rag_system_core.composition.configuration import OllamaConfig, ServiceConfigs
from rag_system_core.composition.health import run_health_checks
from rag_system_core.domain.core import RAGCore
from rag_system_core.ports import (
    Chunker,
    DocumentAssetStorage,
    EmbeddingClient,
    GenerationClient,
    HealthCheckRunner,
    MetadataRepository,
    VectorStore,
)
from rag_system_core.storage.dms_document_storage import DmsDocumentStorage
from rag_system_core.storage.metadata_store import MetadataStore
from rag_system_core.storage.vector_store import MilvusLiteVectorStore


def _create_metadata_engine(metadata_path: str | Path) -> Engine:
    path = Path(metadata_path).expanduser()
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)
        return create_engine(f"sqlite+pysqlite:///{path}")
    return create_engine("sqlite+pysqlite:///:memory:")



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
    if resolved_settings is None and (client is None or collection_name is None or timeout is None):
        resolved_settings = load_docmesh_settings(services={"milvus"})
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


class RAGServiceFactory(Protocol):
    def create_embedding_client(self) -> EmbeddingClient: ...

    def create_generation_client(self) -> GenerationClient: ...

    def create_vector_store(self) -> VectorStore: ...

    def create_document_storage(self) -> DocumentAssetStorage: ...

    def create_metadata_store(self, *, metadata_path: str | Path | None = None) -> MetadataRepository: ...

    def create_chunker(self, *, chunk_size: int, chunk_overlap: int) -> Chunker: ...


@dataclass(slots=True)
class DocmeshRAGServiceFactory:
    dms_sdk: dms.DefaultDocumentManagementSDK
    owns_dms_sdk: bool = False
    embedding_client: EmbeddingClient | None = None
    generation_client: GenerationClient | None = None
    vector_store: VectorStore | None = None
    metadata_engine: Engine | None = None
    _metadata_stores: list[MetadataStore] = field(default_factory=list, init=False, repr=False)
    _closed: bool = field(default=False, init=False, repr=False)

    @classmethod
    def from_clients(
        cls,
        *,
        engine: Engine,
        minio_client: object,
        bucket_name: str,
        embedding_client: EmbeddingClient,
        generation_client: GenerationClient,
        vector_store: VectorStore,
        metadata_engine: Engine | None = None,
        check_on_startup: bool = False,
    ) -> "DocmeshRAGServiceFactory":
        """Assemble RAG services exclusively from host-owned clients."""
        dms_sdk = dms_runtime.create_dms_sdk_from_clients(
            engine=engine,
            minio_client=minio_client,
            bucket_name=bucket_name,
            plan=dms.DmsAssemblyPlan(check_on_startup=check_on_startup),
        )
        return cls(
            dms_sdk=dms_sdk,
            owns_dms_sdk=True,
            embedding_client=embedding_client,
            generation_client=generation_client,
            vector_store=vector_store,
            metadata_engine=metadata_engine,
        )

    @classmethod
    def from_host_clients(
        cls,
        *,
        engine: Engine,
        metadata_engine: Engine,
        minio_client: _Minio,
        bucket_name: str,
        ollama_client: _OllamaClient,
        milvus_client: _MilvusClient,
        embedding_model: str,
        generation_model: str,
        collection_name: str = "rag_chunks",
        timeout: float = 30.0,
        check_on_startup: bool = True,
    ) -> "DocmeshRAGServiceFactory":
        """Assemble RAG services from host-owned transport clients."""
        embedding_client = create_rag_embedding_client(
            client=ollama_client,
            model=embedding_model,
        )
        generation_client = create_rag_generation_client(
            client=ollama_client,
            model=generation_model,
        )
        vector_store = create_rag_vector_store(
            client=milvus_client,
            collection_name=collection_name,
            timeout=timeout,
        )
        return cls.from_clients(
            engine=engine,
            metadata_engine=metadata_engine,
            minio_client=minio_client,
            bucket_name=bucket_name,
            embedding_client=embedding_client,
            generation_client=generation_client,
            vector_store=vector_store,
            check_on_startup=check_on_startup,
        )

    def create_rag_core(
        self,
        *,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        health_check_runner: HealthCheckRunner = run_health_checks,
    ) -> RAGCore:
        """Create an RAGCore from this factory's assembled collaborators."""
        metadata_store = self.create_metadata_store()
        try:
            return RAGCore(
                embedding_client=self.create_embedding_client(),
                generation_client=self.create_generation_client(),
                vector_store=self.create_vector_store(),
                metadata_store=metadata_store,
                document_storage=self.create_document_storage(),
                chunker=self.create_chunker(
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                ),
                health_check_runner=health_check_runner,
            )
        except Exception as exc:
            if metadata_store not in self._metadata_stores:
                raise
            self._metadata_stores.remove(metadata_store)
            try:
                metadata_store.close()
            except Exception as cleanup_error:
                exc.add_note(f"Failed to close metadata store after RAGCore assembly failure: {cleanup_error}")
            raise

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
        if self._closed:
            return
        self._closed = True
        cleanup_errors: list[Exception] = []
        metadata_stores = list(reversed(self._metadata_stores))
        self._metadata_stores.clear()
        for metadata_store in metadata_stores:
            try:
                metadata_store.close()
            except Exception as exc:
                cleanup_errors.append(exc)
        if self.owns_dms_sdk:
            try:
                self.dms_sdk.close()
            except Exception as exc:
                cleanup_errors.append(exc)
        if len(cleanup_errors) == 1:
            raise cleanup_errors[0]
        if cleanup_errors:
            raise ExceptionGroup("Failed to close RAG service resources", cleanup_errors)

    def _raise_missing_client(self, name: str) -> NoReturn:
        raise RuntimeError(f"{name} was not provided")

    def create_embedding_client(self) -> EmbeddingClient:
        return self.embedding_client if self.embedding_client is not None else self._raise_missing_client("Embedding client")

    def create_generation_client(self) -> GenerationClient:
        return self.generation_client if self.generation_client is not None else self._raise_missing_client("Generation client")

    def create_vector_store(self) -> VectorStore:
        return self.vector_store if self.vector_store is not None else self._raise_missing_client("Vector store")

    def create_document_storage(self) -> DmsDocumentStorage:
        return DmsDocumentStorage(self.dms_sdk)

    def create_metadata_store(self, *, metadata_path: str | Path | None = None) -> MetadataStore:
        if self.metadata_engine is not None:
            return MetadataStore(self.metadata_engine)

        if metadata_path is None:
            raise ValueError("metadata_path is required when metadata_engine is not provided")

        engine = _create_metadata_engine(metadata_path)
        try:
            metadata_store = MetadataStore(engine)
        except Exception:
            engine.dispose()
            raise
        self._metadata_stores.append(metadata_store)
        return metadata_store

    def create_chunker(self, *, chunk_size: int, chunk_overlap: int) -> FixedWindowChunker:
        return FixedWindowChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
