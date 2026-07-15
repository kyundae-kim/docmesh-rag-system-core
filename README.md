# docmesh-rag-system-core

DocMesh 환경에서 사용할 수 있는 **조립형 Python RAG 코어 라이브러리**입니다.

이 저장소는 현재 구현 기준으로 다음 책임을 가집니다.
- 문서 적재(ingestion)
- 사용자 스코프 기반 검색(retrieval)
- 생성 모델 호출을 통한 답변 생성(generation)
- SQLite + Milvus Lite 기반 persistence
- DocMesh settings / registry / health-check 연동을 위한 composition 경로 제공

이 패키지는 **HTTP 서버가 아니라 라이브러리**입니다. 외부 애플리케이션이나 서비스가 `RAGCore`를 조립해 사용합니다.

---

## 관련 문서

- [API 문서](docs/api.md)
- [설정 가이드](docs/config.md)
- [PRD](docs/prd.md)
- [SRS](docs/srs.md)
- [테스트 문서](docs/test.md)
- [환경변수 예시](.env.example)

---

## 핵심 개념

### user scope
- 각 공개 메서드는 `docmesh_py_core.AuthenticatedUser`를 `user` 인자로 받습니다.
- 저장 및 검색 격리에는 `user.sub`를 `user_id`로 사용합니다.
- 사용자 인증과 사용자 모델 생성은 상위 애플리케이션의 책임입니다.

### document asset storage
- 문서 본문은 document metadata row에 직접 저장하지 않습니다.
- 원문 자산은 `DocumentStorage`가 관리하고, 문서에는 `storage_path`만 기록됩니다.
- 지원 모드:
  - `memory`
  - `local`

### persistence
- metadata store: SQLite + SQLAlchemy ORM
- vector store: Milvus Lite
- 동일한 metadata / vector store 구성을 다시 열면 restart recovery가 가능합니다.

---

## 현재 공개 진입점

패키지 루트에서 공개되는 주요 항목:

```python
from rag_system_core import (
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

실무적으로는 아래 두 경로가 핵심입니다.

1. **factory helper + `RAGCore(...)` 직접 조립**
2. **`DocmeshRAGServiceFactory` + `bootstrap_rag_core(...)`**

---

## 설치

`pyproject.toml` 기준 요구사항:
- Python `>= 3.11`
- `docmesh-py-core`
- `pydantic-settings`
- `pymilvus[milvus-lite]`

권장 설치:

```bash
uv sync
```

`OllamaEmbeddingClient`, `OllamaGenerationClient`, `create_rag_embedding_client(...)`, `create_rag_generation_client(...)`를 사용할 경우 Python 패키지 `ollama`도 필요합니다.

```bash
uv pip install ollama
```

---

## 최소 설정

첫 성공 호출 기준 최소 권장 env:

```env
OLLAMA_HOST=http://ollama:11434
OLLAMA_EMBEDDING_MODEL=bge-m3
OLLAMA_GENERATION_MODEL=gpt-oss:20b
```

추가로 보통 아래 경로에 쓰기 가능해야 합니다.
- `metadata_path`가 가리키는 SQLite 파일 경로
- `document_storage_dir` 디렉터리
- `metadata_path.with_suffix(".milvus.db")`로 생성될 수 있는 Milvus Lite 파일 경로

전체 canonical 예시는 [.env.example](.env.example), 세부 설명은 [docs/config.md](docs/config.md)를 참고하세요.

---

## 가장 단순한 사용 경로

현재 구현 기준으로 `RAGCore`는 **의존성 주입형 생성자**입니다. 즉, 예전 문서처럼 `metadata_path`, `storage_mode` 같은 값만 바로 넘겨서 생성하지 않습니다.

가장 현실적인 첫 성공 경로는 `create_rag_*` helper로 구성요소를 만든 뒤 `RAGCore(...)`를 조립하는 방식입니다.

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

---

## 사용 예시

상위 애플리케이션에서 인증을 완료한 뒤 생성한 사용자 정보를 전달합니다.

```python
from rag_system_core import AuthenticatedUser

user = AuthenticatedUser(
    sub="user-a",
    preferred_username="user-a",
    email=None,
    given_name=None,
    family_name=None,
    name=None,
    realm_roles=[],
    client_roles={},
    claims={},
)
```

### 1. 텍스트 적재 + 질의

```python
ingested = core.ingest_text(
    user=user,
    text="alpha beta gamma",
    source="note.txt",
)

response = core.query(
    user=user,
    question="alpha를 요약해줘",
    top_k=3,
)

print(ingested.doc_id)
print(response.answer)
```

### 2. 파일 스트림 적재

```python
from io import BytesIO

stream = BytesIO(b"document from stream")

ingested = core.ingest_file_stream(
    user=user,
    file_stream=stream,
    source="stream.txt",
)

print(ingested.chunk_count)
```

### 3. 파일 경로 적재

```python
from pathlib import Path

ingested = core.ingest_file_path(
    user=user,
    file_path=Path("./sample.txt"),
)

print(ingested.doc_id)
```

### 4. 문서 관리

```python
documents = core.list_documents(user=user)
first_doc = documents[0]

print(first_doc.doc_id)
print(first_doc.storage_path)

chunks = core.list_document_chunks(first_doc.doc_id, user=user)
progress_rows = core.list_ingestion_progress(first_doc.doc_id, user=user)
```

### 5. 삭제

```python
deleted = core.delete_document(first_doc.doc_id, user=user)
print(deleted)
```

## bootstrap 경로

DocMesh settings / registry가 이미 준비된 환경이면 service factory 기반 bootstrap 경로도 사용할 수 있습니다.

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

이 경로는 helper가 settings를 직접 로드하는 방식이 아니라, **준비된 service factory를 받아 조립**하는 방식입니다.

---

## 현재 기능 요약

- `ingest_text(...)`
- `ingest_file_stream(...)`
- `ingest_file_path(...)`
- `query(...)`
- `list_documents(...)`
- `get_document(...)`
- `list_document_chunks(...)`
- `list_ingestion_progress(...)`
- `delete_document(...)`
- `health_check()`

추가 구현 특성:
- fixed-window chunking (`chunk_size`, `chunk_overlap`)
- ingestion 중 batch embedding 호출
- prompt 구조에 `[System Prompt]`, `[Retrieved Context]`, `[User Query]` 포함
- user scope 기반 retrieval / 조회 / 삭제 제한
- vector store 삭제 실패 시 metadata / asset 삭제를 진행하지 않아 재시도 가능
- health check에서 metadata 및 사용 가능한 dependency status 집계

---

## 환경변수 요약

### Ollama
- `OLLAMA_HOST`
- `OLLAMA_EMBEDDING_MODEL`
- `OLLAMA_GENERATION_MODEL`
- `OLLAMA_REQUEST_TIMEOUT_SECONDS`

### Milvus
- `MILVUS_URI`
- `MILVUS_COLLECTION`
- `MILVUS_REQUEST_TIMEOUT_SECONDS`
- `MILVUS_CONNECT_TIMEOUT_SECONDS`

legacy 패턴은 현재 지원 대상으로 보지 않습니다.
- `OLLAMA_EMBED__*`
- `OLLAMA_GENERATE__*`
- `MILVUS__*`

---

## 테스트

전체 테스트 실행:

```bash
uv run pytest -q
```

문서 동기화 시점 기준 테스트 결과:

```text
49 passed
```

테스트 범위와 요구사항 추적은 [docs/test.md](docs/test.md)를 참고하세요.
