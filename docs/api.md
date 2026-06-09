# DocMesh RAG Core API Reference

## 1. 개요

이 문서는 현재 구현된 `RAGCore` public API를 설명한다.

### 1.1 문서 목적
- `RAGCore`를 다른 애플리케이션이나 서비스에서 재사용할 때 필요한 public API 사용 기준을 제공한다.
- 생성자, 주요 메서드, 반환 모델, 저장 구조, 현재 제약 사항을 한 곳에서 확인할 수 있도록 정리한다.
- 내부 구현을 직접 읽지 않고도 기본적인 연동 방식과 호출 흐름을 이해할 수 있도록 돕는다.

### 1.2 문서 목표
- 외부 프로젝트에서 `RAGCore`를 생성하고 문서를 적재(query 전 포함)하는 최소 사용 흐름을 이해할 수 있어야 한다.
- 어떤 입력값과 반환값이 오가는지, 그리고 user scope가 어떻게 적용되는지 파악할 수 있어야 한다.
- 어떤 타입과 클래스가 public surface로 기대되는지 빠르게 확인할 수 있어야 한다.
- 현재 문서가 설명하는 범위와 설명하지 않는 범위를 구분할 수 있어야 한다.

기본 원칙:
- `token`은 현재 구현에서 그대로 user scope로 사용된다.
- `token`이 없거나 공백이면 `single-user` 스코프가 사용된다.
- 문서 본문은 메타데이터에 직접 저장되지 않고 `storage_path` 기반 자산 관리 방식을 사용한다.

---

## 2. Public import

다른 프로젝트에서는 가능한 한 아래와 같이 **public import 경로만 사용**하는 것을 권장한다.
내부 모듈 경로가 노출되어 있더라도, 별도 문서화되지 않은 경로는 public contract로 간주하지 않는다.

```python
from pathlib import Path

from rag_system_core import RAGCore
```

반환 타입을 명시적으로 사용할 필요가 있다면, 아래와 같이 **패키지에서 공식적으로 재노출(re-export)된 public 타입 경로**를 제공하는 것이 바람직하다.

```python
from rag_system_core import RAGCore
from rag_system_core.types import (
    DocumentRecord,
    ChunkRecord,
    IngestResult,
    IngestionProgressRecord,
    QueryResult,
)
```

> 주의:
> - `rag_system_core.types`는 반환 타입과 client protocol 타입을 위한 **공식 public import 경로**로 사용한다.
> - `rag_system_core.internal.*`, `rag_system_core.adapters.*` 등 내부 구현 경로에 직접 의존하는 방식은 권장하지 않는다.

---

## 3. 주요 반환 모델

### 3.1 `DocumentRecord`

```python
DocumentRecord(
    doc_id: str,
    user_id: str,
    source: str,
    created_at: str,
    storage_path: str | None,
)
```

### 3.2 `ChunkRecord`

```python
ChunkRecord(
    chunk_id: str,
    doc_id: str,
    user_id: str,
    content: str,
    metadata: dict[str, str],
)
```

### 3.3 `IngestResult`

```python
IngestResult(
    job_id: str,
    doc_id: str,
    user_id: str,
    source: str,
    created_at: str,
    chunk_count: int,
)
```

### 3.4 `IngestionProgressRecord`

```python
IngestionProgressRecord(
    progress_id: str,
    job_id: str,
    doc_id: str,
    user_id: str,
    source: str,
    step_name: str,
    step_order: int,
    status: str,
    created_at: str,
)
```

### 3.5 `QueryResult`

```python
QueryResult(
    answer: str,
    prompt: str,
    context_chunks: list[ChunkRecord],
)
```

---

## 4. `RAGCore` 생성

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

### 4.1 의존성 및 런타임 요구사항

`RAGCore`를 실제로 import/생성하려면 현재 구현 기준으로 아래 런타임 의존성이 필요하다.

- `ollama`: 기본 Ollama client 구현(`OllamaEmbeddingClient`, `OllamaGenerationClient`) import에 필요
- `pydantic-settings`: Ollama/Milvus 설정 클래스 import에 필요
- `sqlalchemy`: metadata persistence(SQLite ORM) 구동에 필요
- `pymilvus`: Milvus Lite vector store 구동에 필요

관련 런타임 조건:
- `docmesh_py_core.load_settings()`가 성공할 수 있도록 docmesh 공통 설정이 유효해야 한다.
- `metadata_path`는 SQLite 파일을 생성/쓰기 가능한 경로여야 한다.
- `document_storage_dir`는 `storage_mode="local"`일 때 문서 자산을 생성/쓰기 가능한 경로여야 한다.
- Milvus Lite 저장 경로는 기본적으로 `metadata_path.with_suffix(".milvus.db")`를 사용하므로, 해당 위치 역시 쓰기 가능해야 한다.

### 4.1.1 `docmesh-py-core` 연동

`rag_system_core`는 `docmesh-py-core`를 기본 의존성으로 사용한다.

- `load_settings()`를 통해 공통 설정을 읽는다.
- `ServiceFactoryRegistry`를 통해 `ollama`, `milvus` client를 우선 생성한다.
- health check 집계 시 `check_all_services(...)`를 우선 사용한다.

이 연동은 현재 다음 범위에 한정된다.

- 설정 로딩
- Ollama/Milvus client 생성
- 공통 health check 집계
- 선택적 Keycloak 기반 `token -> user_id` 해석

반대로 아래는 여전히 `rag_system_core`가 직접 담당한다.

- ingestion pipeline
- chunking
- SQLite metadata persistence
- prompt assembly
- retrieval orchestration

참고:
- `from rag_system_core.types import ...` 형태의 **타입 import만 사용할 경우**에는 위 외부 런타임 의존성이 직접 필요하지 않다.
- 반면 `from rag_system_core import RAGCore` 또는 Ollama/Milvus 관련 설정/클라이언트를 실제로 사용할 경우에는 위 의존성이 설치되어 있어야 한다.

### 4.2 Client contract

#### `EmbeddingClient`

`RAGCore`가 기대하는 최소 contract는 아래와 같다.

```python
from rag_system_core.types import EmbeddingClient

class MyEmbeddingClient(EmbeddingClient):
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...
```

호출 계약:
- 입력은 `list[str]`이다.
- 반환값은 `list[list[float]]`이다.
- **반환 벡터 개수는 입력 텍스트 개수와 반드시 같아야 한다.**
- 각 벡터의 차원 수는 서로 일관되어야 한다.
- 같은 vector store 컬렉션에 들어가는 벡터 차원은 호출 간에도 일관되어야 한다.

현재 구현과의 호환 요구사항:
- ingestion 경로는 `embed(chunks)` 결과를 그대로 vector store에 전달하므로, 청크 수와 벡터 수가 다르면 실패한다.
- query 경로는 `embed([question])[0]` 형태를 사용하므로, 질문 1개 입력에 대해 **반드시 최소 1개의 벡터**를 반환해야 한다.
- 실패 시에는 예외를 발생시키는 것이 안전하다. 현재 `RAGCore`는 embedding 오류를 별도로 표준화하지 않고 상위로 전파한다.

권장 사항:
- 빈 입력 `[]`에 대해서는 `[]`를 반환하도록 구현하는 것이 바람직하다.
- 반환값에는 `numpy.ndarray` 대신 직렬화 가능한 파이썬 `list[float]`를 사용하는 것이 안전하다.

#### `GenerationClient`

`RAGCore`가 기대하는 최소 contract는 아래와 같다.

```python
from rag_system_core.types import GenerationClient

class MyGenerationClient(GenerationClient):
    def generate(self, prompt: str) -> str:
        ...
```

호출 계약:
- 입력은 최종 조립된 단일 `prompt: str`이다.
- 반환값은 **최종 답변 문자열** `str`이어야 한다.

현재 구현과의 호환 요구사항:
- `RAGCore`는 chat message list, tool call 결과, structured object를 기대하지 않는다.
- `generate()` 결과를 그대로 `QueryResult.answer`에 넣으므로, 문자열이 아닌 객체를 반환하면 호출자 측에서 깨질 수 있다.
- 실패 시에는 예외를 발생시키는 것이 안전하다. 현재 `RAGCore`는 generation 오류를 별도로 표준화하지 않고 상위로 전파한다.

권장 사항:
- prompt 전체를 하나의 입력으로 처리하는 non-streaming wrapper를 제공하는 것이 가장 단순하다.
- 외부 LLM SDK가 dict/object를 반환한다면, adapter에서 최종 텍스트만 추출해서 `str`로 반환하는 것이 좋다.

### 4.3 기본 제공 Ollama client

현재 패키지는 `EmbeddingClient`, `GenerationClient`의 기본 구현으로 아래 클래스를 제공한다.

#### `OllamaEmbeddingClient`

```python
from rag_system_core import OllamaEmbeddingClient

embedding_client = OllamaEmbeddingClient(
    model="bge-m3",
    base_url="http://ollama:11434",
    timeout=30.0,
)
```

생성자 시그니처:

```python
OllamaEmbeddingClient(
    *,
    model: str | None = None,
    base_url: str | None = None,
    timeout: float | None = None,
)
```

동작:
- 내부적으로 `ollama.Client(host=..., timeout=...)`를 생성한다.
- `embed(texts)` 호출 시 `client.embed(model=self.model, input=texts)`를 사용한다.
- 응답의 `response["embeddings"]`를 읽어 `list[list[float]]`로 정규화한다.
- 입력이 빈 리스트이면 `[]`를 반환한다.

설정 소스:
- 명시적으로 전달한 인자가 우선한다.
- 그다음 `docmesh_py_core.load_settings()`에서 읽은 `settings.ollama` 값을 시도한다.
- 마지막으로 `OllamaEmbedSettings` 값을 사용한다.
- `OllamaEmbedSettings`는 `.env`와 환경변수 `OLLAMA_EMBED__*`를 읽는다.
- `OLLAMA_HOST`, `OLLAMA_EMBEDDING_MODEL`, `OLLAMA_REQUEST_TIMEOUT_SECONDS` 같은 값은 직접 fallback으로 읽지 않고, `load_settings()`가 성공적으로 해석한 결과를 통해 반영된다.

관련 설정 필드:
- `OLLAMA_HOST` 예: `http://ollama:11434`
- `OLLAMA_EMBEDDING_MODEL` 예: `bge-m3`
- `OLLAMA_REQUEST_TIMEOUT_SECONDS` 기본값 없음
- `OLLAMA_EMBED__BASE_URL` 기본값: `http://ollama:11434`
- `OLLAMA_EMBED__MODEL` 기본값 없음
- `OLLAMA_EMBED__TIMEOUT` 기본값: `30.0`

주의:
- `model` 인자와 `OLLAMA_EMBED__MODEL`이 모두 비어 있으면 `ValueError`가 발생한다.
- Ollama 호출 실패 시 `RuntimeError("Failed to fetch embeddings from Ollama")`가 발생한다.
- 응답에 `embeddings` 필드가 없거나 형식이 다르면 `RuntimeError("Ollama returned a malformed embeddings response")`가 발생한다.
- `docmesh_py_core.load_settings()`가 실패하면 embedding client 초기화도 즉시 실패한다.

#### `OllamaGenerationClient`

```python
from rag_system_core import OllamaGenerationClient

generation_client = OllamaGenerationClient(
    model="gpt-oss:20b",
    base_url="https://ollama.com",
    api_key="<api-key>",
    timeout=30.0,
)
```

생성자 시그니처:

```python
OllamaGenerationClient(
    *,
    model: str | None = None,
    base_url: str | None = None,
    timeout: float | None = None,
    api_key: str | None = None,
    headers: dict[str, str] | None = None,
)
```

동작:
- 내부적으로 `ollama.Client(host=..., headers=..., timeout=...)`를 생성한다.
- `generate(prompt)` 호출 시 `client.chat(model=self.model, messages=[{"role": "user", "content": prompt}])`를 사용한다.
- 응답의 `response["message"]["content"]`를 읽어 `str`로 반환한다.

설정 소스:
- 명시적으로 전달한 인자가 우선한다.
- 그다음 `docmesh_py_core.load_settings()`에서 읽은 `settings.ollama` 값을 시도한다.
- 마지막으로 `OllamaGenerateSettings` 값을 사용한다.
- `OllamaGenerateSettings`는 `.env`와 환경변수 `OLLAMA_GENERATE__*`를 읽는다.
- `OLLAMA_HOST`, `OLLAMA_GENERATION_MODEL`, `OLLAMA_REQUEST_TIMEOUT_SECONDS` 같은 값은 직접 fallback으로 읽지 않고, `load_settings()`가 성공적으로 해석한 결과를 통해 반영된다.

관련 설정 필드:
- `OLLAMA_HOST` 예: `http://ollama:11434`
- `OLLAMA_GENERATION_MODEL` 예: `gpt-oss:20b`
- `OLLAMA_REQUEST_TIMEOUT_SECONDS` 기본값 없음
- `OLLAMA_GENERATE__BASE_URL` 기본값: `https://ollama.com`
- `OLLAMA_GENERATE__MODEL` 기본값: `gpt-oss:20b`
- `OLLAMA_GENERATE__TIMEOUT` 기본값: `30.0`
- `OLLAMA_GENERATE__API_KEY` 기본값 없음

인증/헤더:
- `headers`를 직접 주지 않으면 기본적으로 `{"Authorization": f"Bearer {api_key}"}` 헤더를 사용한다.
- `headers`를 직접 주면 기본 Authorization 헤더 대신 전달한 헤더를 그대로 사용한다.

주의:
- `model` 인자와 `OLLAMA_GENERATE__MODEL`이 모두 비어 있으면 `ValueError`가 발생한다.
- `api_key` 인자와 `OLLAMA_GENERATE__API_KEY`가 모두 비어 있으면 `ValueError`가 발생한다.
- Ollama 호출 실패 시 `RuntimeError("Failed to generate response from Ollama")`가 발생한다.
- 응답에 `message.content`가 없거나 형식이 다르면 `RuntimeError("Ollama returned a malformed generation response")`가 발생한다.
- `docmesh_py_core.load_settings()`가 실패하면 generation client 초기화도 즉시 실패한다.
- 단, `docmesh_py_core`의 `ollama` service client를 성공적으로 만든 경우에는 별도 `api_key` 없이 그 client를 그대로 사용할 수 있다.

### 4.4 생성자 파라미터

- `embedding_client`: `embed(texts: list[str]) -> list[list[float]]`를 제공하는 객체
- `generation_client`: `generate(prompt: str) -> str`를 제공하는 객체
- `metadata_path`: SQLite DB 파일 경로
- `document_storage_dir`: local 문서 자산 저장 경로
- `storage_mode`: `"memory" | "local"`
- `chunk_size`: 청크 길이
- `chunk_overlap`: 청크 overlap 길이

---

## 5. Public API

### 5.1 `ingest_text`

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
- `job_id`가 부여된 ingestion 실행 결과를 반환한다.
- 텍스트를 전처리/청킹/임베딩한다.
- 문서 자산을 저장한다.
- 문서/청크 메타데이터를 persistence에 기록한다.
- vector store에 청크를 적재한다.

---

### 5.2 `ingest_file_stream`

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

### 5.3 `ingest_file_path`

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

### 5.4 `query`

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

### 5.5 `list_documents`

현재 user scope의 문서 목록을 반환한다.

```python
documents = core.list_documents(token="user-token-a")
```

#### 시그니처

```python
list_documents(token: str | None = None) -> list[DocumentRecord]
```

---

### 5.6 `get_document`

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

### 5.7 `list_document_chunks`

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

### 5.8 `list_ingestion_progress`

특정 문서의 ingestion 파이프라인 진행 상태를 현재 user scope 기준으로 반환한다.

```python
progress_rows = core.list_ingestion_progress(doc_id, token="user-token-a")
```

#### 시그니처

```python
list_ingestion_progress(
    doc_id: str,
    *,
    token: str | None = None,
    job_id: str | None = None,
) -> list[IngestionProgressRecord]
```

#### 동작
- 지정한 `doc_id`와 현재 user scope가 모두 일치하는 진행 상태 row만 반환한다.
- `job_id`를 주면 특정 ingestion 실행 단위만 필터링할 수 있다.
- 정렬은 pipeline 순서(`step_order`) 기준이다.
- 현재 구현은 단계별 상태 전이를 `running`, `completed`, `failed`로 기록한다.

---

### 5.9 `delete_document`

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
- ingestion progress rows
- stored asset file or memory object
- Milvus Lite vector store entries

---

### 5.10 `health_check`

현재 코어가 사용하는 주요 의존 서비스의 상태를 집계한다.

```python
status = core.health_check()
```

#### 시그니처

```python
health_check() -> object
```

#### 동작
- 항상 metadata store check를 포함한다.
- vector store가 `check()`를 제공하면 `milvus` 항목을 포함한다.
- embedding client가 `check()`를 제공하면 `embedding` 항목을 포함한다.
- generation client가 `check()`를 제공하면 `generation` 항목을 포함한다.
- `docmesh_py_core.check_all_services(...)`를 우선 사용한다.
- 공통 health check 호출 자체가 실패하면 내부 집계 결과로 fallback 한다.

#### integration contract
- `check()` 메서드는 성공 시 `None` 또는 성공을 의미하는 값을 반환하고, 실패 시 예외를 발생시키는 방식이면 충분하다.
- `MilvusLiteVectorStore.check()`는 내부 client의 `check()` 또는 `list_collections()`를 사용한다.
- 기본 제공 Ollama client의 `check()`는 내부 client의 `check()` 또는 `ps()`를 사용한다.

---

## 6. 프롬프트 형식

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

## 7. 저장 구조 개요

### 7.1 Metadata DB
- backend: SQLite
- access layer: SQLAlchemy ORM
- 주요 테이블:
  - `documents`
  - `chunks`
  - `ingestion_progress`

### 7.2 Document storage
- `memory`: `memory://...` logical path 사용
- `local`: 실제 파일 저장 후 path 기록

### 7.3 Retrieval 복원
- 프로세스 시작 시 동일한 Milvus Lite 컬렉션을 다시 열어 retrieval 가능 상태를 복원한다.
- SQLite에는 청크 메타데이터만 유지하고, embedding 벡터는 Milvus Lite가 관리한다.

---

## 8. 사용 예시

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
progress_rows = core.list_ingestion_progress(
    text_result.doc_id,
    token="user-a",
    job_id=text_result.job_id,
)
deleted = core.delete_document(stream_result.doc_id, token="user-a")
```

---

## 9. 알려진 현재 제약

- vector store는 현재 Milvus Lite 기반 로컬 영속 저장소 구현이다.
- token과 user_id의 별도 매핑 저장소는 아직 없다. 현재는 token 문자열 자체를 scope로 사용한다.
- `DOCMESH_AUTH_MODE=keycloak`을 사용할 때는 Keycloak 관련 `docmesh_py_core` 설정이 유효해야 한다. 그렇지 않으면 user id 해석 시 런타임 오류가 발생할 수 있다.
