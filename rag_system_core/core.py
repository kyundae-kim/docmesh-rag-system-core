from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import rag_system_core.helpers as helpers_module
import rag_system_core.metadata_store as metadata_store_module
import rag_system_core.vector_store as vector_store_module
from rag_system_core.helpers import (
    ChunkRecord,
    DocumentStorage,
    DocumentRecord,
    EmbeddingClient,
    FixedWindowChunker,
    GenerationClient,
    IngestionProgressRecord,
    IngestResult,
    MilvusSettings,
    OllamaEmbeddingClient,
    OllamaSettings,
    QueryResult,
    resolve_user_id,
)
from rag_system_core.ingestion import IngestionService
from rag_system_core.metadata_store import ChunkModel, DocumentModel, IngestionProgressModel, MetadataStore
from rag_system_core.vector_store import MilvusClient, MilvusLiteVectorStore, VectorStore

ollama = helpers_module.ollama


class RetrievalService:
    def __init__(self, *, embedding_client: EmbeddingClient, vector_store: VectorStore) -> None:
        self.embedding_client = embedding_client
        self.vector_store = vector_store

    def search(self, *, user_id: str, question: str, top_k: int) -> list[ChunkRecord]:
        vector = self.embed_query(question)
        return self.vector_search(user_id=user_id, query_vector=vector, top_k=top_k)

    def embed_query(self, question: str) -> list[float]:
        return self.embedding_client.embed([question])[0]

    def vector_search(self, *, user_id: str, query_vector: list[float], top_k: int) -> list[ChunkRecord]:
        return self.vector_store.search(user_id=user_id, query_vector=query_vector, top_k=top_k)


class GenerationService:
    def __init__(self, generation_client: GenerationClient, system_prompt: str | None = None) -> None:
        self.generation_client = generation_client
        self.system_prompt = system_prompt or (
            "You are a helpful RAG assistant. Answer only from the retrieved context."
        )
        self.last_prompt = ""

    def build_prompt(self, *, question: str, context_chunks: list[ChunkRecord]) -> str:
        context = "\n\n".join(chunk.content for chunk in context_chunks) if context_chunks else "No context retrieved."
        return (
            "[System Prompt]\n"
            f"{self.system_prompt}\n\n"
            "[Retrieved Context]\n"
            f"{context}\n\n"
            "[User Query]\n"
            f"{question}"
        )

    def call_llm(self, prompt: str) -> str:
        self.last_prompt = prompt
        return self.generation_client.generate(prompt)

    def generate(self, *, question: str, context_chunks: list[ChunkRecord]) -> QueryResult:
        prompt = self.build_prompt(question=question, context_chunks=context_chunks)
        answer = self.call_llm(prompt)
        return QueryResult(answer=answer, prompt=prompt, context_chunks=context_chunks)


class RAGCore:
    def __init__(
        self,
        *,
        embedding_client: EmbeddingClient,
        generation_client: GenerationClient,
        metadata_path: str | Path,
        document_storage_dir: str | Path,
        storage_mode: str = "memory",
        chunk_size: int = 512,
        chunk_overlap: int = 64,
    ) -> None:
        self.embedding_client = embedding_client
        metadata_path = Path(metadata_path)
        self.metadata_store = MetadataStore(metadata_path)
        self.document_storage = DocumentStorage(storage_mode, Path(document_storage_dir))
        milvus_settings = MilvusSettings()
        milvus_uri = milvus_settings.uri or str(metadata_path.with_suffix(".milvus.db"))
        self.vector_store = MilvusLiteVectorStore(
            uri=milvus_uri,
            collection_name=milvus_settings.collection_name,
            timeout=milvus_settings.timeout,
        )
        self.ingestor = IngestionService(
            chunker=FixedWindowChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap),
            embedding_client=embedding_client,
            vector_store=self.vector_store,
            metadata_store=self.metadata_store,
            document_storage=self.document_storage,
        )
        self.retriever = RetrievalService(
            embedding_client=embedding_client,
            vector_store=self.vector_store,
        )
        self.generator = GenerationService(generation_client)

    def ingest_text(self, *, text: str, source: str, token: str | None = None) -> IngestResult:
        resolved_user_id = resolve_user_id(token)
        return self.ingestor.ingest_text(user_id=resolved_user_id, text=text, source=source)

    def ingest_file_stream(
        self,
        *,
        file_stream: BinaryIO,
        source: str | None = None,
        token: str | None = None,
    ) -> IngestResult:
        resolved_user_id = resolve_user_id(token)
        if source is None or not source.strip():
            raise ValueError("source is required for stream ingestion")
        return self.ingestor.ingest_file_stream(
            user_id=resolved_user_id,
            file_stream=file_stream,
            source=source,
        )

    def ingest_file_path(
        self,
        *,
        file_path: str | Path,
        token: str | None = None,
        source: str | None = None,
    ) -> IngestResult:
        resolved_user_id = resolve_user_id(token)
        return self.ingestor.ingest_file_path(
            user_id=resolved_user_id,
            file_path=Path(file_path),
            source=source,
        )

    def query(
        self,
        *,
        question: str,
        top_k: int = 3,
        token: str | None = None,
    ) -> QueryResult:
        resolved_user_id = resolve_user_id(token)
        context = self.retriever.search(user_id=resolved_user_id, question=question, top_k=top_k)
        return self.generator.generate(question=question, context_chunks=context)

    def list_documents(self, token: str | None = None) -> list[DocumentRecord]:
        resolved_user_id = resolve_user_id(token)
        return self.metadata_store.list_documents(resolved_user_id)

    def get_document(self, doc_id: str, *, token: str | None = None) -> DocumentRecord | None:
        resolved_user_id = resolve_user_id(token)
        return self.metadata_store.get_document_for_user(doc_id=doc_id, user_id=resolved_user_id)

    def list_document_chunks(self, doc_id: str, *, token: str | None = None) -> list[ChunkRecord]:
        resolved_user_id = resolve_user_id(token)
        return self.metadata_store.list_document_chunks(doc_id=doc_id, user_id=resolved_user_id)

    def list_ingestion_progress(
        self,
        doc_id: str,
        *,
        token: str | None = None,
        job_id: str | None = None,
    ) -> list[IngestionProgressRecord]:
        resolved_user_id = resolve_user_id(token)
        return self.metadata_store.list_ingestion_progress(doc_id=doc_id, user_id=resolved_user_id, job_id=job_id)

    def delete_document(self, doc_id: str, *, token: str | None = None) -> bool:
        resolved_user_id = resolve_user_id(token)
        document = self.metadata_store.get_document_for_user(doc_id=doc_id, user_id=resolved_user_id)
        if document is None:
            return False
        self.vector_store.delete_document(doc_id)
        deleted_document = self.metadata_store.delete_document(doc_id=doc_id, user_id=resolved_user_id)
        if deleted_document is None:
            return False
        self.document_storage.delete(deleted_document)
        return True


__all__ = [
    "ChunkModel",
    "ChunkRecord",
    "DocumentModel",
    "DocumentRecord",
    "DocumentStorage",
    "EmbeddingClient",
    "FixedWindowChunker",
    "GenerationClient",
    "IngestionProgressModel",
    "IngestionProgressRecord",
    "IngestionService",
    "IngestResult",
    "MetadataStore",
    "MilvusClient",
    "MilvusLiteVectorStore",
    "MilvusSettings",
    "OllamaEmbeddingClient",
    "OllamaSettings",
    "QueryResult",
    "RAGCore",
    "RetrievalService",
    "VectorStore",
    "helpers_module",
    "metadata_store_module",
    "ollama",
    "vector_store_module",
]
