from __future__ import annotations

from rag_system_core.ports import VectorStore
from rag_system_core.types import ChunkRecord, EmbeddingClient


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
