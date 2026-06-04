from __future__ import annotations

import json
import math
from io import BytesIO
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import uuid4


DEFAULT_SINGLE_USER_ID = "single-user"


class EmbeddingClient(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class GenerationClient(Protocol):
    def generate(self, prompt: str) -> str: ...


@dataclass(slots=True)
class DocumentRecord:
    doc_id: str
    user_id: str
    source: str
    created_at: str
    storage_path: str | None = None


@dataclass(slots=True)
class ChunkRecord:
    chunk_id: str
    doc_id: str
    user_id: str
    content: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class IngestResult:
    doc_id: str
    user_id: str
    source: str
    created_at: str
    chunk_count: int


@dataclass(slots=True)
class QueryResult:
    answer: str
    prompt: str
    context_chunks: list[ChunkRecord]


class MetadataStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._documents: dict[str, DocumentRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self._documents = {
            item["doc_id"]: DocumentRecord(**item)
            for item in raw.get("documents", [])
        }

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "documents": [asdict(record) for record in self._documents.values()],
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add_document(self, document: DocumentRecord) -> None:
        self._documents[document.doc_id] = document
        self._save()

    def get_document(self, doc_id: str) -> DocumentRecord | None:
        return self._documents.get(doc_id)

    def list_documents(self, user_id: str) -> list[DocumentRecord]:
        return sorted(
            (doc for doc in self._documents.values() if doc.user_id == user_id),
            key=lambda doc: doc.created_at,
        )


class DocumentStorage:
    def __init__(self, mode: str, base_dir: Path) -> None:
        if mode not in {"memory", "local"}:
            raise ValueError("storage_mode must be 'memory' or 'local'")
        self.mode = mode
        self.base_dir = base_dir
        self._memory_documents: dict[str, str] = {}

    def store_text(self, *, doc_id: str, text: str, source: str) -> str:
        if self.mode == "memory":
            storage_path = f"memory://{doc_id}/{source}"
            self._memory_documents[storage_path] = text
            return storage_path

        self.base_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(source).suffix or ".txt"
        target = self.base_dir / f"{doc_id}{suffix}"
        target.write_text(text, encoding="utf-8")
        return str(target)

    def store_file_stream(self, *, doc_id: str, file_stream: BinaryIO, source: str) -> str:
        data = file_stream.read()
        if self.mode == "memory":
            storage_path = f"memory://{doc_id}/{source}"
            self._memory_documents[storage_path] = data.decode("utf-8")
            return storage_path

        self.base_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(source).suffix or ".bin"
        target = self.base_dir / f"{doc_id}{suffix}"
        target.write_bytes(data)
        return str(target)

    def store_file_path(self, *, doc_id: str, file_path: Path, source: str | None = None) -> str:
        with file_path.open("rb") as stream:
            return self.store_file_stream(
                doc_id=doc_id,
                file_stream=stream,
                source=source or file_path.name,
            )

    def load(self, document: DocumentRecord) -> str | None:
        if document.storage_path:
            if document.storage_path.startswith("memory://"):
                return self._memory_documents.get(document.storage_path)
            path = Path(document.storage_path)
            if path.exists():
                return path.read_text(encoding="utf-8")
        return None


class FixedWindowChunker:
    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap cannot be negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str) -> list[str]:
        normalized = " ".join(text.split())
        if not normalized:
            return []

        chunks: list[str] = []
        start = 0
        while start < len(normalized):
            end = min(len(normalized), start + self.chunk_size)
            chunks.append(normalized[start:end].strip())
            if end == len(normalized):
                break
            start = end - self.chunk_overlap
        return [chunk for chunk in chunks if chunk]


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._entries: list[tuple[ChunkRecord, list[float]]] = []

    def add(self, chunks: list[ChunkRecord], vectors: list[list[float]]) -> None:
        for chunk, vector in zip(chunks, vectors, strict=True):
            self._entries.append((chunk, vector))

    def search(self, *, user_id: str, query_vector: list[float], top_k: int) -> list[ChunkRecord]:
        scoped_entries = [entry for entry in self._entries if entry[0].user_id == user_id]
        ranked = sorted(
            scoped_entries,
            key=lambda entry: cosine_similarity(query_vector, entry[1]),
            reverse=True,
        )
        return [chunk for chunk, _ in ranked[:top_k]]


class IngestionService:
    def __init__(
        self,
        *,
        chunker: FixedWindowChunker,
        embedding_client: EmbeddingClient,
        vector_store: InMemoryVectorStore,
        metadata_store: MetadataStore,
        document_storage: DocumentStorage,
    ) -> None:
        self.chunker = chunker
        self.embedding_client = embedding_client
        self.vector_store = vector_store
        self.metadata_store = metadata_store
        self.document_storage = document_storage

    def ingest_text(self, *, user_id: str, text: str, source: str) -> IngestResult:
        normalized = self.preprocess(text)
        storage_path = self.document_storage.store_text(
            doc_id=str(uuid4()),
            text=normalized,
            source=source,
        )
        doc_id = extract_doc_id_from_storage_path(storage_path)
        return self._finalize_ingest(
            user_id=user_id,
            text=normalized,
            source=source,
            doc_id=doc_id,
            storage_path=storage_path,
        )

    def ingest_file_stream(self, *, user_id: str, file_stream: BinaryIO, source: str) -> IngestResult:
        payload = file_stream.read()
        text = payload.decode("utf-8")
        doc_id = str(uuid4())
        storage_path = self.document_storage.store_file_stream(
            doc_id=doc_id,
            file_stream=BytesIO(payload),
            source=source,
        )
        return self._finalize_ingest(
            user_id=user_id,
            text=text,
            source=source,
            doc_id=doc_id,
            storage_path=storage_path,
        )

    def ingest_file_path(self, *, user_id: str, file_path: Path, source: str | None = None) -> IngestResult:
        payload = file_path.read_bytes()
        resolved_source = source or file_path.name
        doc_id = str(uuid4())
        storage_path = self.document_storage.store_file_path(
            doc_id=doc_id,
            file_path=file_path,
            source=resolved_source,
        )
        return self._finalize_ingest(
            user_id=user_id,
            text=payload.decode("utf-8"),
            source=resolved_source,
            doc_id=doc_id,
            storage_path=storage_path,
        )

    def _finalize_ingest(
        self,
        *,
        user_id: str,
        text: str,
        source: str,
        doc_id: str,
        storage_path: str,
    ) -> IngestResult:
        normalized = self.preprocess(text)
        chunks = self.chunk(normalized)
        if not chunks:
            raise ValueError("Document must contain non-empty text")

        created_at = datetime.now(UTC).isoformat()
        document_record = DocumentRecord(
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            created_at=created_at,
            storage_path=storage_path,
        )
        self.metadata_store.add_document(document_record)

        chunk_records = [
            ChunkRecord(
                chunk_id=str(uuid4()),
                doc_id=doc_id,
                user_id=user_id,
                content=chunk,
                metadata={"source": source},
            )
            for chunk in chunks
        ]
        embeddings = self.embed(chunks)
        self.store(chunk_records, embeddings)
        return IngestResult(
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            created_at=created_at,
            chunk_count=len(chunk_records),
        )

    def preprocess(self, text: str) -> str:
        return text.strip()

    def chunk(self, text: str) -> list[str]:
        return self.chunker.chunk(text)

    def embed(self, chunks: list[str]) -> list[list[float]]:
        return self.embedding_client.embed(chunks)

    def store(self, chunks: list[ChunkRecord], embeddings: list[list[float]]) -> None:
        self.vector_store.add(chunks, embeddings)


class RetrievalService:
    def __init__(self, *, embedding_client: EmbeddingClient, vector_store: InMemoryVectorStore) -> None:
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
        self.metadata_store = MetadataStore(Path(metadata_path))
        self.document_storage = DocumentStorage(storage_mode, Path(document_storage_dir))
        self.vector_store = InMemoryVectorStore()
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

    def get_document(self, doc_id: str) -> DocumentRecord | None:
        return self.metadata_store.get_document(doc_id)


def resolve_user_id(token: str | None) -> str:
    if token is None:
        return DEFAULT_SINGLE_USER_ID

    normalized = token.strip()
    if not normalized:
        return DEFAULT_SINGLE_USER_ID
    return normalized


def extract_doc_id_from_storage_path(storage_path: str) -> str:
    name = Path(storage_path).stem
    if storage_path.startswith("memory://"):
        return storage_path.removeprefix("memory://").split("/", 1)[0]
    return name


def cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
