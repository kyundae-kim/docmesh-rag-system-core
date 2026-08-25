# docmesh-rag-system-core

DocMesh 환경에서 사용할 수 있는 **조립형 Python RAG 코어 라이브러리**입니다.

이 저장소는 현재 구현 기준으로 다음 책임을 가집니다.
- 문서 적재(ingestion)
- 사용자 스코프 기반 검색(retrieval)
- 생성 모델 호출을 통한 답변 생성(generation)
- SQLite + configured Milvus adapter 기반 검색 persistence
- dms-core + MinIO 기반 원문 lifecycle
- DocMesh settings / `ServiceBundle` 연동을 위한 composition 경로 제공

이 패키지는 **HTTP 서버가 아니라 라이브러리**입니다. 외부 애플리케이션이나 서비스가 `RAGCore`를 조립해 사용합니다.

---

## 관련 문서

- [PRD](docs/prd.md)
- [SRS](docs/srs.md)

---

## 핵심 개념

### user scope
- 각 공개 메서드는 `rag_system_core.types.AuthenticatedUser`를 `user` 인자로 받습니다.
- 저장 및 검색 격리에는 `user.sub`를 `user_id`로 사용합니다.
- 사용자 인증과 사용자 모델 생성은 상위 애플리케이션의 책임입니다.

### document asset storage
- 문서 본문은 document metadata row에 직접 저장하지 않습니다.
- 표준 composition에서는 `DmsDocumentStorage`가 dms-core의 원문 lifecycle을 사용합니다.
- RAG metadata에는 내부 MinIO key가 아니라 opaque `asset_reference`만 기록되며, 기본값은 동일한 DMS `document_id`입니다.
- 테스트나 사용자 정의 직접 조립에서는 `DocumentAssetStorage` protocol 구현체를 주입할 수 있습니다.

### persistence
- metadata store: SQLite + SQLAlchemy ORM
- vector store: standard `MilvusLiteVectorStore` adapter (local Milvus Lite or remote Milvus according to the supplied client/configuration)
- 동일한 metadata / vector store 구성을 다시 열면 restart recovery가 가능합니다.

---

## 현재 공개 진입점

패키지 루트에서 공개되는 주요 항목:

```python
from rag_system_core import (
    RAGCore,
    OllamaEmbeddingClient,
    OllamaGenerationClient,
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

실무적으로는 아래 조립 경로가 핵심입니다.

1. **host-owned client 경로: `DocmeshRAGServiceFactory.from_host_clients(...)` + `create_rag_core(...)`**
2. **이미 조립된 collaborator 경로: `DocmeshRAGServiceFactory.from_clients(...)` + `create_rag_core(...)`**
3. **테스트·사용자 정의 경로: factory helper + `RAGCore(...)` 직접 조립**

---

## 설치

`pyproject.toml` 기준 요구사항:
- Python `>= 3.11`
- `dms-core>=0.9.0` (Python package name `dms`)
- `ollama>=0.6.2`
- `pydantic-settings>=2.14.1`
- `pymilvus[milvus-lite]>=3.0.1`

권장 설치:

```bash
uv sync
```

`ollama`는 위 선언 의존성에 포함되어 있으므로 별도 설치가 필요하지 않습니다.

---

## 설정 및 조립

RAG와 DMS composition layer는 process 환경변수를 읽지 않습니다. 상위 애플리케이션이 Ollama·Milvus client와 model, collection, timeout 값을 직접 생성·결정하고, DMS용 SQLAlchemy `Engine`, MinIO client, bucket 이름을 명시적으로 조립한 뒤 `DocmeshRAGServiceFactory.from_host_clients(...)` 또는 `create_rag_*` helper에 전달해야 합니다.

추가로 보통 아래 경로에 쓰기 가능해야 합니다.
- `metadata_path`가 가리키는 SQLite 파일 경로
- 상위 애플리케이션이 생성한 Milvus client가 사용하는 파일 경로

---

## 가장 단순한 사용 경로

현재 구현 기준으로 `RAGCore`는 **의존성 주입형 생성자**입니다. 상위 애플리케이션이 service factory를 직접 구성하거나 아래의 host-owned client service-factory 경로를 사용해야 합니다.

---

## 사용 예시

상위 애플리케이션에서 인증을 완료한 뒤 생성한 사용자 정보를 전달합니다.

```python
from rag_system_core import AuthenticatedUser

user = AuthenticatedUser(
    sub="user-a",
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
step_statuses = core.get_ingestion_step_statuses(first_doc.doc_id, user=user)
```

`progress_rows`에는 각 파이프라인 단계의 상태 전이가 포함되고, `step_statuses`에는
문서에 대해 확인된 각 단계의 최종 상태가 포함됩니다. 아직 실행되지 않은 후속 단계는
`"not_started"`로 표시됩니다. 특정 ingestion 실행만 조회하려면 `job_id`를 함께 전달합니다.

### 5. 삭제

```python
deleted = core.delete_document(first_doc.doc_id, user=user)
print(deleted)
```

## 조립 경로

`RAGCore(...)`는 fully assembled dependency graph를 받는 의존성 주입형 생성자입니다. 상위 애플리케이션은 service factory를 직접 구성하거나 아래의 host-owned client service-factory 경로를 사용해야 합니다. 이미 조립된 RAG collaborator를 주입하는 경로에서는 `DocmeshRAGServiceFactory.from_clients(...)`를 사용할 수 있고, 원시 host-owned transport client에서 시작할 경우에는 `DocmeshRAGServiceFactory.from_host_clients(...)`를 사용할 수 있습니다. Factory의 `create_rag_core(...)`는 보유한 collaborator를 최종 `RAGCore`로 조립하며, 정상적인 Factory 조립에는 `metadata_engine`이 필요합니다. 두 classmethod 경로 모두 context manager이지만 dms-core v0.9 SDK에는 `close()` lifecycle이 없으므로 DMS SDK와 host-owned Engine/raw client를 닫지 않습니다. `metadata_path`로 Factory가 생성해 추적한 MetadataStore만 Factory `close()`에서 정리하며, host-owned `metadata_engine` 기반 MetadataStore의 lifecycle은 호출자가 관리합니다.

### host-owned clients

DMS와 RAG runtime 설정을 환경변수에서 읽지 않고 상위 애플리케이션이 직접 만든 transport client를 전달할 수도 있습니다. `DocmeshRAGServiceFactory.from_host_clients(...)`는 DMS용 및 metadata용 SQLAlchemy `Engine`, MinIO client, Ollama client, Milvus client를 받아 Ollama embedding/generation adapter와 Milvus vector store를 조립한 Factory를 반환합니다. Factory의 `create_rag_core(...)`가 최종 `RAGCore`를 조립하며, 이 경로는 `ServiceBundle`이나 runtime settings를 만들지 않습니다.

```python
from minio import Minio
from ollama import Client as OllamaClient
from pymilvus import MilvusClient
from sqlalchemy import create_engine

from rag_system_core import DocmeshRAGServiceFactory

engine = create_engine("sqlite+pysqlite:///./data/dms.db")
metadata_engine = create_engine("sqlite+pysqlite:///./data/metadata.db")
minio_client = Minio(
    "minio:9000",
    access_key="replace-me",
    secret_key="replace-me",
    secure=False,
)
ollama_client = OllamaClient(host="http://ollama:11434")
milvus_client = MilvusClient(uri="./data/metadata.milvus.db")

with DocmeshRAGServiceFactory.from_host_clients(
    engine=engine,
    metadata_engine=metadata_engine,
    minio_client=minio_client,
    bucket_name="documents",
    ollama_client=ollama_client,
    milvus_client=milvus_client,
    embedding_model="bge-m3",
    generation_model="gpt-oss:20b",
    collection_name="rag_chunks",
    timeout=30.0,
) as service_factory:
    core = service_factory.create_rag_core()
```

context 종료 시 host-client 경로에서 Factory는 dms-core SDK, `Engine`, `metadata_engine`, MinIO, Ollama, Milvus raw client를 닫지 않습니다. 이 자원은 caller-owned이며 상위 애플리케이션 lifecycle에서 정리합니다. Factory가 `metadata_path`로 생성한 compatibility MetadataStore만 Factory가 추적·정리합니다. Factory가 생성한 RAG adapter와 MetadataStore는 주입된 transport client를 소유하지 않습니다. `DocmeshRAGServiceFactory.from_clients(...)`는 이미 만들어진 RAG collaborator를 주입받는 경로입니다. Factory를 직접 사용할 때는 context 안에서 `create_rag_core(...)`를 호출하고, 반환된 Core도 같은 context 안에서 사용해야 합니다.

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

추가 구현 특성:
- fixed-window chunking (`chunk_size`, `chunk_overlap`)
- ingestion 중 batch embedding 호출
- prompt 구조에 `[System Prompt]`, `[Retrieved Context]`, `[User Query]` 포함
- user scope 기반 retrieval / 조회 / 삭제 제한
- 삭제는 vector → DMS soft delete → RAG metadata 순서로 실행해 실패 시 metadata 기반 재시도를 보존

---

## DMS 조립 경계

`DocmeshRAGServiceFactory.from_host_clients(...)`는 DMS 환경변수나 RAG 환경변수를 읽지 않습니다. 상위 애플리케이션이 만든 DMS용 및 metadata용 SQLAlchemy `Engine`, MinIO client, Ollama client, Milvus client와 embedding/generation model 및 vector-store 설정을 직접 전달해야 합니다.

---

## 테스트

전체 테스트 실행:

```bash
uv run pytest -q
```
