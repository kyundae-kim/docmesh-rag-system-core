from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest

from test_rag_system_core.support import create_test_rig


def test_ingest_text_uses_token_as_user_scope(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)

    result = rig.core.ingest_text(token="token-a", text="alpha beta gamma", source="note.txt")

    assert result.user_id == "token-a"
    assert result.source == "note.txt"
    assert result.doc_id
    assert result.created_at
    assert result.chunk_count == 1
    assert [doc.doc_id for doc in rig.core.list_documents(token="token-a")] == [result.doc_id]


def test_ingest_text_without_token_uses_single_user_scope(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)

    result = rig.core.ingest_text(text="alpha solo text", source="solo.txt")

    assert result.user_id == "single-user"
    assert [doc.doc_id for doc in rig.core.list_documents()] == [result.doc_id]


def test_ingest_text_stores_string_input_as_managed_asset(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path, storage_mode="local")

    result = rig.core.ingest_text(token="token-a", text="alpha asset text", source="asset.txt")

    stored = rig.core.get_document(result.doc_id, token="token-a")
    assert stored is not None
    assert stored.storage_path is not None
    stored_path = Path(stored.storage_path)
    assert stored_path.exists()
    assert stored_path.read_text(encoding="utf-8") == "alpha asset text"


def test_ingest_text_memory_storage_uses_logical_asset_path(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path, storage_mode="memory")

    result = rig.core.ingest_text(token="token-a", text="alpha memory asset", source="memory.txt")

    stored = rig.core.get_document(result.doc_id, token="token-a")
    assert stored is not None
    assert stored.storage_path is not None
    assert stored.storage_path.startswith("memory://")
    assert rig.core.document_storage.load(stored) == "alpha memory asset"


def test_ingest_file_stream_copies_input_stream_into_managed_storage(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path, storage_mode="local")
    stream = BytesIO(b"alpha original file")

    result = rig.core.ingest_file_stream(token="token-a", file_stream=stream, source="source.txt")

    stored = rig.core.get_document(result.doc_id, token="token-a")
    assert stored is not None
    assert stored.storage_path is not None
    stored_path = Path(stored.storage_path)
    assert stored_path.exists()
    assert stored_path.name != "source.txt"
    assert stored_path.read_text(encoding="utf-8") == "alpha original file"


def test_ingest_file_stream_requires_explicit_source(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path, storage_mode="local")

    with pytest.raises(ValueError, match="source is required for stream ingestion"):
        rig.core.ingest_file_stream(token="token-a", file_stream=BytesIO(b"alpha"))


def test_ingest_file_path_reads_existing_file_via_dedicated_api(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path, storage_mode="local")
    source_file = tmp_path / "existing.txt"
    source_file.write_text("alpha from path", encoding="utf-8")

    result = rig.core.ingest_file_path(token="token-a", file_path=source_file)

    stored = rig.core.get_document(result.doc_id, token="token-a")
    assert stored is not None
    assert stored.source == "existing.txt"
    assert stored.storage_path is not None
    assert Path(stored.storage_path).read_text(encoding="utf-8") == "alpha from path"


def test_ingestion_service_exposes_separate_stream_and_path_methods(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)

    assert hasattr(rig.core.ingestor, "ingest_file_stream")
    assert hasattr(rig.core.ingestor, "ingest_file_path")
    assert not hasattr(rig.core.ingestor, "ingest_file")


def test_document_storage_exposes_text_stream_and_path_methods(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)

    assert hasattr(rig.core.document_storage, "store_text")
    assert hasattr(rig.core.document_storage, "store_file_stream")
    assert hasattr(rig.core.document_storage, "store_file_path")
    assert not hasattr(rig.core.document_storage, "store_bytes")


def test_ragcore_exposes_explicit_stream_and_path_ingest_methods(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)

    assert hasattr(rig.core, "ingest_file_stream")
    assert hasattr(rig.core, "ingest_file_path")
    assert not hasattr(rig.core, "ingest_file")


def test_blank_token_falls_back_to_single_user_scope(tmp_path: Path) -> None:
    rig = create_test_rig(tmp_path)

    result = rig.core.ingest_text(token="   ", text="alpha", source="x.txt")

    assert result.user_id == "single-user"
    assert [doc.doc_id for doc in rig.core.list_documents()] == [result.doc_id]
