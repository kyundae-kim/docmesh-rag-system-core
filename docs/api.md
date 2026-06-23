# DocMesh RAG Core Public API Reference

## 1. 목적

이 문서는 **외부 애플리케이션/서비스가 현재 저장소의 코드를 직접 읽지 않고도 첫 호출을 성공시킬 수 있도록** `rag_system_core`의 공개 API만 설명합니다.

이 문서가 보장하려는 범위:
- 어떤 import 경로가 공개 경로인지 안다.
- 어떤 전제조건이 있어야 첫 호출이 성공하는지 안다.
- 어떤 생성 경로가 가장 짧고 안전한지 안다.
- 어떤 메서드와 반환 타입을 사용하는지 안다.

설정값은 `docs/config.md`를 함께 보세요.

## 1.1 용어 기준

본 문서는 `docs/prd.md`, `docs/srs.md`, `docs/test.md`와 동일한 용어 기준을 사용합니다.

- **user scope**: 현재 요청에 대해 해석된 사용자 경계
- **resolved user identity**: token 또는 Keycloak 검증으로부터 해석된 사용자 식별 결과
- **`user_id`**: persistence 및 filtering에 사용되는 저장된 사용자 식별자
- **metadata store**: SQLite + SQLAlchemy 기반 document / chunk / ingestion progress persistence 계층
- **vector store**: Milvus Lite 기반 embedding 저장 및 retrieval 계층
- **document asset storage**: 문서 원문 자산을 `storage_path`로 추적하는 저장 계층
- **restart recovery**: 동일한 metadata store 및 vector store 구성을 다시 열어 상태를 재사용하는 동작
- **health check**: metadata 및 사용 가능한 의존 서비스 상태를 집계하는 점검 동작

---

## 2. 첫 호출 전에 필요한 것

## 2.1 Python / 패키지 전제조건

현재 저장소 기준 전제조건:
- Python `>= 3.11`
- `docmesh-py-core`
- `pydantic-settings`
- `pymilvus[milvus-lite]`

`pyproject.toml` 기준 기본 의존성:

```toml
requires-python = ">=3.11"
dependencies = [
  "docmesh-py-core",
  "pydantic-settings>=2.14.1",
  "pymilvus[milvus-lite]>=3.0.0",
]
```

권장 설치:

```bash
uv sync
```

## 2.2 추가 런타임 의존성: `ollama`

현재 코드 기준으로 `RAGCore` 또는 기본 제공 Ollama adapter를 실제로 import/사용하려면 Python 패키지 `ollama`도 필요합니다.

이유:
- `rag_system_core.adapters.__init__`가 `rag_system_core.adapters.ollama`를 import합니다.
- `rag_system_core.adapters.ollama`는 `import ollama`를 수행합니다.

따라서 현재 환경에 `ollama`가 없으면 다음과 같은 오류가 날 수 있습니다.

```text
ModuleNotFoundError: No module named 'ollama'
```

필요 시 설치:

```bash
uv pip install ollama
```

## 2.3 외부 런타임 전제조건

첫 성공 호출을 위해서는 아래가 준비되어 있어야 합니다.

- Ollama 서버가 접근 가능해야 함
- embedding 모델이 준비되어 있어야 함
- generation 모델이 준비되어 있어야 함
- metadata store / vector store 파일을 생성할 수 있는 쓰기 가능한 디렉터리가 있어야 함

문서에서 사용하는 기본 예시 값:
- Ollama host: `http://ollama:11434`
- embedding model: `bge-m3`
- generation model: `gpt-oss:20b`

> 모델이 Ollama에 실제로 존재하지 않거나 pull되지 않았다면 첫 호출은 실패합니다.

---

## 3. 공개 import 경로

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

다음 경로들은 현재 존재하지만 공개 API 문서의 사용 대상이 아닙니다.

- `rag_system_core.domain.*`
- `rag_system_core.storage.*`
- `rag_system_core.composition.*`
- `rag_system_core.adapters.*`
- `rag_system_core.core`

---

## 4. 가장 짧은 성공 경로

현재 문서 기준 **가장 짧고 예측 가능한 첫 성공 경로는 `bootstrap_rag_core_from_docmesh(...)`가 아니라 `RAGCore(...)` 직접 생성**입니다.

이유:
- `bootstrap_rag_core_from_docmesh(...)`는 DocMesh settings 로드와 service registry 생성에 의존합니다.
- 반면 `RAGCore(...)` 직접 생성은 embedding / generation client만 직접 준비하면 더 적은 전제조건으로 동작합니다.

### 4.1 권장 첫 성공 순서

1. 의존성 설치
2. `ollama` Python 패키지 설치 확인
3. `docs/config.md` 기준으로 최소 env 준비
4. Ollama 서버와 모델 준비 확인
5. `RAGCore(...)`를 직접 생성
6. `ingest_text(...)`
7. `query(...)`

### 4.2 최소 성공 예시

```python
import os
from pathlib import Path

import ollama
from rag_system_core import RAGCore, OllamaEmbeddingClient, OllamaGenerationClient

ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
embedding_model = os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3")
generation_model = os.getenv("OLLAMA_GENERATION_MODEL", "gpt-oss:20b")

client = ollama.Client(host=ollama_host)

core = RAGCore(
    embedding_client=OllamaEmbeddingClient(client=client, model=embedding_model),
    generation_client=OllamaGenerationClient(client=client, model=generation_model),
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

이 경로의 특징:
- `DOCMESH_AUTH_MODE`를 건드리지 않으면 single-user 기본 흐름으로 동작
- DocMesh service registry 없이도 시작 가능
- Milvus URI가 없으면 `metadata_path.with_suffix(".milvus.db")` fallback 사용 가능

---

## 5. 공개 생성 경로

### 5.1 `RAGCore`

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
| `metadata_path` | metadata store(SQLite) 파일 경로 |
| `document_storage_dir` | document asset storage 디렉터리 |
| `storage_mode` | `"memory"` 또는 `"local"` |
| `chunk_size` | chunk 크기 |
| `chunk_overlap` | chunk overlap 크기 |
| `vector_store` | 선택적 사용자 제공 vector store |

중요:
- `storage_mode` 기본값은 `"memory"`
- `vector_store`를 직접 주지 않으면 내부에서 Milvus Lite 기반 vector store를 생성
- Milvus 설정을 찾지 못하면 `metadata_path.with_suffix(".milvus.db")`, `rag_chunks`, `30.0`을 fallback으로 사용

### 5.2 `bootstrap_rag_core_from_docmesh`

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

이 helper는 공개 API로 export됩니다. 하지만 **첫 성공 경로로는 direct construction보다 전제조건이 많습니다.**

이 helper를 쓰려면:
- `docmesh_py_core.load_settings()`가 성공해야 함
- `create_service_registry(settings)`가 성공해야 함
- registry가 `ollama` client를 생성할 수 있어야 함
- settings에서 embedding/generation 모델을 읽을 수 있어야 함

즉, 이 helper는 **이미 DocMesh 설정/registry 계약이 준비된 환경에서 쓰는 convenience path**로 보는 것이 안전합니다.

---

## 6. 공개 타입과 클라이언트 계약

### 6.1 `EmbeddingClient`

```python
class EmbeddingClient(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
```

계약:
- 입력은 `list[str]`
- 반환은 `list[list[float]]`
- 반환 벡터 수는 입력 텍스트 수와 같아야 함
- 벡터 차원은 일관되어야 함
- query 경로는 질문 1개에 대해 최소 1개 벡터를 기대함

### 6.2 `GenerationClient`

```python
class GenerationClient(Protocol):
    def generate(self, prompt: str) -> str: ...
```

계약:
- 입력은 완성된 단일 프롬프트 문자열
- 반환은 최종 답변 문자열 `str`

### 6.3 `DocumentRecord`

```python
@dataclass(slots=True)
class DocumentRecord:
    doc_id: str
    user_id: str
    source: str
    created_at: str
    storage_path: str | None = None
```

### 6.4 `ChunkRecord`

```python
@dataclass(slots=True)
class ChunkRecord:
    chunk_id: str
    doc_id: str
    user_id: str
    content: str
    metadata: dict[str, str]
```

### 6.5 `IngestResult`

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

### 6.6 `IngestionProgressRecord`

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

### 6.7 `QueryResult`

```python
@dataclass(slots=True)
class QueryResult:
    answer: str
    prompt: str
    context_chunks: list[ChunkRecord]
```

---

## 7. 공개 메서드

### 7.1 `ingest_text`

```python
ingest_text(*, text: str, source: str, token: str | None = None) -> IngestResult
```

주의:
- 전처리 후 빈 문자열이면 실패할 수 있음

### 7.2 `ingest_file_stream`

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
- 현재 구현은 UTF-8 decode 가능한 텍스트 스트림을 전제

### 7.3 `ingest_file_path`

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
- 현재 구현은 UTF-8 decode 가능한 텍스트 파일을 전제

### 7.4 `query`

```python
query(*, question: str, top_k: int = 3, token: str | None = None) -> QueryResult
```

반환:
- `answer`: 최종 답변 문자열
- `prompt`: 실제 생성에 사용된 프롬프트
- `context_chunks`: 검색된 chunk 목록

### 7.5 `list_documents`

```python
list_documents(token: str | None = None) -> list[DocumentRecord]
```

### 7.6 `get_document`

```python
get_document(doc_id: str, *, token: str | None = None) -> DocumentRecord | None
```

### 7.7 `list_document_chunks`

```python
list_document_chunks(doc_id: str, *, token: str | None = None) -> list[ChunkRecord]
```

### 7.8 `list_ingestion_progress`

```python
list_ingestion_progress(
    doc_id: str,
    *,
    token: str | None = None,
    job_id: str | None = None,
) -> list[IngestionProgressRecord]
```

### 7.9 `delete_document`

```python
delete_document(doc_id: str, *, token: str | None = None) -> bool
```

반환:
- `True`: 삭제 성공
- `False`: 대상 문서가 없거나 현재 user scope에 없음

중요 제약:
- vector store 삭제가 먼저 수행됨
- vector store 삭제 실패 시 metadata/asset 삭제가 수행되지 않을 수 있음

### 7.10 `health_check`

```python
health_check() -> object
```

의미:
- metadata store 및 사용 가능한 의존 서비스 상태를 집계한다.

---

## 8. user scope / resolved user identity 규칙

기본 규칙:
- `token is None` → `single-user`
- `token.strip() == ""` → `single-user`
- 그 외 → token 문자열 자체를 resolved user identity이자 `user_id`로 사용

첫 성공 호출을 목표로 한다면:
- `DOCMESH_AUTH_MODE`를 설정하지 말고
- `token`도 생략하는 single-user 흐름이 가장 단순합니다.

Keycloak 모드:
- `DOCMESH_AUTH_MODE=keycloak`이면 Keycloak 검증을 통해 resolved user identity / `user_id`를 해석
- 관련 설정은 `docs/config.md` 참고
- 이 경로는 첫 성공 경로가 아니라 고급/통합 경로로 보는 것이 안전함

---

## 9. 공개 제공 Ollama adapter

현재 패키지는 공개 export로 다음 adapter를 제공합니다.

### 9.1 `OllamaEmbeddingClient`

```python
OllamaEmbeddingClient(*, client, model: str)
```

계약:
- `client.embed(model=..., input=...)`를 호출할 수 있어야 함
- 응답은 `embeddings` 배열을 제공해야 함
- `model`이 비어 있으면 `ValueError`

### 9.2 `OllamaGenerationClient`

```python
OllamaGenerationClient(*, client, model: str)
```

계약:
- `client.chat(model=..., messages=[...])`를 호출할 수 있어야 함
- 응답은 `message.content`를 제공해야 함
- `model`이 비어 있으면 `ValueError`

> 이 두 클래스는 공개 API이지만, 이미 생성된 Ollama 호환 client를 주입받는 adapter입니다.

---

## 10. 문서만으로 첫 호출을 성공시키기 위한 체크리스트

- [ ] `uv sync`를 실행했다
- [ ] Python 패키지 `ollama`가 설치되어 있다
- [ ] Ollama 서버가 접근 가능하다
- [ ] embedding / generation 모델이 준비되어 있다
- [ ] `docs/config.md` 기준 최소 env가 준비되어 있다
- [ ] `./data/` 아래 파일을 쓸 수 있다
- [ ] 첫 시도는 `bootstrap_rag_core_from_docmesh(...)`가 아니라 `RAGCore(...)` 직접 생성 경로를 사용한다
- [ ] 첫 시도는 Keycloak이 아니라 single-user 기본 흐름을 사용한다

---

## 11. 비공개 범위 / non-goals

다음은 이 문서의 범위 밖입니다.
- 내부 모듈 경로별 구현 설명
- ORM 모델과 내부 저장 상세 구현
- 내부 composition helper/factory 사용법 상세
- 내부 prompt builder 구조 세부사항
- 내부 vector store 구현 세부사항

외부 연동은 이 문서의 공개 import 경로와 메서드 계약만 기준으로 하세요.
