from __future__ import annotations

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from dms import (
    DocumentContent,
    DocumentDeletedError,
    DocumentNotFoundError,
    UploadDocumentRequest,
    UploadDocumentStreamRequest,
)

from rag_system_core.storage.dms_document_storage import DmsDocumentStorage
from rag_system_core.types import DocumentRecord


class FakeDmsSdk:
    def __init__(self) -> None:
        self.upload_requests: list[object] = []
        self.upload_file_calls: list[dict[str, object]] = []
        self.delete_calls: list[str] = []
        self.content: bytes = b"stored content"
        self.content_error: Exception | None = None
        self.delete_error: Exception | None = None

    def upload_document(self, request):
        self.upload_requests.append(request)
        return SimpleNamespace(document_id=request.document_id)

    def upload_document_stream(self, request):
        self.upload_requests.append(request)
        return SimpleNamespace(document_id=request.document_id)

    def upload_file(self, path, *, filename, content_type, document_id, metadata, created_by):
        self.upload_file_calls.append(
            {
                "path": path,
                "filename": filename,
                "content_type": content_type,
                "document_id": document_id,
                "metadata": metadata,
                "created_by": created_by,
            }
        )
        return SimpleNamespace(document_id=document_id)

    def get_document_content(self, document_id: str):
        if self.content_error is not None:
            raise self.content_error
        return DocumentContent(
            document_id=document_id,
            content=self.content,
            content_type="text/plain",
            filename="note.txt",
            size=len(self.content),
        )

    def delete_document(self, document_id: str):
        self.delete_calls.append(document_id)
        if self.delete_error is not None:
            raise self.delete_error
        return SimpleNamespace(deleted=True)

def make_document(*, asset_reference: str = "doc-1") -> DocumentRecord:
    return DocumentRecord(
        doc_id="doc-1",
        user_id="user-a",
        source="note.txt",
        created_at="2026-07-28T00:00:00+00:00",
        asset_reference=asset_reference,
    )


def test_store_text_uploads_public_document_id_with_user_metadata_and_idempotency() -> None:
    sdk = FakeDmsSdk()
    storage = DmsDocumentStorage(sdk)

    asset_reference = storage.store_text(
        doc_id="doc-1",
        user_id="user-a",
        text="alpha",
        source="note.txt",
        idempotency_key="job-1",
    )

    assert asset_reference == "doc-1"
    request = sdk.upload_requests[0]
    assert isinstance(request, UploadDocumentRequest)
    assert request.content == b"alpha"
    assert request.filename == "note.txt"
    assert request.content_type == "text/plain"
    assert request.document_id == "doc-1"
    assert request.created_by == "user-a"
    assert request.metadata == {"user_id": "user-a", "source": "note.txt"}
    assert request.idempotency_scope == "user-a"
    assert request.idempotency_key == "job-1"


def test_store_file_stream_uses_known_size_request_without_closing_caller_stream() -> None:
    sdk = FakeDmsSdk()
    storage = DmsDocumentStorage(sdk)
    stream = BytesIO(b"pdf bytes")

    asset_reference = storage.store_file_stream(
        doc_id="doc-2",
        user_id="user-a",
        file_stream=stream,
        size=9,
        source="paper.pdf",
        idempotency_key="job-2",
    )

    assert asset_reference == "doc-2"
    request = sdk.upload_requests[0]
    assert isinstance(request, UploadDocumentStreamRequest)
    assert request.stream is stream
    assert request.size == 9
    assert request.filename == "paper.pdf"
    assert request.content_type == "application/pdf"
    assert request.document_id == "doc-2"

    assert stream.closed is False


def test_store_file_path_delegates_file_lifecycle_to_dms(tmp_path: Path) -> None:
    sdk = FakeDmsSdk()
    storage = DmsDocumentStorage(sdk)
    source_file = tmp_path / "source.md"
    source_file.write_bytes(b"alpha")

    asset_reference = storage.store_file_path(
        doc_id="doc-3",
        user_id="user-a",
        file_path=source_file,
        source=None,
        idempotency_key="job-3",
    )

    assert asset_reference == "doc-3"
    assert sdk.upload_file_calls == [
        {
            "path": source_file,
            "filename": "source.md",
            "content_type": "text/markdown",
            "document_id": "doc-3",
            "metadata": {"user_id": "user-a", "source": "source.md"},
            "created_by": "user-a",
        }
    ]


def test_load_returns_utf8_text_and_maps_missing_or_deleted_documents_to_none() -> None:
    sdk = FakeDmsSdk()
    storage = DmsDocumentStorage(sdk)
    document = make_document()

    assert storage.load(document) == "stored content"

    sdk.content_error = DocumentNotFoundError("missing", document_id="doc-1")
    assert storage.load(document) is None

    sdk.content_error = DocumentDeletedError("deleted", document_id="doc-1")
    assert storage.load(document) is None


def test_delete_soft_deletes_by_public_asset_reference_and_is_idempotent() -> None:
    sdk = FakeDmsSdk()
    storage = DmsDocumentStorage(sdk)
    document = make_document()

    storage.delete(document)
    sdk.delete_error = DocumentDeletedError("deleted", document_id="doc-1")
    storage.delete(document)

    assert sdk.delete_calls == ["doc-1", "doc-1"]
