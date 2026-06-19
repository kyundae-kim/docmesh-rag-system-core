from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from rag_system_core.types import DocumentRecord


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


def extract_doc_id_from_storage_path(storage_path: str) -> str:
    name = Path(storage_path).stem
    if storage_path.startswith("memory://"):
        return storage_path.removeprefix("memory://").split("/", 1)[0]
    return name
