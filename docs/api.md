# DocMesh RAG Core API Reference

## 1. 개요

이 문서는 **현재 저장소에 구현된 코드 기준**으로 `rag_system_core`의 public API와 연동 계약을 설명한다.
목표는 외부 애플리케이션이 소스코드를 직접 읽지 않고도 `RAGCore`를 생성하고, 문서를 적재하고, 검색/질의하고, 운영 시 제약을 이해할 수 있게 만드는 것이다.

### 1.1 이 문서가 다루는 범위
- 패키지 루트(`rag_system_core`)에서 공개하는 안정적 import 경로
- `RAGCore` 생성자와 public method
- 반환 타입과 client protocol
- 기본 제공 Ollama adapter의 **실제 생성자 계약**
- DocMesh 런타임 설정/서비스 팩토리 연동 방식
- 저장 구조, health check, 현재 제약

### 1.2 핵심 구현 원칙
- 기본 사용자 식별은 `token -> user_id` 직접 매핑이다.
- `token`이 없거나 공백이면 `single-user` 스코프를 사용한다.
- `DOCMESH_AUTH_MODE=keycloak`일 때만 Keycloak 검증을 통해 `user_id`를 해석한다.
- 문서 본문은 metadata DB에 직접 저장하지 않고 `storage_path`가 가리키는 managed asset으로 저장한다.
- metadata는 SQLite에, 벡터는 Milvus Lite 컬렉션에 저장한다.
- 재시작 복원은 **같은 Milvus 설정/컬렉션을 다시 여는 방식**으로 동작한다.

---

## 2. Public import surface

### 2.1 패키지 루트에서 공개하는 import

공식적으로 문서화된 루트 import는 다음과 같다.

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

패키지 루트 `__all__`에는 위 이름들이 포함되어 있으며, `RAGCore`, Ollama client, bootstrap helper는 lazy import로 노출된다.

### 2.2 타입 전용 import

타입과 protocol은 별도 모듈에서도 직접 import할 수 있다.

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

### 2.3 구현 세부 모듈 import에 대한 주의

다음 경로들은 현재 존재하지만, 외부 통합에서는 **구현 세부사항**으로 간주하는 것이 안전하다.

- `rag_system_core.domain.*`
- `rag_system_core.storage.*`
- `rag_system_core.composition.*`
- `rag_system_core.adapters.*`
- `rag_system_core.core`

예외적으로 `rag_system_core.core`는 여러 내부 클래스와 ORM model을 재노출하지만, 장기 호환 계약은 패키지 루트와 `rag_system_core.types` 기준으로 보는 것이 좋다.

---

## 3. Public return models / protocols

### 3.1 `EmbeddingClient`

```python
class EmbeddingClient(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
```

계약:
- 입력은 `list[str]`
- 반환은 `list[list[float]]`
- 반환 벡터 수는 입력 텍스트 수와 같아야 함
- 같은 vector store 컬렉션에 저장되는 벡터는 차원이 일관되어야 함
- query 경로는 `embed([question])[0]`를 사용하므로 최소 1개 벡터를 반환해야 함

### 3.2 `GenerationClient`

```python
class GenerationClient(Protocol):
    def generate(self, prompt: str) -> str: ...
```

계약:
- 입력은 완성된 단일 프롬프트 문자열
- 반환은 최종 답변 문자열 `str`
- structured object나 message list가 아니라 plain text를 반환해야 함

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
    metadata: dict[str, str] = field(default_factory=dict)
```

현재 구현에서 chunk metadata에는 기본적으로 `{"source": <source>}`가 들어간다.

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

## 4. `RAGCore`

### 4.1 생성자 시그니처

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
    vector_store: VectorStore | None = None,
)
```

중요:
- `storage_mode` 기본값은 **`"memory"`** 이다.
- `vector_store`를 주지 않으면 내부에서 Milvus Lite 기반 store를 생성한다.
- `metadata_path`는 SQLite 파일 경로로 사용된다.
- `document_storage_dir`는 `storage_mode="local"`일 때 managed asset 저장 디렉터리로 사용된다.

### 4.2 파라미터 의미

| 파라미터 | 설명 |
|---|---|
| `embedding_client` | `embed(texts)`를 제공하는 embedding adapter |
| `generation_client` | `generate(prompt)`를 제공하는 generation adapter |
| `metadata_path` | SQLite metadata DB 파일 경로 |
| `document_storage_dir` | 문서 자산 저장 디렉터리 |
| `storage_mode` | `"memory"` 또는 `"local"` |
| `chunk_size` | 고정 길이 chunk 크기 |
| `chunk_overlap` | 인접 chunk overlap 길이 |
| `vector_store` | 선택적 사용자 제공 vector store 구현 |

### 4.3 내부 구성

`RAGCore`는 현재 다음 구성요소를 묶는 orchestration entry point다.

- `MetadataStore`
- `DocumentStorage`
- `IngestionService`
- `RetrievalService`
- `GenerationService`
- `MilvusLiteVectorStore` (직접 주입하지 않은 경우)

---

## 5. 사용자 식별 규칙

사용자 스코프 해석은 `rag_system_core.composition.auth.resolve_user_id()`를 통해 수행된다.

기본 규칙:
- `token is None` → `single-user`
- `token.strip() == ""` → `single-user`
- 그 외 → 기본적으로 token 문자열 자체를 `user_id`로 사용

Keycloak 모드:
- `DOCMESH_AUTH_MODE=keycloak`이면 token 문자열을 그대로 user_id로 쓰지 않는다.
- `docmesh_py_core.load_settings()`와 `KeycloakAuthService`를 사용해 토큰을 검증한다.
- 우선 `sub`, 없으면 `preferred_username`을 user_id로 사용한다.
- 둘 다 없으면 `RuntimeError`가 발생한다.

---

## 6. Public methods

### 6.1 `ingest_text`

```python
ingest_text(*, text: str, source: str, token: str | None = None) -> IngestResult
```

예시:

```python
result = core.ingest_text(
    text="alpha beta gamma",
    source="note.txt",
    token="user-token-a",
)
```

동작:
1. `token`을 `user_id`로 해석한다.
2. 텍스트를 `strip()` 기반으로 전처리한다.
3. managed asset에 저장한다.
4. 문서를 chunking 한다.
5. embedding을 **배치 1회 호출**로 생성한다.
6. Milvus Lite에 저장해 chunk id를 받는다.
7. SQLite metadata에 chunk/document/progress를 기록한다.

주의:
- 전처리 후 비어 있으면 chunking 단계에서 `ValueError("Document must contain non-empty text")`가 발생한다.

### 6.2 `ingest_file_stream`

```python
ingest_file_stream(
    *,
    file_stream: BinaryIO,
    source: str | None = None,
    token: str | None = None,
) -> IngestResult
```

예시:

```python
from io import BytesIO

result = core.ingest_file_stream(
    file_stream=BytesIO(b"document from stream"),
    source="stream.txt",
    token="user-token-a",
)
```

주의:
- `source`는 실질적으로 필수다.
- `source is None` 또는 공백이면 `ValueError("source is required for stream ingestion")`가 발생한다.
- 현재 구현은 파일 스트림 바이트를 UTF-8로 decode 한다.

### 6.3 `ingest_file_path`

```python
ingest_file_path(
    *,
    file_path: str | Path,
    token: str | None = None,
    source: str | None = None,
) -> IngestResult
```

동작:
- `source`를 생략하면 `file_path.name`을 사용한다.
- 파일 내용을 읽어 UTF-8로 decode 한다.
- 실제 managed asset 이름은 원본 파일명이 아니라 `doc_id + suffix` 형태가 된다.

### 6.4 `query`

```python
query(*, question: str, top_k: int = 3, token: str | None = None) -> QueryResult
```

동작:
- 질문을 embedding 한다.
- 현재 `user_id` 범위로 Milvus 검색을 수행한다.
- 검색된 chunk로 prompt를 조립한다.
- generation client의 `generate(prompt)`를 호출한다.

반환:
- `answer`: 최종 텍스트 답변
- `prompt`: 실제 전달된 프롬프트
- `context_chunks`: 검색된 chunk 목록

### 6.5 `list_documents`

```python
list_documents(token: str | None = None) -> list[DocumentRecord]
```

동작:
- 현재 user scope의 문서만 반환
- `created_at` 기준 정렬

### 6.6 `get_document`

```python
get_document(doc_id: str, *, token: str | None = None) -> DocumentRecord | None
```

동작:
- `doc_id`와 `user_id`가 모두 일치하는 문서만 반환
- 범위 밖 문서거나 없으면 `None`

### 6.7 `list_document_chunks`

```python
list_document_chunks(doc_id: str, *, token: str | None = None) -> list[ChunkRecord]
```

동작:
- `doc_id` + 현재 user scope 기준으로 chunk 반환
- `chunk_index` 순서로 정렬

### 6.8 `list_ingestion_progress`

```python
list_ingestion_progress(
    doc_id: str,
    *,
    token: str | None = None,
    job_id: str | None = None,
) -> list[IngestionProgressRecord]
```

동작:
- 현재 user scope에 속한 진행 상태만 반환
- `job_id`를 주면 특정 ingestion 실행만 필터링
- `step_order`, `created_at` 기준 정렬

파이프라인 단계 순서:
1. `load`
2. `preprocess`
3. `chunking`
4. `embedding`
5. `vector_store`
6. `chunk_persistence`

상태 전이:
- 정상 단계는 `running` → `completed`
- 실패 가능 단계에서는 `failed` row가 남을 수 있음

### 6.9 `delete_document`

```python
delete_document(doc_id: str, *, token: str | None = None) -> bool
```

정상 삭제 순서:
1. 현재 user scope에서 문서 조회
2. vector store에서 `doc_id` 기준 삭제
3. SQLite metadata에서 document/chunk/ingestion progress 삭제
4. managed asset 삭제

반환:
- `True`: 삭제 성공
- `False`: 대상 문서가 없거나 현재 user scope에 없음

중요 제약:
- vector store 삭제가 먼저 수행된다.
- vector store 삭제에서 예외가 발생하면 metadata와 asset 삭제는 수행되지 않는다.
- 즉, 현재 구현은 전체 삭제를 하나의 원자적 트랜잭션으로 보장하지 않는다. 다만 실패 후 재시도는 가능하도록 동작한다.

### 6.10 `health_check`

```python
health_check() -> object
```

동작:
- 항상 metadata store check 포함
- vector store가 `check()`를 제공하면 `milvus` 포함
- embedding client가 `check()`를 제공하면 `embedding` 포함
- generation client가 `check()`를 제공하면 `generation` 포함
- 가능하면 `docmesh_py_core.check_all_services(...)`를 사용
- 공통 집계 호출 실패 시 로컬 집계 결과로 fallback

로컬 fallback 결과 shape:
- `LocalHealthCheckResult(ok: bool, services: list[LocalHealthServiceResult])`
- 각 service row는 `service`, `ok`, `error` 필드를 가짐

---

## 7. 생성 프롬프트 형식

현재 `GenerationService.build_prompt()`는 다음 형식을 사용한다.

```text
[System Prompt]
You are a helpful RAG assistant. Answer only from the retrieved context.

[Retrieved Context]
<chunk 1>

<chunk 2>

[User Query]
<question>
```

검색 결과가 없으면 context 영역에는 `No context retrieved.`가 들어간다.

---

## 8. 기본 제공 Ollama adapter

## 8.1 중요한 사실

현재 코드 기준으로 `OllamaEmbeddingClient`, `OllamaGenerationClient`는 **직접 HTTP 설정을 받는 고수준 client가 아니다.**
이 두 클래스는 이미 생성된 Ollama 호환 client 객체를 주입받는 얇은 adapter다.

### 8.2 `OllamaEmbeddingClient`

```python
OllamaEmbeddingClient(*, client: Any, model: str)
```

동작:
- `client.embed(model=self.model, input=texts)` 호출
- 응답의 `response["embeddings"]`를 읽음
- 빈 입력이면 `[]` 반환
- transport 오류는 `RuntimeError("Failed to fetch embeddings from Ollama")`로 감싼다
- malformed response는 `RuntimeError("Ollama returned a malformed embeddings response")`

health check:
- 내부 client에 `check()`가 있으면 사용
- 없고 `ps()`가 있으면 사용
- 둘 다 없으면 `RuntimeError`

### 8.3 `OllamaGenerationClient`

```python
OllamaGenerationClient(*, client: Any, model: str)
```

동작:
- `client.chat(model=self.model, messages=[{"role": "user", "content": prompt}])` 호출
- 응답의 `response["message"]["content"]`를 읽어 문자열 반환
- transport 오류는 `RuntimeError("Failed to generate response from Ollama")`
- malformed response는 `RuntimeError("Ollama returned a malformed generation response")`

health check:
- 내부 client에 `check()`가 있으면 사용
- 없고 `ps()`가 있으면 사용
- 둘 다 없으면 `RuntimeError`

### 8.4 권장 생성 경로: factory 사용

직접 `client`를 만들기보다 아래 factory/helper를 사용하는 편이 안전하다.

```python
from rag_system_core.composition.factories import (
    create_rag_embedding_client,
    create_rag_generation_client,
)
```

factory 동작:
- `docmesh_py_core` service registry에서 `ollama` client 생성을 우선 시도
- settings의 `ollama.embedding_model`, `ollama.generation_model`을 읽음
- 명시적 override가 없고 model 설정이 비어 있으면 `ValueError`

---

## 9. Bootstrap helper

패키지 루트는 `bootstrap_rag_core_from_docmesh`를 공개한다.

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

동작:
- DocMesh settings 로드
- service registry 생성
- registry를 통해 embedding/generation client 생성
- DocMesh 설정 기반 vector store 생성
- 최종적으로 `RAGCore(...)` 반환

주의:
- 이 helper의 기본 `storage_mode`는 `"local"`이다.
- 반면 `RAGCore` 생성자 자체의 기본값은 `"memory"`이다.

---

## 10. Runtime configuration

### 10.1 Milvus runtime resolution

`RAGCore`가 내부 vector store를 생성할 때:
- 우선 `docmesh_py_core` 설정에서 Milvus 정보를 읽는다.
- 읽을 수 없으면 fallback을 사용한다.

fallback 기본값:
- `uri`: `metadata_path.with_suffix(".milvus.db")`
- `collection_name`: `rag_chunks`
- `timeout`: `30.0`

DocMesh 설정에서 읽는 필드:
- `milvus.uri`
- `milvus.collection` 또는 `milvus.collection_name`
- `milvus.request_timeout_seconds` 또는 `milvus.connect_timeout_seconds`

### 10.2 서비스 클라이언트 생성 우선순위

일부 경로는 `docmesh_py_core.ServiceFactoryRegistry`를 통해 client 생성을 시도한다.

- `ollama` 서비스 client
- `milvus` 서비스 client

생성 실패/설정 부재 시 fallback:
- embedding/generation factory는 usable `ollama` client가 없으면 실패
- `RAGCore` 내부 vector store 생성은 직접 `MilvusClient(uri=..., timeout=...)`로 fallback 가능

---

## 11. 저장 구조

### 11.1 SQLite metadata

테이블:
- `documents`
- `chunks`
- `ingestion_progress`

#### `documents`
- `doc_id`
- `user_id`
- `source`
- `created_at`
- `storage_path`

#### `chunks`
- `chunk_id`
- `doc_id`
- `user_id`
- `chunk_index`
- `content`
- `metadata_json`

#### `ingestion_progress`
- `progress_id`
- `job_id`
- `doc_id`
- `user_id`
- `source`
- `step_name`
- `step_order`
- `status`
- `created_at`

### 11.2 Document storage

`memory` 모드:
- `memory://<doc_id>/<source>` logical path 사용
- 본문은 process memory dict에 저장
- 재시작 후 자산은 유지되지 않음

`local` 모드:
- 실제 파일을 `document_storage_dir/<doc_id><suffix>` 형식으로 저장
- 원본 파일명은 metadata `source`로 유지되지만, 저장 파일명 자체는 `doc_id` 기반으로 바뀐다

### 11.3 Vector store

기본 구현은 `MilvusLiteVectorStore`이다.

특징:
- `chunk_id`는 Milvus auto id를 사용
- 검색 시 `user_id == "..."` filter 적용
- `doc_id` 기준 삭제 지원
- Milvus collection이 없으면 첫 insert 때 dimension 기준으로 생성

---

## 12. 사용 예시

### 12.1 직접 조립

```python
from pathlib import Path
from rag_system_core import RAGCore
from rag_system_core.composition.factories import (
    create_rag_embedding_client,
    create_rag_generation_client,
)
from rag_system_core.composition.docmesh_runtime import load_docmesh_settings

settings = load_docmesh_settings()
embedding_client = create_rag_embedding_client(settings=settings)
generation_client = create_rag_generation_client(settings=settings)

core = RAGCore(
    embedding_client=embedding_client,
    generation_client=generation_client,
    metadata_path=Path("./data/metadata.db"),
    document_storage_dir=Path("./data/documents"),
    storage_mode="local",
)
```

### 12.2 bootstrap helper 사용

```python
from pathlib import Path
from rag_system_core import bootstrap_rag_core_from_docmesh

core = bootstrap_rag_core_from_docmesh(
    metadata_path=Path("./data/metadata.db"),
    document_storage_dir=Path("./data/documents"),
    storage_mode="local",
)
```

### 12.3 문서 적재 / 질의 / 관리

```python
from io import BytesIO
from pathlib import Path

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

documents = core.list_documents(token="user-a")
document = core.get_document(text_result.doc_id, token="user-a")
chunks = core.list_document_chunks(text_result.doc_id, token="user-a")
progress_rows = core.list_ingestion_progress(text_result.doc_id, token="user-a", job_id=text_result.job_id)
status = core.health_check()
deleted = core.delete_document(stream_result.doc_id, token="user-a")
```

---

## 13. 현재 제약 / non-goals

- vector store 기본 구현은 Milvus Lite 단일 컬렉션 기반이다.
- 강한 의미의 distributed / production-grade vector DB 운영은 범위 밖이다.
- 문서 파일/스트림 ingestion은 현재 UTF-8 decode 가능한 텍스트를 전제로 한다.
- delete는 vector store와 metadata/asset 사이의 완전한 분산 트랜잭션을 제공하지 않는다.
- `memory` storage mode의 문서 자산은 재시작 시 복원되지 않는다.
- `DOCMESH_AUTH_MODE=keycloak`을 사용할 때는 DocMesh Keycloak 설정이 유효해야 한다.
- `rag_system_core.core`가 많은 내부 심볼을 export하지만, 외부 연동의 안정 경로로는 패키지 루트와 `rag_system_core.types`를 권장한다.
