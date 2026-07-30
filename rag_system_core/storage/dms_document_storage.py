from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import BinaryIO, Protocol

import dms

from rag_system_core.types import DocumentRecord


class DocumentManagementSdk(Protocol):
    def upload_document(self, request: dms.UploadDocumentRequest) -> dms.UploadDocumentResult: ...

    def upload_document_stream(self, request: dms.UploadDocumentStreamRequest) -> dms.UploadDocumentResult: ...

    def get_document_content(self, document_id: str) -> dms.DocumentContent: ...

    def soft_delete_document(self, document_id: str) -> dms.DeleteDocumentResult: ...

    def check_health(self) -> dms.HealthStatus: ...


class DmsDocumentStorage:
    def __init__(self, sdk: DocumentManagementSdk) -> None:
        self.sdk = sdk

    def store_text(
        self,
        *,
        doc_id: str,
        user_id: str,
        text: str,
        source: str,
        idempotency_key: str,
    ) -> str:
        request = dms.UploadDocumentRequest(
            content=text.encode("utf-8"),
            filename=source,
            content_type=_content_type(source, fallback="text/plain"),
            document_id=doc_id,
            metadata={"user_id": user_id, "source": source},
            created_by=user_id,
            idempotency_key=idempotency_key,
            idempotency_scope=user_id,
        )
        result = self.sdk.upload_document(request)
        return _require_document_id(result.document_id, expected=doc_id)

    def store_file_stream(
        self,
        *,
        doc_id: str,
        user_id: str,
        file_stream: BinaryIO,
        size: int,
        source: str,
        idempotency_key: str,
    ) -> str:
        request = dms.UploadDocumentStreamRequest(
            stream=file_stream,
            size=size,
            filename=source,
            content_type=_content_type(source),
            document_id=doc_id,
            metadata={"user_id": user_id, "source": source},
            created_by=user_id,
            idempotency_key=idempotency_key,
            idempotency_scope=user_id,
        )
        result = self.sdk.upload_document_stream(request)
        return _require_document_id(result.document_id, expected=doc_id)

    def store_file_path(
        self,
        *,
        doc_id: str,
        user_id: str,
        file_path: Path,
        source: str | None = None,
        idempotency_key: str,
    ) -> str:
        resolved_source = source or file_path.name
        with file_path.open("rb") as stream:
            return self.store_file_stream(
                doc_id=doc_id,
                user_id=user_id,
                file_stream=stream,
                size=file_path.stat().st_size,
                source=resolved_source,
                idempotency_key=idempotency_key,
            )

    def load(self, document: DocumentRecord) -> str | None:
        if document.asset_reference is None:
            return None
        try:
            content = self.sdk.get_document_content(document.asset_reference)
        except (dms.DocumentNotFoundError, dms.DocumentDeletedError):
            return None
        return content.content.decode("utf-8")

    def delete(self, document: DocumentRecord) -> None:
        if document.asset_reference is None:
            return
        try:
            self.sdk.soft_delete_document(document.asset_reference)
        except (dms.DocumentNotFoundError, dms.DocumentDeletedError):
            return

    def check(self) -> None:
        if not self.sdk.check_health().ok:
            raise RuntimeError("DMS health check failed")


def _content_type(source: str, *, fallback: str = "application/octet-stream") -> str:
    guessed, _ = mimetypes.guess_type(source)
    return guessed or fallback


def _require_document_id(document_id: str, *, expected: str) -> str:
    if document_id != expected:
        raise RuntimeError(f"DMS returned document_id {document_id!r}; expected {expected!r}")
    return document_id


__all__ = ["DmsDocumentStorage", "DocumentManagementSdk"]
