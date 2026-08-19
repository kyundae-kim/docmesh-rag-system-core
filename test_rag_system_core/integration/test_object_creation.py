from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from uuid import uuid4

import dms
import pytest
from minio import Minio
from ollama import Client as OllamaClient
from pymilvus import MilvusClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from rag_system_core import (
    DocmeshRAGServiceFactory,
    OllamaEmbeddingClient,
    OllamaGenerationClient,
    RAGCore,
)
from rag_system_core.adapters.chunking import FixedWindowChunker
from rag_system_core.storage.dms_document_storage import DmsDocumentStorage
from rag_system_core.storage.metadata_store import MetadataStore
from rag_system_core.storage.vector_store import MilvusLiteVectorStore
from test_rag_system_core.support import authenticated_user


POSTGRES_DSN = "postgresql+psycopg://docmesh:password@postgres:5432/docmesh"
MILVUS_URI = "http://milvus:19530"


@dataclass(frozen=True, slots=True)
class _HostClientFactoryResources:
    factory: DocmeshRAGServiceFactory
    metadata_engine: Engine
    ollama_client: OllamaClient
    milvus_client: MilvusClient
    collection_name: str


@contextmanager
def _create_host_client_factory() -> Iterator[_HostClientFactoryResources]:
    collection_name = f"integration_chunks_{uuid4().hex}"
    dms_engine = create_engine(POSTGRES_DSN, pool_pre_ping=True)
    metadata_engine = create_engine(POSTGRES_DSN, pool_pre_ping=True)
    ollama_client = OllamaClient(
        host="http://ollama:11434",
        timeout=120,
        verify=False,
        follow_redirects=False,
    )
    milvus_client = MilvusClient(
        uri=MILVUS_URI,
        token="",
        db_name="default",
        timeout=120,
    )

    try:
        with DocmeshRAGServiceFactory.from_host_clients(
            engine=dms_engine,
            metadata_engine=metadata_engine,
            minio_client=Minio(
                "minio:9000",
                access_key="admin",
                secret_key="password",
                secure=False,
            ),
            bucket_name="documents",
            ollama_client=ollama_client,
            milvus_client=milvus_client,
            embedding_model="bge-m3",
            generation_model="llama3.2",
            collection_name=collection_name,
            timeout=float(120),
            check_on_startup=False,
        ) as factory:
            yield _HostClientFactoryResources(
                factory=factory,
                metadata_engine=metadata_engine,
                ollama_client=ollama_client,
                milvus_client=milvus_client,
                collection_name=collection_name,
            )
    finally:
        if milvus_client.has_collection(collection_name):
            milvus_client.drop_collection(collection_name, timeout=120)
        milvus_client.close()
        metadata_engine.dispose()
        dms_engine.dispose()


@pytest.mark.integration
def test_host_clients_create_rag_core_object_graph() -> None:
    """Create the host-owned dependency graph without running RAG operations."""
    with _create_host_client_factory() as resources:
        factory = resources.factory
        core = factory.create_rag_core()

        assert isinstance(factory.dms_sdk, dms.DefaultDocumentManagementSDK)
        assert isinstance(core, RAGCore)
        assert isinstance(core.embedding_client, OllamaEmbeddingClient)
        assert isinstance(core.generation_client, OllamaGenerationClient)
        assert isinstance(core.vector_store, MilvusLiteVectorStore)
        assert isinstance(core.metadata_store, MetadataStore)
        assert isinstance(core.document_storage, DmsDocumentStorage)
        assert isinstance(core.chunker, FixedWindowChunker)
        assert core.metadata_store.engine is resources.metadata_engine
        assert core.metadata_store.engine.dialect.name == "postgresql"
        assert core.embedding_client._client is resources.ollama_client
        assert core.vector_store._client is resources.milvus_client
        assert core.vector_store.collection_name == resources.collection_name
        assert core.document_storage.sdk is factory.dms_sdk


@pytest.mark.integration
def test_host_clients_run_ingestion_and_query_end_to_end() -> None:
    """Exercise DMS, Ollama, Milvus, PostgreSQL, and RAGCore through public APIs."""
    user = authenticated_user(f"integration-user-{uuid4().hex}")
    doc_id: str | None = None

    with _create_host_client_factory() as resources:
        core = resources.factory.create_rag_core()
        try:
            assert isinstance(core, RAGCore)

            source_text = (
                "The integration document states that the primary color is blue "
                "and that the pipeline stores this fact."
            )
            question = "What primary color does the integration document mention?"

            ingested = core.ingest_text(
                user=user,
                text=source_text,
                source="functional-integration.txt",
            )
            doc_id = ingested.doc_id

            assert ingested.user_id == user.sub
            assert ingested.chunk_count == 1
            stored = core.get_document(ingested.doc_id, user=user)
            assert stored is not None
            assert stored.asset_reference == ingested.doc_id
            assert [doc.doc_id for doc in core.list_documents(user=user)] == [ingested.doc_id]

            response = core.query(user=user, question=question, top_k=1)

            assert response.answer.strip()
            assert question in response.prompt
            assert source_text in response.prompt
            assert len(response.context_chunks) == 1
            assert response.context_chunks[0].doc_id == ingested.doc_id
            assert response.context_chunks[0].content == source_text
        finally:
            if doc_id is not None:
                core.delete_document(doc_id, user=user)
