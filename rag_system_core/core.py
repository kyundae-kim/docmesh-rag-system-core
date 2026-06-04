from __future__ import annotations

import math
from io import BytesIO
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO, Protocol
from uuid import uuid4

import ollama
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import JSON, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


DEFAULT_SINGLE_USER_ID = "single-user"


class Base(DeclarativeBase):
    pass


class DocumentModel(Base):
    __tablename__ = "documents"

    doc_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, index=True)
    storage_path: Mapped[str | None] = mapped_column(String, nullable=True)


class ChunkModel(Base):
    __tablename__ = "chunks"

    chunk_id: Mapped[str] = mapped_column(String, primary_key=True)
    doc_id: Mapped[str] = mapped_column(ForeignKey("documents.doc_id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    metadata_json: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    embedding: Mapped[list[float]] = mapped_column(JSON, nullable=False)


class IngestionProgressModel(Base):
    __tablename__ = "ingestion_progress"

    progress_id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    doc_id: Mapped[str] = mapped_column(ForeignKey("documents.doc_id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    step_name: Mapped[str] = mapped_column(String, nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False, index=True)


class EmbeddingClient(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OllamaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OLLAMA_",
        env_file=".env",
        extra="ignore",
    )

    base_url: str = "http://ollama:11434"
    embed_model: str | None = None
    timeout: float = 30.0


class OllamaEmbeddingClient:
    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        settings = OllamaSettings()
        resolved_model = model or settings.embed_model
        if resolved_model is None or not resolved_model.strip():
            raise ValueError("Ollama embed model must be provided either as 'model' or OLLAMA_EMBED_MODEL")
        self.model = resolved_model
        self.base_url = (base_url or settings.base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.timeout
        self._client = ollama.Client(host=self.base_url, timeout=self.timeout)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        try:
            response = self._client.embed(model=self.model, input=texts)
        except Exception as exc:
            raise RuntimeError("Failed to fetch embeddings from Ollama") from exc

        try:
            embeddings = response["embeddings"]
        except (KeyError, TypeError) as exc:
            raise RuntimeError("Ollama returned a malformed embeddings response") from exc

        return [[float(value) for value in vector] for vector in embeddings]


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
    job_id: str
    doc_id: str
    user_id: str
    source: str
    created_at: str
    chunk_count: int


@dataclass(slots=True)
class IngestionProgressRecord:
    progress_id: str
    job_id: str
    doc_id: str
    user_id: str
    source: str
    step_name: str
    step_order: int
    status: str
    created_at: str


@dataclass(slots=True)
class QueryResult:
    answer: str
    prompt: str
    context_chunks: list[ChunkRecord]


class MetadataStore:
    DocumentModel = DocumentModel
    ChunkModel = ChunkModel
    IngestionProgressModel = IngestionProgressModel

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.engine: Engine = create_engine(f"sqlite+pysqlite:///{self.path}")
        self.session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self._initialize()

    def _initialize(self) -> None:
        Base.metadata.create_all(self.engine)

    def add_document(self, document: DocumentRecord) -> None:
        model = DocumentModel(
            doc_id=document.doc_id,
            user_id=document.user_id,
            source=document.source,
            created_at=document.created_at,
            storage_path=document.storage_path,
        )
        with self.session() as session:
            session.merge(model)
            session.commit()

    def add_chunks(self, chunks: list[ChunkRecord], embeddings: list[list[float]]) -> None:
        models = [
            ChunkModel(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                user_id=chunk.user_id,
                chunk_index=index,
                content=chunk.content,
                metadata_json=chunk.metadata,
                embedding=embedding,
            )
            for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
        ]
        with self.session() as session:
            session.add_all(models)
            session.commit()

    def add_ingestion_progress(self, progress_rows: list[IngestionProgressRecord]) -> None:
        models = [
            IngestionProgressModel(
                progress_id=row.progress_id,
                job_id=row.job_id,
                doc_id=row.doc_id,
                user_id=row.user_id,
                source=row.source,
                step_name=row.step_name,
                step_order=row.step_order,
                status=row.status,
                created_at=row.created_at,
            )
            for row in progress_rows
        ]
        with self.session() as session:
            session.add_all(models)
            session.commit()

    def get_document(self, doc_id: str) -> DocumentRecord | None:
        with self.session() as session:
            row = session.get(DocumentModel, doc_id)
        return document_record_from_model(row)

    def get_document_for_user(self, *, doc_id: str, user_id: str) -> DocumentRecord | None:
        statement = select(DocumentModel).where(DocumentModel.doc_id == doc_id, DocumentModel.user_id == user_id)
        with self.session() as session:
            row = session.scalars(statement).first()
        return document_record_from_model(row)

    def list_documents(self, user_id: str) -> list[DocumentRecord]:
        statement = select(DocumentModel).where(DocumentModel.user_id == user_id).order_by(DocumentModel.created_at)
        with self.session() as session:
            rows = session.scalars(statement).all()
        documents: list[DocumentRecord] = []
        for row in rows:
            record = document_record_from_model(row)
            if record is not None:
                documents.append(record)
        return documents

    def list_chunks(self, user_id: str | None = None) -> list[ChunkRecord]:
        statement = select(ChunkModel).order_by(ChunkModel.user_id, ChunkModel.doc_id, ChunkModel.chunk_index)
        if user_id is not None:
            statement = statement.where(ChunkModel.user_id == user_id)
        with self.session() as session:
            rows = session.scalars(statement).all()
        return [chunk_record_from_model(row) for row in rows]

    def load_chunk_embeddings(self, user_id: str | None = None) -> list[tuple[ChunkRecord, list[float]]]:
        statement = select(ChunkModel).order_by(ChunkModel.user_id, ChunkModel.doc_id, ChunkModel.chunk_index)
        if user_id is not None:
            statement = statement.where(ChunkModel.user_id == user_id)
        with self.session() as session:
            rows = session.scalars(statement).all()
        return [(chunk_record_from_model(row), list(row.embedding)) for row in rows]

    def list_document_chunks(self, *, doc_id: str, user_id: str) -> list[ChunkRecord]:
        statement = (
            select(ChunkModel)
            .where(ChunkModel.doc_id == doc_id, ChunkModel.user_id == user_id)
            .order_by(ChunkModel.chunk_index)
        )
        with self.session() as session:
            rows = session.scalars(statement).all()
        return [chunk_record_from_model(row) for row in rows]

    def list_ingestion_progress(
        self,
        *,
        doc_id: str,
        user_id: str,
        job_id: str | None = None,
    ) -> list[IngestionProgressRecord]:
        statement = (
            select(IngestionProgressModel)
            .where(IngestionProgressModel.doc_id == doc_id, IngestionProgressModel.user_id == user_id)
            .order_by(IngestionProgressModel.step_order, IngestionProgressModel.created_at)
        )
        if job_id is not None:
            statement = statement.where(IngestionProgressModel.job_id == job_id)
        with self.session() as session:
            rows = session.scalars(statement).all()
        return [ingestion_progress_record_from_model(row) for row in rows]

    def delete_document(self, *, doc_id: str, user_id: str) -> DocumentRecord | None:
        with self.session() as session:
            document = session.get(DocumentModel, doc_id)
            if document is None or document.user_id != user_id:
                return None
            chunk_rows = session.scalars(select(ChunkModel).where(ChunkModel.doc_id == doc_id)).all()
            for chunk in chunk_rows:
                session.delete(chunk)
            progress_rows = session.scalars(select(IngestionProgressModel).where(IngestionProgressModel.doc_id == doc_id)).all()
            for progress in progress_rows:
                session.delete(progress)
            session.delete(document)
            session.commit()
        return document_record_from_model(document)


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

    def delete(self, document: DocumentRecord) -> None:
        if not document.storage_path:
            return
        if document.storage_path.startswith("memory://"):
            self._memory_documents.pop(document.storage_path, None)
            return
        path = Path(document.storage_path)
        if path.exists():
            path.unlink()


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

    def delete_document(self, doc_id: str) -> None:
        self._entries = [entry for entry in self._entries if entry[0].doc_id != doc_id]


class IngestionService:
    PIPELINE_STEPS = [
        "load",
        "preprocess",
        "chunking",
        "embedding",
        "chunk_persistence",
        "vector_store",
    ]

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
        job_id = str(uuid4())
        created_at = datetime.now(UTC).isoformat()
        document_record = DocumentRecord(
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            created_at=created_at,
            storage_path=storage_path,
        )
        self.metadata_store.add_document(document_record)

        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="load",
            status="running",
            created_at=created_at,
        )
        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="load",
            status="completed",
            created_at=created_at,
        )

        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="preprocess",
            status="running",
            created_at=created_at,
        )
        normalized = self.preprocess(text)
        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="preprocess",
            status="completed",
            created_at=created_at,
        )

        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="chunking",
            status="running",
            created_at=created_at,
        )
        chunks = self.chunk(normalized)
        if not chunks:
            self._record_progress_transition(
                job_id=job_id,
                doc_id=doc_id,
                user_id=user_id,
                source=source,
                step_name="chunking",
                status="failed",
                created_at=created_at,
            )
            raise ValueError("Document must contain non-empty text")
        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="chunking",
            status="completed",
            created_at=created_at,
        )

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

        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="embedding",
            status="running",
            created_at=created_at,
        )
        try:
            embeddings = self.embed(chunks)
        except Exception:
            self._record_progress_transition(
                job_id=job_id,
                doc_id=doc_id,
                user_id=user_id,
                source=source,
                step_name="embedding",
                status="failed",
                created_at=created_at,
            )
            raise
        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="embedding",
            status="completed",
            created_at=created_at,
        )

        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="chunk_persistence",
            status="running",
            created_at=created_at,
        )
        try:
            self.metadata_store.add_chunks(chunk_records, embeddings)
        except Exception:
            self._record_progress_transition(
                job_id=job_id,
                doc_id=doc_id,
                user_id=user_id,
                source=source,
                step_name="chunk_persistence",
                status="failed",
                created_at=created_at,
            )
            raise
        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="chunk_persistence",
            status="completed",
            created_at=created_at,
        )

        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="vector_store",
            status="running",
            created_at=created_at,
        )
        try:
            self.vector_store.add(chunk_records, embeddings)
        except Exception:
            self._record_progress_transition(
                job_id=job_id,
                doc_id=doc_id,
                user_id=user_id,
                source=source,
                step_name="vector_store",
                status="failed",
                created_at=created_at,
            )
            raise
        self._record_progress_transition(
            job_id=job_id,
            doc_id=doc_id,
            user_id=user_id,
            source=source,
            step_name="vector_store",
            status="completed",
            created_at=created_at,
        )

        return IngestResult(
            job_id=job_id,
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

    def _record_progress_transition(
        self,
        *,
        job_id: str,
        doc_id: str,
        user_id: str,
        source: str,
        step_name: str,
        status: str,
        created_at: str,
    ) -> None:
        self.metadata_store.add_ingestion_progress(
            [
                IngestionProgressRecord(
                    progress_id=str(uuid4()),
                    job_id=job_id,
                    doc_id=doc_id,
                    user_id=user_id,
                    source=source,
                    step_name=step_name,
                    step_order=self.PIPELINE_STEPS.index(step_name),
                    status=status,
                    created_at=created_at,
                )
            ]
        )

    def store(self, chunks: list[ChunkRecord], embeddings: list[list[float]]) -> None:
        self.metadata_store.add_chunks(chunks, embeddings)
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
        self._restore_vector_store_from_metadata()

    def _restore_vector_store_from_metadata(self) -> None:
        persisted_entries = self.metadata_store.load_chunk_embeddings()
        if not persisted_entries:
            return
        chunks = [chunk for chunk, _ in persisted_entries]
        embeddings = [embedding for _, embedding in persisted_entries]
        self.vector_store.add(chunks, embeddings)

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
        document = self.metadata_store.delete_document(doc_id=doc_id, user_id=resolved_user_id)
        if document is None:
            return False
        self.document_storage.delete(document)
        self.vector_store.delete_document(doc_id)
        return True


def document_record_from_model(row: DocumentModel | None) -> DocumentRecord | None:
    if row is None:
        return None
    return DocumentRecord(
        doc_id=row.doc_id,
        user_id=row.user_id,
        source=row.source,
        created_at=row.created_at,
        storage_path=row.storage_path,
    )


def chunk_record_from_model(row: ChunkModel) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=row.chunk_id,
        doc_id=row.doc_id,
        user_id=row.user_id,
        content=row.content,
        metadata=dict(row.metadata_json),
    )


def ingestion_progress_record_from_model(row: IngestionProgressModel) -> IngestionProgressRecord:
    return IngestionProgressRecord(
        progress_id=row.progress_id,
        job_id=row.job_id,
        doc_id=row.doc_id,
        user_id=row.user_id,
        source=row.source,
        step_name=row.step_name,
        step_order=row.step_order,
        status=row.status,
        created_at=row.created_at,
    )


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
