from __future__ import annotations

from typing import Protocol

from pymilvus import MilvusClient

from rag_system_core.helpers import ChunkRecord, escape_milvus_string


class VectorStore(Protocol):
    def add(self, chunks: list[ChunkRecord], vectors: list[list[float]]) -> list[str]: ...

    def search(self, *, user_id: str, query_vector: list[float], top_k: int) -> list[ChunkRecord]: ...

    def delete_document(self, doc_id: str) -> None: ...

    def delete_chunks(self, chunk_ids: list[str]) -> None: ...


class MilvusLiteVectorStore:
    def __init__(self, *, uri: str, collection_name: str, timeout: float = 30.0) -> None:
        self.uri = uri
        self.collection_name = collection_name
        self.timeout = timeout
        self._client = MilvusClient(uri=uri, timeout=timeout)

    def add(self, chunks: list[ChunkRecord], vectors: list[list[float]]) -> list[str]:
        if not chunks:
            return []
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        self._ensure_collection(dimension=len(vectors[0]))
        payload = [
            {
                "doc_id": chunk.doc_id,
                "user_id": chunk.user_id,
                "content": chunk.content,
                "metadata": dict(chunk.metadata),
                "embedding": [float(value) for value in vector],
            }
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        result = self._client.insert(self.collection_name, payload, timeout=self.timeout)
        return [str(value) for value in result.get("ids", [])]

    def search(self, *, user_id: str, query_vector: list[float], top_k: int) -> list[ChunkRecord]:
        if top_k <= 0 or not query_vector or not self._client.has_collection(self.collection_name):
            return []
        self._client.load_collection(self.collection_name)
        results = self._client.search(
            self.collection_name,
            data=[query_vector],
            filter=f'user_id == "{escape_milvus_string(user_id)}"',
            limit=top_k,
            output_fields=["chunk_id", "doc_id", "user_id", "content", "metadata"],
            timeout=self.timeout,
        )
        hits = results[0] if results else []
        return [chunk_record_from_milvus_hit(hit) for hit in hits]

    def delete_document(self, doc_id: str) -> None:
        if not self._client.has_collection(self.collection_name):
            return
        self._client.delete(
            self.collection_name,
            filter=f'doc_id == "{escape_milvus_string(doc_id)}"',
            timeout=self.timeout,
        )

    def delete_chunks(self, chunk_ids: list[str]) -> None:
        if not chunk_ids or not self._client.has_collection(self.collection_name):
            return
        self._client.delete(
            self.collection_name,
            ids=[int(chunk_id) for chunk_id in chunk_ids],
            timeout=self.timeout,
        )

    def _ensure_collection(self, *, dimension: int) -> None:
        if self._client.has_collection(self.collection_name):
            return
        self._client.create_collection(
            collection_name=self.collection_name,
            dimension=dimension,
            primary_field_name="chunk_id",
            id_type="int",
            vector_field_name="embedding",
            metric_type="COSINE",
            auto_id=True,
            timeout=self.timeout,
        )


def chunk_record_from_milvus_hit(hit: dict) -> ChunkRecord:
    entity = hit.get("entity", hit)
    return ChunkRecord(
        chunk_id=str(entity["chunk_id"]),
        doc_id=str(entity["doc_id"]),
        user_id=str(entity["user_id"]),
        content=str(entity["content"]),
        metadata=dict(entity.get("metadata") or {}),
    )
