from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from io import BytesIO
import os
from pathlib import Path
from uuid import uuid4

import dms
import pytest
from minio import Minio
from ollama import Client as OllamaClient
from pymilvus import MilvusClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from rag_system_core import (
    DocmeshRAGServiceFactory,
    OllamaEmbeddingClient,
    OllamaGenerationClient,
    RAGCore,
)
from rag_system_core.adapters.chunking import FixedWindowChunker
from rag_system_core.composition.configuration import MilvusConfig, OllamaConfig, ServiceConfigs
from rag_system_core.composition.docmesh_runtime import (
    assemble_docmesh_services,
    build_docmesh_runtime_plan,
)
from rag_system_core.composition.factories import (
    create_rag_embedding_client,
    create_rag_generation_client,
    create_rag_vector_store,
)
from rag_system_core.storage.dms_document_storage import DmsDocumentStorage
from rag_system_core.storage.metadata_store import MetadataStore
from rag_system_core.storage.vector_store import MilvusLiteVectorStore
from test_rag_system_core.support import authenticated_user


POSTGRES_DSN = "postgresql+psycopg://docmesh:password@postgres:5432/docmesh"
MILVUS_URI = "http://milvus:19530"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")


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
        host=OLLAMA_HOST,
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


@contextmanager
def _create_sqlite_client_factory(
    tmp_path: Path,
    *,
    in_memory: bool,
) -> Iterator[_HostClientFactoryResources]:
    storage_prefix = "memory" if in_memory else "file"
    collection_name = f"{storage_prefix}_integration_chunks_{uuid4().hex}"
    if in_memory:
        sqlite_engine_kwargs = {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
        dms_engine = create_engine("sqlite+pysqlite:///:memory:", **sqlite_engine_kwargs)
        metadata_engine = create_engine("sqlite+pysqlite:///:memory:", **sqlite_engine_kwargs)
    else:
        dms_engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'dms.db'}")
        metadata_engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'metadata.db'}")
    ollama_client = OllamaClient(
        host=OLLAMA_HOST,
        timeout=120,
        verify=False,
        follow_redirects=False,
    )
    milvus_path = tmp_path / "milvus.db"
    milvus_client = MilvusClient(
        uri=str(milvus_path),
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


@pytest.mark.integration
def test_file_clients_run_ingestion_and_query_end_to_end(tmp_path: Path) -> None:
    """Exercise Milvus Lite and SQLite file-backed access with remote Ollama/MinIO."""
    user = authenticated_user(f"file-backend-user-{uuid4().hex}")
    doc_id: str | None = None

    with _create_sqlite_client_factory(tmp_path, in_memory=False) as resources:
        core = resources.factory.create_rag_core()
        try:
            source_text = "The file-backed integration document contains the color green."
            question = "Which color does the file-backed document contain?"

            ingested = core.ingest_text(
                user=user,
                text=source_text,
                source="file-backed-integration.txt",
            )
            doc_id = ingested.doc_id
            response = core.query(user=user, question=question, top_k=1)

            assert resources.metadata_engine.dialect.name == "sqlite"
            assert (tmp_path / "dms.db").exists()
            assert (tmp_path / "metadata.db").exists()
            assert (tmp_path / "milvus.db").exists()
            assert response.answer.strip()
            assert source_text in response.prompt
            assert response.context_chunks[0].doc_id == ingested.doc_id
            assert response.context_chunks[0].content == source_text
        finally:
            if doc_id is not None:
                core.delete_document(doc_id, user=user)


@pytest.mark.integration
def test_memory_clients_run_ingestion_and_query_end_to_end(tmp_path: Path) -> None:
    """Exercise Milvus Lite and in-memory SQLite with remote Ollama/MinIO."""
    user = authenticated_user(f"memory-backend-user-{uuid4().hex}")
    doc_id: str | None = None

    with _create_sqlite_client_factory(tmp_path, in_memory=True) as resources:
        core = resources.factory.create_rag_core()
        try:
            source_text = "The in-memory integration document contains the color purple."
            question = "Which color does the in-memory document contain?"

            ingested = core.ingest_text(
                user=user,
                text=source_text,
                source="memory-backed-integration.txt",
            )
            doc_id = ingested.doc_id
            response = core.query(user=user, question=question, top_k=1)

            assert resources.metadata_engine.dialect.name == "sqlite"
            assert resources.metadata_engine.url.database == ":memory:"
            assert not (tmp_path / "dms.db").exists()
            assert not (tmp_path / "metadata.db").exists()
            assert response.answer.strip()
            assert source_text in response.prompt
            assert response.context_chunks[0].doc_id == ingested.doc_id
            assert response.context_chunks[0].content == source_text
        finally:
            if doc_id is not None:
                core.delete_document(doc_id, user=user)


@pytest.mark.integration
def test_host_clients_support_file_stream_and_file_path_ingestion(tmp_path: Path) -> None:
    """Exercise stream and filesystem access paths through the remote services."""
    user = authenticated_user(f"file-integration-user-{uuid4().hex}")
    document_ids: list[str] = []

    with _create_host_client_factory() as resources:
        core = resources.factory.create_rag_core()
        try:
            stream_text = "The stream upload contains the word violet."
            stream_result = core.ingest_file_stream(
                user=user,
                file_stream=BytesIO(stream_text.encode("utf-8")),
                source="stream-upload.txt",
            )
            document_ids.append(stream_result.doc_id)

            path = tmp_path / "path-upload.txt"
            path_text = "The path upload contains the word orange."
            path.write_text(path_text, encoding="utf-8")
            path_result = core.ingest_file_path(user=user, file_path=path)
            document_ids.append(path_result.doc_id)

            assert stream_result.source == "stream-upload.txt"
            assert path_result.source == path.name
            assert {document.doc_id for document in core.list_documents(user=user)} == set(document_ids)

            stream_document = core.get_document(stream_result.doc_id, user=user)
            path_document = core.get_document(path_result.doc_id, user=user)
            assert stream_document is not None
            assert path_document is not None
            assert stream_document.asset_reference == stream_result.doc_id
            assert path_document.asset_reference == path_result.doc_id
            assert core.list_document_chunks(stream_result.doc_id, user=user)[0].content == stream_text
            assert core.list_document_chunks(path_result.doc_id, user=user)[0].content == path_text
        finally:
            for document_id in reversed(document_ids):
                core.delete_document(document_id, user=user)


@pytest.mark.integration
def test_service_bundle_access_path_runs_remote_ingestion_and_query() -> None:
    """Assemble remote clients from ServiceConfigs and use the public factory path."""
    collection_name = f"integration_bundle_chunks_{uuid4().hex}"
    user = authenticated_user(f"bundle-integration-user-{uuid4().hex}")
    settings = ServiceConfigs(
        milvus=MilvusConfig(
            endpoint=MILVUS_URI,
            db_name="default",
            collection=collection_name,
            request_timeout_seconds=120,
        ),
        ollama=OllamaConfig(
            host=OLLAMA_HOST,
            verify_ssl=False,
            follow_redirects=False,
            embedding_model="bge-m3",
            generation_model="llama3.2",
            request_timeout_seconds=120,
        ),
    )
    plan = build_docmesh_runtime_plan(
        services={"milvus", "ollama"},
    )
    bundle = assemble_docmesh_services(plan=plan, settings=settings)
    dms_engine = create_engine(POSTGRES_DSN, pool_pre_ping=True)
    metadata_engine = create_engine(POSTGRES_DSN, pool_pre_ping=True)
    milvus_client = bundle.get_client("milvus")
    document_id: str | None = None

    try:
        embedding_client = create_rag_embedding_client(settings=settings, bundle=bundle)
        generation_client = create_rag_generation_client(settings=settings, bundle=bundle)
        vector_store = create_rag_vector_store(settings=settings, bundle=bundle)
        with DocmeshRAGServiceFactory.from_clients(
            engine=dms_engine,
            metadata_engine=metadata_engine,
            minio_client=Minio(
                "minio:9000",
                access_key="admin",
                secret_key="password",
                secure=False,
            ),
            bucket_name="documents",
            embedding_client=embedding_client,
            generation_client=generation_client,
            vector_store=vector_store,
        ) as factory:
            core = factory.create_rag_core()
            try:
                source_text = "The ServiceBundle path stores a teal integration fact."
                question = "Which color does the ServiceBundle integration fact mention?"

                ingested = core.ingest_text(user=user, text=source_text, source="bundle.txt")
                document_id = ingested.doc_id
                response = core.query(user=user, question=question, top_k=1)

                assert response.answer.strip()
                assert source_text in response.prompt
                assert response.context_chunks[0].doc_id == ingested.doc_id
                assert response.context_chunks[0].content == source_text
            finally:
                if document_id is not None:
                    core.delete_document(document_id, user=user)
    finally:
        if milvus_client.has_collection(collection_name):
            milvus_client.drop_collection(collection_name, timeout=120)
        bundle.close()
        metadata_engine.dispose()
        dms_engine.dispose()


@pytest.mark.integration
def test_ragcore_public_api_covers_ingestion_query_and_document_lifecycle(tmp_path: Path) -> None:
    """Exercise every RAGCore public operation through the assembled services."""
    user = authenticated_user(f"core-public-api-user-{uuid4().hex}")
    other_user = authenticated_user(f"core-public-api-other-user-{uuid4().hex}")
    document_ids: list[str] = []

    with _create_sqlite_client_factory(tmp_path, in_memory=True) as resources:
        core = resources.factory.create_rag_core()
        try:
            assert isinstance(core, RAGCore)

            source_text = "The public API integration document states that the primary color is amber."
            text_result = core.ingest_text(
                user=user,
                text=source_text,
                source="public-api-text.txt",
            )
            document_ids.append(text_result.doc_id)

            question = "Which primary color does the public API integration document state?"
            response = core.query(user=user, question=question, top_k=1)

            assert response.answer.strip()
            assert source_text in response.prompt
            assert len(response.context_chunks) == 1
            assert response.context_chunks[0].doc_id == text_result.doc_id

            stream_result = core.ingest_file_stream(
                user=user,
                file_stream=BytesIO(b"The stream document contains a violet value."),
                source="public-api-stream.txt",
            )
            document_ids.append(stream_result.doc_id)

            path = tmp_path / "public-api-path.txt"
            path.write_text("The path document contains an orange value.", encoding="utf-8")
            path_result = core.ingest_file_path(user=user, file_path=path)
            document_ids.append(path_result.doc_id)

            assert stream_result.source == "public-api-stream.txt"
            assert path_result.source == path.name
            assert {
                document.doc_id for document in core.list_documents(user=user)
            } == set(document_ids)

            stored = core.get_document(text_result.doc_id, user=user)
            assert stored is not None
            assert stored.doc_id == text_result.doc_id
            assert stored.user_id == user.sub
            assert stored.source == "public-api-text.txt"

            chunks = core.list_document_chunks(text_result.doc_id, user=user)
            assert len(chunks) == text_result.chunk_count
            assert all(chunk.doc_id == text_result.doc_id for chunk in chunks)
            assert all(chunk.user_id == user.sub for chunk in chunks)

            progress_rows = core.list_ingestion_progress(
                text_result.doc_id,
                user=user,
                job_id=text_result.job_id,
            )
            assert progress_rows
            assert all(row.doc_id == text_result.doc_id for row in progress_rows)
            assert all(row.job_id == text_result.job_id for row in progress_rows)
            assert any(row.status == "completed" for row in progress_rows)
            assert core.get_ingestion_step_statuses(
                text_result.doc_id,
                user=user,
                job_id=text_result.job_id,
            ) == {
                "load": "completed",
                "preprocess": "completed",
                "chunking": "completed",
                "embedding": "completed",
                "vector_store": "completed",
                "chunk_persistence": "completed",
            }

            assert core.get_document(text_result.doc_id, user=other_user) is None
            assert core.list_document_chunks(text_result.doc_id, user=other_user) == []
            assert core.list_ingestion_progress(text_result.doc_id, user=other_user) == []
            assert core.delete_document(text_result.doc_id, user=other_user) is False
            assert core.get_document(text_result.doc_id, user=user) is not None

            assert core.delete_document(text_result.doc_id, user=user) is True
            assert core.get_document(text_result.doc_id, user=user) is None
            assert core.list_document_chunks(text_result.doc_id, user=user) == []
            assert core.list_ingestion_progress(text_result.doc_id, user=user) == []
            assert text_result.doc_id not in {
                document.doc_id for document in core.list_documents(user=user)
            }
        finally:
            for document_id in reversed(document_ids):
                core.delete_document(document_id, user=user)
