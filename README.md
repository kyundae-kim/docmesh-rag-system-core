# docmesh-rag-system-core

DocMesh 환경에서 사용할 수 있는 **조립형 Python RAG 코어 라이브러리**입니다.

이 저장소는 현재 구현 기준으로 다음 책임을 가집니다.
- 문서 적재(ingestion)
- 사용자 스코프 기반 검색(retrieval)
- 생성 모델 호출을 통한 답변 생성(generation)
- SQLite + Milvus Lite 기반 검색 persistence
- dms-core + MinIO 기반 원문 lifecycle
- DocMesh settings / `ServiceBundle` / health-check 연동을 위한 composition 경로 제공

이 패키지는 **HTTP 서버가 아니라 라이브러리**입니다. 외부 애플리케이션이나 서비스가 `RAGCore`를 조립해 사용합니다.

---

## 관련 문서

- [PRD](docs/prd.md)
- [SRS](docs/srs.md)

---

## 핵심 개념

### user scope
- 각 공개 메서드는 `docmesh_py_core.AuthenticatedUser`를 `user` 인자로 받습니다.
- 저장 및 검색 격리에는 `user.sub`를 `user_id`로 사용합니다.
- 사용자 인증과 사용자 모델 생성은 상위 애플리케이션의 책임입니다.

### document asset storage
- 문서 본문은 document metadata row에 직접 저장하지 않습니다.
- production bootstrap에서는 `DmsDocumentStorage`가 dms-core의 원문 lifecycle을 사용합니다.
- RAG metadata에는 내부 MinIO key가 아니라 opaque `asset_reference`만 기록되며, 기본값은 동일한 DMS `document_id`입니다.
- 테스트나 사용자 정의 직접 조립에서는 `DocumentAssetStorage` protocol 구현체를 주입할 수 있습니다.

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
    bootstrap_rag_core_from_env,
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

실무적으로는 아래 세 경로가 핵심입니다.

1. **production 기본 경로: `bootstrap_rag_core_from_env(...)` context manager**
2. **고급 조립 경로: `DocmeshRAGServiceFactory` + `bootstrap_rag_core(...)`**
3. **테스트·사용자 정의 경로: factory helper + `RAGCore(...)` 직접 조립**

---

## 설치

`pyproject.toml` 기준 요구사항:
- Python `>= 3.11`
- `docmesh-py-core`
- `dms-core`
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
MILVUS_URI=./data/metadata.milvus.db
DMS_DOCMESH_ENV=development
DMS_METADATA_BACKEND=sqlite
DMS_SQLITE_PATH=./data/dms.db
DMS_MINIO_ENDPOINT=minio:9000
DMS_MINIO_ACCESS_KEY=replace-me
DMS_MINIO_SECRET_KEY=replace-me
DMS_MINIO_BUCKET=documents
DMS_MINIO_SECURE=false
```

추가로 보통 아래 경로에 쓰기 가능해야 합니다.
- `metadata_path`가 가리키는 SQLite 파일 경로
- `DMS_SQLITE_PATH`가 가리키는 DMS metadata 파일 경로
- `metadata_path.with_suffix(".milvus.db")`로 생성될 수 있는 Milvus Lite 파일 경로

위 환경변수 예시는 production bootstrap에 필요한 canonical 설정 이름을 보여 줍니다.

---

## 가장 단순한 사용 경로

현재 구현 기준으로 `RAGCore`는 **의존성 주입형 생성자**입니다. production 기본 경로는 DocMesh 설정으로 Ollama·Milvus·DMS를 함께 조립하는 service factory입니다.

가장 현실적인 첫 성공 경로는 `bootstrap_rag_core_from_env(...)`가 구성요소와 DMS SDK를 한 번 조립하고 context 종료 시 소유 자원을 정리하는 방식입니다. startup health check는 기본적으로 활성화되며 Ollama와 Milvus를 병렬 점검합니다.

```python
from rag_system_core import bootstrap_rag_core_from_env

with bootstrap_rag_core_from_env(
    metadata_path="./data/metadata.db",
    chunk_size=512,
    chunk_overlap=64,
) as core:
    # 이 context 안에서 API 서버, worker 또는 batch 작업을 실행합니다.
    print(core.health_check().ok)
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
print(first_doc.asset_reference)

chunks = core.list_document_chunks(first_doc.doc_id, user=user)
progress_rows = core.list_ingestion_progress(first_doc.doc_id, user=user)
```

### 5. 삭제

```python
deleted = core.delete_document(first_doc.doc_id, user=user)
print(deleted)
```

## bootstrap 경로

DocMesh v0.5.0 설정이 프로세스 환경변수에 준비되어 있으면 lifecycle을 소유하는 environment bootstrap 경로를 사용합니다. `from_env()`는 별도의 환경 mapping을 받지 않고 현재 프로세스 환경을 읽으며, DMS의 공유 서비스 설정은 `DMS_` 접두사로 RAG 설정과 분리합니다.

```python
from rag_system_core import bootstrap_rag_core_from_env

with bootstrap_rag_core_from_env(
    metadata_path="./data/metadata.db",
    check_on_startup=True,
    parallel_healthchecks=True,
) as core:
    # 여기에서 core를 사용하는 애플리케이션을 실행합니다.
    ...
```

이 helper는 DocMesh service bundle과 DMS SDK의 lifecycle을 소유합니다. context가 정상 종료되거나 예외로 종료되면 DMS SDK와 RAG bundle을 순서대로 정리합니다. 사용자 정의 조립이 필요한 경우 `DocmeshRAGServiceFactory.from_env(...)` 자체도 context manager로 사용할 수 있습니다.

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
- 삭제는 vector → DMS soft delete → RAG metadata 순서로 실행해 실패 시 metadata 기반 재시도를 보존
- health check에서 metadata, Milvus, DMS 및 사용 가능한 dependency status 집계

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

### DMS / MinIO
- `DMS_METADATA_BACKEND` (`sqlite` 또는 `postgresql`)
- `DMS_SQLITE_PATH` 또는 `DMS_POSTGRES_*`
- `DMS_MINIO_ENDPOINT`
- `DMS_MINIO_ACCESS_KEY`
- `DMS_MINIO_SECRET_KEY`
- `DMS_MINIO_BUCKET`
- `DMS_MINIO_SECURE`

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
