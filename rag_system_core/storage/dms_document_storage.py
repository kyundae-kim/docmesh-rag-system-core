from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import BinaryIO

import dms

from rag_system_core.types import DocumentRecord


DocumentManagementSdk = dms.DocumentManagementClient


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
        del idempotency_key
        request = dms.UploadDocumentStreamRequest(
            stream=file_stream,
            size=size,
            filename=source,
            content_type=_content_type(source),
            document_id=doc_id,
            metadata={"user_id": user_id, "source": source},
            created_by=user_id,
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
        result = self.sdk.upload_file(
            file_path,
            filename=resolved_source,
            content_type=_content_type(resolved_source),
            document_id=doc_id,
            metadata={"user_id": user_id, "source": resolved_source},
            created_by=user_id,
        )
        return _require_document_id(result.document_id, expected=doc_id)

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
            self.sdk.delete_document(document.asset_reference)
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
