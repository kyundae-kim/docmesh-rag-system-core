# DocMesh RAG Core Public API Reference

## 1. 목적

이 문서는 **외부 애플리케이션/서비스가 재사용할 수 있는 공개 API만** 설명합니다.
즉, 소스코드의 내부 구현 경로가 아니라, 현재 패키지가 안정적으로 노출하는 public surface를 기준으로 작성합니다.

이 문서를 읽은 뒤 가능한 목표:
- 공개 import 경로만 사용해 `RAGCore`를 생성한다.
- 문서를 적재하고 질의한다.
- 반환 타입과 메서드 계약을 이해한다.
- 필요한 설정은 `docs/config.md`에서 확인한다.

---

## 2. 공개 import 경로

외부 사용자는 아래 경로만 사용하세요.

```python
from rag_system_core import (
    RAGCore,
    OllamaEmbeddingClient,
    OllamaGenerationClient,
    bootstrap_rag_core_from_docmesh,
    DocumentRecord,
    ChunkRecord,
    IngestResult,
    IngestionProgressRecord,
    QueryResult,
    EmbeddingClient,
    GenerationClient,
)
```

타입만 가져올 때는 다음 경로도 사용 가능합니다.

```python
from rag_system_core.types import (
    DocumentRecord,
    ChunkRecord,
    IngestResult,
    IngestionProgressRecord,
    QueryResult,
    EmbeddingClient,
    GenerationClient,
)
```

> `rag_system_core.domain.*`, `rag_system_core.storage.*`, `rag_system_core.composition.*`, `rag_system_core.adapters.*`, `rag_system_core.core` 같은 내부 경로는 공개 API 문서의 사용 대상이 아닙니다.

---

## 3. 공개 타입과 클라이언트 계약

### 3.1 `EmbeddingClient`

```python
class EmbeddingClient(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
```

계약:
- 입력은 `list[str]`
- 반환은 `list[list[float]]`
- 반환 벡터 수는 입력 텍스트 수와 같아야 함
- 벡터 차원은 일관되어야 함

### 3.2 `GenerationClient`

```python
class GenerationClient(Protocol):
    def generate(self, prompt: str) -> str: ...
```

계약:
- 입력은 완성된 단일 프롬프트 문자열
- 반환은 최종 답변 문자열 `str`

### 3.3 `DocumentRecord`

```python
@dataclass(slots=True)
class DocumentRecord:
    doc_id: str
    user_id: str
    source: str
    created_at: str
    storage_path: str | None = None
```

### 3.4 `ChunkRecord`

```python
@dataclass(slots=True)
class ChunkRecord:
    chunk_id: str
    doc_id: str
    user_id: str
    content: str
    metadata: dict[str, str]
```

### 3.5 `IngestResult`

```python
@dataclass(slots=True)
class IngestResult:
    job_id: str
    doc_id: str
    user_id: str
    source: str
    created_at: str
    chunk_count: int
```

### 3.6 `IngestionProgressRecord`

```python
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
```

### 3.7 `QueryResult`

```python
@dataclass(slots=True)
class QueryResult:
    answer: str
    prompt: str
    context_chunks: list[ChunkRecord]
```

---

## 4. 공개 생성 경로

### 4.1 `RAGCore`

```python
RAGCore(
    *,
    embedding_client: EmbeddingClient,
    generation_client: GenerationClient,
    metadata_path: str | Path,
    document_storage_dir: str | Path,
    storage_mode: str = "memory",
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    vector_store=None,
)
```

주요 파라미터:

| 파라미터 | 설명 |
|---|---|
| `embedding_client` | `embed(texts)`를 제공하는 embedding adapter |
| `generation_client` | `generate(prompt)`를 제공하는 generation adapter |
| `metadata_path` | SQLite metadata DB 파일 경로 |
| `document_storage_dir` | 문서 자산 저장 디렉터리 |
| `storage_mode` | `"memory"` 또는 `"local"` |
| `chunk_size` | chunk 크기 |
| `chunk_overlap` | chunk overlap 크기 |
| `vector_store` | 선택적 사용자 제공 vector store |

중요:
- `storage_mode` 기본값은 `"memory"`
- 설정값 예시는 `docs/config.md` 참고

### 4.2 `bootstrap_rag_core_from_docmesh`

```python
bootstrap_rag_core_from_docmesh(
    *,
    metadata_path,
    document_storage_dir,
    storage_mode="local",
    chunk_size=512,
    chunk_overlap=64,
)
```

이 helper는 공개 API로 export되며, DocMesh 설정을 사용해 `RAGCore`를 조립할 때 사용합니다.

중요:
- helper의 기본 `storage_mode`는 `"local"`
- `RAGCore` 생성자 자체 기본값은 `"memory"`

---

## 5. 공개 메서드

### 5.1 `ingest_text`

```python
ingest_text(*, text: str, source: str, token: str | None = None) -> IngestResult
```

예시:

```python
result = core.ingest_text(
    text="alpha beta gamma",
    source="note.txt",
    token="user-a",
)
```

### 5.2 `ingest_file_stream`

```python
ingest_file_stream(
    *,
    file_stream,
    source: str | None = None,
    token: str | None = None,
) -> IngestResult
```

주의:
- `source`는 실질적으로 필수
- 비어 있으면 `ValueError("source is required for stream ingestion")`

### 5.3 `ingest_file_path`

```python
ingest_file_path(
    *,
    file_path,
    token: str | None = None,
    source: str | None = None,
) -> IngestResult
```

동작:
- `source`를 생략하면 파일명을 사용

### 5.4 `query`

```python
query(*, question: str, top_k: int = 3, token: str | None = None) -> QueryResult
```

반환:
- `answer`: 최종 답변 문자열
- `prompt`: 실제 생성에 사용된 프롬프트
- `context_chunks`: 검색된 chunk 목록

### 5.5 `list_documents`

```python
list_documents(token: str | None = None) -> list[DocumentRecord]
```

### 5.6 `get_document`

```python
get_document(doc_id: str, *, token: str | None = None) -> DocumentRecord | None
```

### 5.7 `list_document_chunks`

```python
list_document_chunks(doc_id: str, *, token: str | None = None) -> list[ChunkRecord]
```

### 5.8 `list_ingestion_progress`

```python
list_ingestion_progress(
    doc_id: str,
    *,
    token: str | None = None,
    job_id: str | None = None,
) -> list[IngestionProgressRecord]
```

### 5.9 `delete_document`

```python
delete_document(doc_id: str, *, token: str | None = None) -> bool
```

반환:
- `True`: 삭제 성공
- `False`: 대상 문서가 없거나 현재 user scope에 없음

### 5.10 `health_check`

```python
health_check() -> object
```

의미:
- metadata store 및 사용 가능한 의존 서비스 상태를 점검

---

## 6. 사용자 식별 규칙

기본 규칙:
- `token is None` → `single-user`
- `token.strip() == ""` → `single-user`
- 그 외 → token 문자열 자체를 `user_id`로 사용

Keycloak 모드:
- `DOCMESH_AUTH_MODE=keycloak`이면 Keycloak 검증을 통해 `user_id`를 해석
- 관련 설정은 `docs/config.md` 참고

---

## 7. 공개 제공 Ollama adapter

현재 패키지는 공개 export로 다음 adapter를 제공합니다.

### 7.1 `OllamaEmbeddingClient`

```python
OllamaEmbeddingClient(*, client, model: str)
```

계약:
- `client.embed(model=..., input=...)`를 호출할 수 있어야 함
- 응답은 embeddings 배열을 제공해야 함

### 7.2 `OllamaGenerationClient`

```python
OllamaGenerationClient(*, client, model: str)
```

계약:
- `client.chat(model=..., messages=[...])`를 호출할 수 있어야 함
- 응답은 최종 텍스트를 제공해야 함

> 이 두 클래스는 공개 API이지만, 이미 생성된 Ollama 호환 client를 주입받는 adapter입니다.

---

## 8. 최소 성공 예시

### 8.1 bootstrap helper 사용

```python
from pathlib import Path
from rag_system_core import bootstrap_rag_core_from_docmesh

core = bootstrap_rag_core_from_docmesh(
    metadata_path=Path("./data/metadata.db"),
    document_storage_dir=Path("./data/documents"),
    storage_mode="local",
)

result = core.ingest_text(
    text="alpha beta gamma",
    source="note.txt",
)

response = core.query(
    question="alpha를 요약해줘",
)

print(result.doc_id)
print(response.answer)
```

### 8.2 직접 생성

```python
from pathlib import Path
from rag_system_core import RAGCore

class MyEmbeddingClient:
    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

class MyGenerationClient:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

core = RAGCore(
    embedding_client=MyEmbeddingClient(),
    generation_client=MyGenerationClient(),
    metadata_path=Path("./data/metadata.db"),
    document_storage_dir=Path("./data/documents"),
    storage_mode="local",
)
```

---

## 9. 비공개 범위 / non-goals

다음은 이 문서의 범위 밖입니다.
- 내부 모듈 경로별 구현 설명
- ORM 모델과 내부 저장 상세 구현
- 내부 composition helper/factory 사용법
- 내부 prompt builder 구조 세부사항
- 내부 vector store 구현 세부사항

외부 연동은 이 문서의 공개 import 경로와 메서드 계약만 기준으로 하세요.
