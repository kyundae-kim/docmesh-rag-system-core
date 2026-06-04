# DocMesh RAG Core API Reference

## 1. 개요

이 문서는 현재 구현된 `RAGCore` public API를 설명한다.

기본 원칙:
- `token`은 현재 구현에서 그대로 user scope로 사용된다.
- `token`이 없거나 공백이면 `single-user` 스코프가 사용된다.
- 문서 본문은 메타데이터에 직접 저장되지 않고 `storage_path` 기반 자산 관리 방식을 사용한다.

---

## 2. 주요 반환 모델

### 2.1 `DocumentRecord`

```python
DocumentRecord(
    doc_id: str,
    user_id: str,
    source: str,
    created_at: str,
    storage_path: str | None,
)
```

### 2.2 `ChunkRecord`

```python
ChunkRecord(
    chunk_id: str,
    doc_id: str,
    user_id: str,
    content: str,
    metadata: dict[str, str],
)
```

### 2.3 `IngestResult`

```python
IngestResult(
    doc_id: str,
    user_id: str,
    source: str,
    created_at: str,
    chunk_count: int,
)
```

### 2.4 `QueryResult`

```python
QueryResult(
    answer: str,
    prompt: str,
    context_chunks: list[ChunkRecord],
)
```

---

## 3. `RAGCore` 생성

```python
from pathlib import Path
from rag_system_core import RAGCore

core = RAGCore(
    embedding_client=embedding_client,
    generation_client=generation_client,
    metadata_path=Path("./data/metadata.db"),
    document_storage_dir=Path("./data/documents"),
    storage_mode="local",
    chunk_size=512,
    chunk_overlap=64,
)
```

### 생성자 파라미터

- `embedding_client`: `embed(texts: list[str]) -> list[list[float]]`를 제공하는 객체
- `generation_client`: `generate(prompt: str) -> str`를 제공하는 객체
- `metadata_path`: SQLite DB 파일 경로
- `document_storage_dir`: local 문서 자산 저장 경로
- `storage_mode`: `"memory" | "local"`
- `chunk_size`: 청크 길이
- `chunk_overlap`: 청크 overlap 길이

---

## 4. Public API

### 4.1 `ingest_text`

텍스트 본문을 직접 적재한다.

```python
result = core.ingest_text(
    text="alpha beta gamma",
    source="note.txt",
    token="user-token-a",
)
```

#### 시그니처

```python
ingest_text(*, text: str, source: str, token: str | None = None) -> IngestResult
```

#### 동작
- token을 user scope로 해석한다.
- 텍스트를 전처리/청킹/임베딩한다.
- 문서 자산을 저장한다.
- 문서/청크 메타데이터를 persistence에 기록한다.
- vector store에 청크를 적재한다.

---

### 4.2 `ingest_file_stream`

파일 스트림을 적재한다.

```python
from io import BytesIO

result = core.ingest_file_stream(
    file_stream=BytesIO(b"document from stream"),
    source="stream.txt",
    token="user-token-a",
)
```

#### 시그니처

```python
ingest_file_stream(
    *,
    file_stream,
    source: str | None = None,
    token: str | None = None,
) -> IngestResult
```

#### 주의
- `source`는 필수 의미를 가진다.
- `source`가 없거나 공백이면 `ValueError("source is required for stream ingestion")`가 발생한다.

---

### 4.3 `ingest_file_path`

파일 경로를 직접 받아 적재한다.

```python
from pathlib import Path

result = core.ingest_file_path(
    file_path=Path("./sample.txt"),
    token="user-token-a",
)
```

#### 시그니처

```python
ingest_file_path(
    *,
    file_path,
    token: str | None = None,
    source: str | None = None,
) -> IngestResult
```

#### 동작
- `source`를 생략하면 파일명(`file_path.name`)을 사용한다.
- 파일 내용을 읽어 ingest 파이프라인에 전달한다.

---

### 4.4 `query`

질문에 대해 사용자 스코프 내 문서만 검색하여 답변을 생성한다.

```python
response = core.query(
    question="alpha에 대해 요약해줘",
    top_k=3,
    token="user-token-a",
)
```

#### 시그니처

```python
query(*, question: str, top_k: int = 3, token: str | None = None) -> QueryResult
```

#### 반환
- `answer`: 생성된 답변
- `prompt`: 실제 생성에 사용된 프롬프트
- `context_chunks`: 검색된 청크 목록

---

### 4.5 `list_documents`

현재 user scope의 문서 목록을 반환한다.

```python
documents = core.list_documents(token="user-token-a")
```

#### 시그니처

```python
list_documents(token: str | None = None) -> list[DocumentRecord]
```

---

### 4.6 `get_document`

특정 문서 메타데이터를 **현재 user scope 기준으로** 조회한다.

```python
doc = core.get_document(doc_id, token="user-token-a")
```

#### 시그니처

```python
get_document(doc_id: str, *, token: str | None = None) -> DocumentRecord | None
```

#### 동작
- 현재 user scope와 `doc_id`가 모두 일치하는 문서만 반환한다.
- scope가 다르거나 문서가 없으면 `None`을 반환한다.

---

### 4.7 `list_document_chunks`

특정 문서의 chunk 목록을 현재 user scope 기준으로 반환한다.

```python
chunks = core.list_document_chunks(doc_id, token="user-token-a")
```

#### 시그니처

```python
list_document_chunks(doc_id: str, *, token: str | None = None) -> list[ChunkRecord]
```

#### 동작
- 지정한 `doc_id`와 현재 user scope가 모두 일치하는 chunk만 반환한다.
- 정렬은 chunk 생성 순서(`chunk_index`) 기준이다.

---

### 4.8 `delete_document`

특정 문서를 현재 user scope에서 삭제한다.

```python
deleted = core.delete_document(doc_id, token="user-token-a")
```

#### 시그니처

```python
delete_document(doc_id: str, *, token: str | None = None) -> bool
```

#### 반환
- `True`: 삭제 성공
- `False`: 대상 문서가 없거나 현재 user scope와 일치하지 않음

#### 삭제 범위
- document metadata row
- chunk metadata rows
- stored asset file or memory object
- in-memory vector store entries

---

## 5. 프롬프트 형식

현재 generation prompt는 아래 형식을 따른다.

```text
[System Prompt]
<system prompt>

[Retrieved Context]
<context chunk 1>

<context chunk 2>

[User Query]
<question>
```

---

## 6. 저장 구조 개요

### 6.1 Metadata DB
- backend: SQLite
- access layer: SQLAlchemy ORM
- 주요 테이블:
  - `documents`
  - `chunks`

### 6.2 Document storage
- `memory`: `memory://...` logical path 사용
- `local`: 실제 파일 저장 후 path 기록

### 6.3 Retrieval 복원
- 프로세스 시작 시 `chunks` 테이블의 persisted chunk + embedding을 로드한다.
- 이를 기반으로 in-memory vector store를 복원한다.

---

## 7. 사용 예시

```python
from io import BytesIO
from pathlib import Path
from rag_system_core import RAGCore

core = RAGCore(
    embedding_client=embedding_client,
    generation_client=generation_client,
    metadata_path=Path("./data/metadata.db"),
    document_storage_dir=Path("./data/documents"),
    storage_mode="local",
)

text_result = core.ingest_text(
    token="user-a",
    text="alpha beta gamma",
    source="note.txt",
)

stream_result = core.ingest_file_stream(
    token="user-a",
    file_stream=BytesIO(b"alpha from stream"),
    source="stream.txt",
)

path_result = core.ingest_file_path(
    token="user-a",
    file_path=Path("./sample.txt"),
)

response = core.query(
    token="user-a",
    question="alpha를 요약해줘",
    top_k=3,
)

chunks = core.list_document_chunks(text_result.doc_id, token="user-a")
deleted = core.delete_document(stream_result.doc_id, token="user-a")
```

---

## 8. 알려진 현재 제약

- vector store는 현재 in-memory 구현이다.
- token과 user_id의 별도 매핑 저장소는 아직 없다. 현재는 token 문자열 자체를 scope로 사용한다.
