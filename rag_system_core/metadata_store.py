from __future__ import annotations

from pathlib import Path

from sqlalchemy import JSON, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from rag_system_core.helpers import ChunkRecord, DocumentRecord, IngestionProgressRecord


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

    def add_chunks(self, chunks: list[ChunkRecord]) -> None:
        models = [
            ChunkModel(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                user_id=chunk.user_id,
                chunk_index=index,
                content=chunk.content,
                metadata_json=chunk.metadata,
            )
            for index, chunk in enumerate(chunks)
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
