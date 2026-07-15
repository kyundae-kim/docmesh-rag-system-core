# DocMesh RAG Core Public API Reference

## 1. 목적

이 문서는 현재 저장소의 **실제 구현 기준**으로 `rag_system_core`의 공개 API와 사용 경로를 설명한다.

이 문서가 보장하는 범위:
- 어떤 import 경로가 현재 공개적으로 사용 가능한지
- `RAGCore`를 실제 코드와 일치하게 어떻게 조립하는지
- ingestion / query / document management API가 무엇인지
- 어떤 타입과 helper가 외부 사용 관점에서 의미가 있는지

설정 관련 세부값은 `docs/config.md`를 함께 본다.

## 1.1 용어 기준

본 문서는 `docs/prd.md`, `docs/srs.md`, `docs/test.md`와 동일한 용어 기준을 사용한다.

- **user scope**: 현재 요청에 대해 해석된 사용자 경계
- **authenticated user**: 상위 애플리케이션이 전달하는 `docmesh_py_core.AuthenticatedUser`
- **`user_id`**: persistence 및 filtering에 사용되는 저장된 사용자 식별자
- **metadata store**: SQLite + SQLAlchemy 기반 document / chunk / ingestion progress persistence 계층
- **vector store**: Milvus Lite 기반 embedding 저장 및 retrieval 계층
- **document asset storage**: 문서 원문 자산을 `storage_path`로 추적하는 저장 계층
- **restart recovery**: 동일한 metadata store 및 vector store 구성을 다시 열어 상태를 재사용하는 동작
- **health check**: metadata 및 사용 가능한 의존 서비스 상태를 집계하는 점검 동작

---

## 2. 런타임 전제조건

### 2.1 Python / 패키지 전제조건

`pyproject.toml` 기준:

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

### 2.2 Ollama Python 패키지

현재 구현에서 제공하는 `OllamaEmbeddingClient`, `OllamaGenerationClient`, `create_rag_embedding_client(...)`, `create_rag_generation_client(...)`를 사용하려면 Python 패키지 `ollama`가 설치되어 있어야 한다.

필요 시:

```bash
uv pip install ollama
```

### 2.3 외부 런타임 전제조건

현재 기본 조합으로 첫 성공 호출을 만들려면 보통 아래가 필요하다.

- writable metadata store 경로
- writable document asset storage 디렉터리
- Milvus Lite 파일을 생성할 수 있는 경로
- embedding / generation 호출 가능한 모델 런타임

DocMesh 통합 환경에서 자주 쓰는 예시 값:

- Ollama host: `http://ollama`
- embedding model: `bge-m3`
- generation model: `gpt-oss:20b`

---

## 3. 공개 import 경로

### 3.1 패키지 루트 export

현재 `rag_system_core.__all__` 기준 루트 공개 export:

```python
from rag_system_core import (
    AuthenticatedUser,
    RAGCore,
    OllamaEmbeddingClient,
    OllamaGenerationClient,
    bootstrap_rag_core,
    DocmeshRAGServiceFactory,
    RAGServiceFactory,
    DocumentRecord,
    ChunkRecord,
    IngestResult,
    IngestionProgressRecord,
    QueryResult,
    EmbeddingClient,
    GenerationClient,
)
```

### 3.2 타입 import 경로

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

### 3.3 Composition helper import 경로

구성용 helper는 현재 다음 경로에서 사용한다.

```python
from rag_system_core.composition.factories import (
    create_rag_embedding_client,
    create_rag_generation_client,
    create_rag_vector_store,
    create_rag_metadata_store,
    create_rag_document_storage,
    create_rag_chunker,
)
```

```python
from rag_system_core.composition.bootstrap import bootstrap_rag_core
```

### 3.4 공개 API로 보지 않는 내부 경로

아래는 현재 구현 파일이지만 외부 사용 문서의 주 대상은 아니다.

- `rag_system_core.domain.*`
- `rag_system_core.storage.*`
- `rag_system_core.adapters.*`
- `rag_system_core.core`

다만 현재 일부 테스트와 고급 통합 코드는 `rag_system_core.composition.factories`를 직접 사용한다.

---

## 4. 실제 생성 경로

## 4.1 가장 직접적인 생성 경로: `RAGCore(...)`

현재 구현에서 `RAGCore`는 아래 의존성을 **직접 주입받는 조립형 생성자**다.

```python
RAGCore(
    *,
    embedding_client: EmbeddingClient,
    generation_client: GenerationClient,
    vector_store: VectorStore,
    metadata_store: MetadataStore,
    document_storage: DocumentStorage,
    chunker: FixedWindowChunker,
)
```

즉, 이전 문서처럼 `metadata_path`, `document_storage_dir`, `storage_mode`, `chunk_size`, `chunk_overlap`를 `RAGCore` 생성자에 바로 넘기는 방식은 **현재 코드와 일치하지 않는다**.

### 4.2 실용적인 첫 성공 경로: factory helper + `RAGCore(...)`

현재 저장소의 테스트와 구현에 가장 잘 맞는 첫 성공 경로는 factory helper로 구성요소를 만든 뒤 `RAGCore(...)`를 조립하는 방식이다.

```python
from pathlib import Path

from rag_system_core import RAGCore
from rag_system_core.composition.factories import (
    create_rag_chunker,
    create_rag_document_storage,
    create_rag_embedding_client,
    create_rag_generation_client,
    create_rag_metadata_store,
    create_rag_vector_store,
)

metadata_path = Path("./data/metadata.db")
document_storage_dir = Path("./data/documents")

core = RAGCore(
    embedding_client=create_rag_embedding_client(),
    generation_client=create_rag_generation_client(),
    vector_store=create_rag_vector_store(metadata_path=metadata_path),
    metadata_store=create_rag_metadata_store(metadata_path=metadata_path),
    document_storage=create_rag_document_storage(
        storage_mode="local",
        document_storage_dir=document_storage_dir,
    ),
    chunker=create_rag_chunker(chunk_size=512, chunk_overlap=64),
)
```

### 4.3 Service factory 기반 helper: `bootstrap_rag_core(...)`

현재 bootstrap helper 이름은 `bootstrap_rag_core(...)`이며, 시그니처는 아래와 같다.

```python
bootstrap_rag_core(
    *,
    service_factory: RAGServiceFactory,
    metadata_path,
    document_storage_dir,
    storage_mode="local",
    chunk_size=512,
    chunk_overlap=64,
)
```

이 helper는 **settings를 직접 로드하지 않는다.**
대신 `service_factory`가 embedding / generation / vector store / metadata store / storage / chunker를 만드는 구조다.

DocMesh settings 연동이 필요하면 보통 `DocmeshRAGServiceFactory(settings=..., registry=...)`와 함께 사용한다.

```python
from rag_system_core import DocmeshRAGServiceFactory, bootstrap_rag_core
from rag_system_core.composition.docmesh_runtime import create_service_registry, load_docmesh_settings

settings = load_docmesh_settings()
registry = create_service_registry(settings)
service_factory = DocmeshRAGServiceFactory(settings=settings, registry=registry)

core = bootstrap_rag_core(
    service_factory=service_factory,
    metadata_path="./data/metadata.db",
    document_storage_dir="./data/documents",
    storage_mode="local",
    chunk_size=512,
    chunk_overlap=64,
)
```

---

## 5. Composition helper 계약

### 5.1 `create_rag_embedding_client`

```python
create_rag_embedding_client(*, settings=None, registry=None, **overrides)
```

동작:
- `overrides["client"]`가 있으면 그 client를 사용
- 아니면 DocMesh service client 생성 시도
- model은 `overrides["model"]` 또는 DocMesh settings에서 읽음
- model이 비어 있으면 `ValueError`

### 5.2 `create_rag_generation_client`

```python
create_rag_generation_client(*, settings=None, registry=None, **overrides)
```

동작은 embedding client factory와 동일한 패턴이며 generation model을 사용한다.

### 5.3 `create_rag_vector_store`

```python
create_rag_vector_store(*, metadata_path: str | Path, settings=None, registry=None, **overrides)
```

동작:
- 가능하면 DocMesh settings에서 Milvus runtime 설정을 읽음
- fallback URI는 `metadata_path.with_suffix(".milvus.db")`
- fallback collection name은 `rag_chunks`
- fallback timeout은 `30.0`
- DocMesh `milvus` client 생성 실패 시 `MilvusClient(uri=..., timeout=...)`를 직접 생성
- 반환 타입은 `MilvusLiteVectorStore`

### 5.4 `create_rag_document_storage`

```python
create_rag_document_storage(*, storage_mode: str, document_storage_dir: str | Path)
```

지원 mode:
- `"memory"`
- `"local"`

### 5.5 `create_rag_metadata_store`

```python
create_rag_metadata_store(*, metadata_path: str | Path)
```

### 5.6 `create_rag_chunker`

```python
create_rag_chunker(*, chunk_size: int, chunk_overlap: int)
```

---

## 6. 공개 타입과 클라이언트 계약

### 6.1 `EmbeddingClient`

```python
class EmbeddingClient(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...
```

### 6.2 `GenerationClient`

```python
class GenerationClient(Protocol):
    def generate(self, prompt: str) -> str: ...
```

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
    metadata: dict[str, str] = field(default_factory=dict)
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
ingest_text(*, user: AuthenticatedUser, text: str, source: str) -> IngestResult
```

동작 요약:
- `user.sub`를 `user_id`로 사용
- text는 `strip()` 전처리 적용
- 빈 텍스트가 되면 `ValueError("Document must contain non-empty text")`

### 7.2 `ingest_file_stream`

```python
ingest_file_stream(
    *,
    user: AuthenticatedUser,
    file_stream,
    source: str | None = None,
) -> IngestResult
```

주의:
- `source`가 없거나 공백이면 `ValueError("source is required for stream ingestion")`
- payload는 UTF-8로 decode 가능해야 함

### 7.3 `ingest_file_path`

```python
ingest_file_path(
    *,
    user: AuthenticatedUser,
    file_path: str | Path,
    source: str | None = None,
) -> IngestResult
```

동작:
- `source` 생략 시 `file_path.name` 사용
- 파일 바이트를 읽어 UTF-8로 decode

### 7.4 `query`

```python
query(*, user: AuthenticatedUser, question: str, top_k: int = 3) -> QueryResult
```

생성되는 prompt 구조:

```text
[System Prompt]
...

[Retrieved Context]
...

[User Query]
...
```

### 7.5 `list_documents`

```python
list_documents(*, user: AuthenticatedUser) -> list[DocumentRecord]
```

### 7.6 `get_document`

```python
get_document(doc_id: str, *, user: AuthenticatedUser) -> DocumentRecord | None
```

### 7.7 `list_document_chunks`

```python
list_document_chunks(doc_id: str, *, user: AuthenticatedUser) -> list[ChunkRecord]
```

### 7.8 `list_ingestion_progress`

```python
list_ingestion_progress(
    doc_id: str,
    *,
    user: AuthenticatedUser,
    job_id: str | None = None,
) -> list[IngestionProgressRecord]
```

### 7.9 `delete_document`

```python
delete_document(doc_id: str, *, user: AuthenticatedUser) -> bool
```

반환:
- `True`: 현재 user scope에서 문서를 찾아 vector / metadata / asset 삭제 완료
- `False`: 현재 user scope에서 대상 문서를 찾지 못함

중요 제약:
- vector store 삭제가 먼저 수행된다.
- vector store 삭제가 예외를 내면 metadata / asset 삭제는 진행되지 않는다.
- 이후 재시도 가능하다.

### 7.10 `health_check`

```python
health_check() -> object
```

동작:
- 항상 metadata check 포함
- `vector_store`, `embedding_client`, `generation_client`가 `check()`를 제공하면 함께 포함
- 가능하면 DocMesh aggregate health path 사용
- 실패 시 local fallback result 사용

---

## 8. user scope 규칙

기본 규칙:
- 모든 user-scoped 공개 메서드는 `AuthenticatedUser`를 필수로 받는다.
- persistence 및 filtering에는 `user.sub`를 `user_id`로 사용한다.
- 사용자 인증 및 `AuthenticatedUser` 생성은 상위 애플리케이션에서 완료한다.

---

## 9. 제공 Ollama adapter

### 9.1 `OllamaEmbeddingClient`

```python
OllamaEmbeddingClient(*, client, model: str)
```

동작:
- `client.embed(model=..., input=...)` 호출
- 응답의 `embeddings` 배열을 `list[list[float]]`로 변환
- model이 비어 있으면 `ValueError`
- transport 오류는 `RuntimeError("Failed to fetch embeddings from Ollama")`
- malformed response는 `RuntimeError("Ollama returned a malformed embeddings response")`

### 9.2 `OllamaGenerationClient`

```python
OllamaGenerationClient(*, client, model: str)
```

동작:
- `client.chat(model=..., messages=[{"role": "user", "content": prompt}])` 호출
- 응답의 `message.content`를 문자열로 반환
- model이 비어 있으면 `ValueError`
- transport 오류는 `RuntimeError("Failed to generate response from Ollama")`
- malformed response는 `RuntimeError("Ollama returned a malformed generation response")`

---

## 10. 최소 실행 예시

```python
from pathlib import Path

from rag_system_core import RAGCore
from rag_system_core.composition.factories import (
    create_rag_chunker,
    create_rag_document_storage,
    create_rag_embedding_client,
    create_rag_generation_client,
    create_rag_metadata_store,
    create_rag_vector_store,
)

metadata_path = Path("./data/metadata.db")
document_storage_dir = Path("./data/documents")

core = RAGCore(
    embedding_client=create_rag_embedding_client(),
    generation_client=create_rag_generation_client(),
    vector_store=create_rag_vector_store(metadata_path=metadata_path),
    metadata_store=create_rag_metadata_store(metadata_path=metadata_path),
    document_storage=create_rag_document_storage(
        storage_mode="local",
        document_storage_dir=document_storage_dir,
    ),
    chunker=create_rag_chunker(chunk_size=512, chunk_overlap=64),
)

ingested = core.ingest_text(
    text="alpha beta gamma",
    source="note.txt",
)

response = core.query(
    question="alpha를 요약해줘",
    top_k=3,
)

print(ingested.doc_id)
print(response.answer)
```