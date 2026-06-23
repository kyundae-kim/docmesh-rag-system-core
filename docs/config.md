# Configuration Guide

이 문서는 `docmesh-rag-system-core`를 **현재 구현 기준**으로 설정하는 방법을 설명한다.

이 문서의 초점:
- 어떤 env가 실제로 사용되는지
- 어떤 값이 첫 성공 호출에 필요한지
- 어떤 값이 DocMesh / Keycloak 통합 시에만 필요한지
- factory helper와 bootstrap 경로가 어떻게 연결되는지

---

## 1. 가장 쉬운 첫 성공 설정

첫 성공 호출만 목표라면 다음 전략이 가장 단순하다.

- `DOCMESH_AUTH_MODE` 미설정
- token 생략 (`single-user` 경로)
- `create_rag_*` helper로 구성요소 생성
- `RAGCore(...)` 직접 조립
- local storage 사용
- Ollama + Milvus Lite 기본 경로 사용

최소 권장 env:

```env
OLLAMA_HOST=http://ollama:11434
OLLAMA_EMBEDDING_MODEL=bge-m3
OLLAMA_GENERATION_MODEL=gpt-oss:20b
```

이 경우:
- auth는 기본 token mode이지만 token을 안 넘기면 `single-user`
- Milvus URI를 비워도 `metadata_path.with_suffix(".milvus.db")` fallback 사용 가능
- collection을 비워도 `rag_chunks` fallback 사용 가능

---

## 2. canonical configuration example

```env
# Shared Ollama runtime
OLLAMA_HOST=http://ollama:11434
OLLAMA_EMBEDDING_MODEL=bge-m3
OLLAMA_GENERATION_MODEL=gpt-oss:20b
OLLAMA_REQUEST_TIMEOUT_SECONDS=30

# Milvus runtime
MILVUS_URI=./data/metadata.milvus.db
MILVUS_COLLECTION=rag_chunks
MILVUS_REQUEST_TIMEOUT_SECONDS=30
MILVUS_CONNECT_TIMEOUT_SECONDS=30

# Optional auth mode
# DOCMESH_AUTH_MODE=keycloak

# If using keycloak mode, configure the required docmesh-py-core auth settings too.
# Example names depend on your shared docmesh config contract.
# KEYCLOAK_URL=
# KEYCLOAK_REALM=
# KEYCLOAK_CLIENT_ID=
```

---

## 3. 필수 / 권장 / 선택 설정

| 변수 | 분류 | 언제 필요한가 | 비고 |
|---|---|---|---|
| `OLLAMA_HOST` | 권장 | 기본 Ollama factory/adapter를 쓸 때 | 예: `http://ollama:11434` |
| `OLLAMA_EMBEDDING_MODEL` | 사실상 필수 | 기본 Ollama embedding 경로 사용 시 | 비어 있으면 embedding client 생성 실패 가능 |
| `OLLAMA_GENERATION_MODEL` | 사실상 필수 | 기본 Ollama generation 경로 사용 시 | 비어 있으면 generation client 생성 실패 가능 |
| `OLLAMA_REQUEST_TIMEOUT_SECONDS` | 선택 | Ollama timeout 조정 시 | 현재 client factory는 settings에서 읽을 수 있음 |
| `MILVUS_URI` | 선택 | fallback 대신 명시적 vector store 위치를 쓰고 싶을 때 | 없으면 `metadata_path.with_suffix(".milvus.db")` |
| `MILVUS_COLLECTION` | 선택 | 기본 `rag_chunks` 대신 별도 collection 사용 시 | |
| `MILVUS_REQUEST_TIMEOUT_SECONDS` | 선택 | Milvus timeout 조정 시 | |
| `MILVUS_CONNECT_TIMEOUT_SECONDS` | 선택 | DocMesh settings shape에 따라 timeout fallback으로 사용 가능 | |
| `DOCMESH_AUTH_MODE` | 선택 | Keycloak 기반 user identity 해석이 필요할 때 | 기본은 token mode |

---

## 4. 설정 우선순위와 생성 경로

### 4.1 첫 성공 경로: factory helper + `RAGCore(...)`

현재 구현에서 `RAGCore`는 아래 의존성을 직접 요구한다.

- `embedding_client`
- `generation_client`
- `vector_store`
- `metadata_store`
- `document_storage`
- `chunker`

따라서 가장 현실적인 첫 성공 경로는 아래와 같다.

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

### 4.2 Milvus fallback

`create_rag_vector_store(...)`의 fallback 규칙:
- URI: `metadata_path.with_suffix(".milvus.db")`
- Collection: `rag_chunks`
- Timeout: `30.0`

즉, Milvus env가 비어 있어도 `metadata_path`만 있으면 기본 vector store를 만들 수 있다.

### 4.3 service factory 기반 bootstrap

현재 bootstrap helper 이름은 `bootstrap_rag_core(...)`이며, helper 자체가 settings를 직접 읽는 것은 아니다.

대신 아래를 받는다.
- `service_factory`
- `metadata_path`
- `document_storage_dir`
- `storage_mode`
- `chunk_size`
- `chunk_overlap`

DocMesh 환경에서는 보통 다음 순서로 사용한다.

1. `load_docmesh_settings()`
2. `create_service_registry(settings)`
3. `DocmeshRAGServiceFactory(settings=settings, registry=registry)`
4. `bootstrap_rag_core(service_factory=..., ...)`

즉, bootstrap helper는 **이미 settings / registry / service-factory 계약이 준비된 환경**에서 쓰는 경로다.

---

## 5. 첫 성공 호출용 추천 조합

### 5.1 가장 단순한 로컬 조합

- `OLLAMA_HOST=http://ollama:11434`
- `OLLAMA_EMBEDDING_MODEL=bge-m3`
- `OLLAMA_GENERATION_MODEL=gpt-oss:20b`
- `DOCMESH_AUTH_MODE` 미설정
- `storage_mode="local"`
- `metadata_path=./data/metadata.db`
- `document_storage_dir=./data/documents`
- token 생략

### 5.2 이때 기대되는 기본 동작

- user scope: `single-user`
- auth mode: 기본 token mode
- Milvus URI: `./data/metadata.milvus.db` 형태 fallback 사용 가능
- Milvus collection: `rag_chunks`
- chunker default 예시: `chunk_size=512`, `chunk_overlap=64`

---

## 6. 첫 성공 호출에는 필요 없는 것

다음은 **첫 성공 호출만 목표라면 당장 필요하지 않다.**

- `DOCMESH_AUTH_MODE=keycloak`
- Keycloak 관련 설정
- custom collection 이름
- custom timeout 값
- `bootstrap_rag_core(...)`
- `DocmeshRAGServiceFactory`
- 외부 registry 주입

단, `create_rag_*` helper는 현재 `RAGCore` 조립을 단순화하는 실용 경로이므로 첫 성공 호출에서도 사용하는 편이 자연스럽다.

---

## 7. legacy env

현재 문서 기준으로 지원 대상으로 보지 않는 legacy 패턴:

- `OLLAMA_EMBED__*`
- `OLLAMA_GENERATE__*`
- `MILVUS__*`

---

## 8. 빠른 사용 절차

1. `.env`에 최소한 아래 3개를 채운다.
   - `OLLAMA_HOST`
   - `OLLAMA_EMBEDDING_MODEL`
   - `OLLAMA_GENERATION_MODEL`
2. Ollama 서버와 모델 준비를 확인한다.
3. `docs/api.md`의 factory helper + `RAGCore(...)` 예시로 첫 호출을 시도한다.

---

## 9. 첫 성공 체크리스트

- [ ] `OLLAMA_HOST`가 올바르다
- [ ] `OLLAMA_EMBEDDING_MODEL`이 설정됐다
- [ ] `OLLAMA_GENERATION_MODEL`이 설정됐다
- [ ] Ollama 서버가 실제로 떠 있다
- [ ] 모델이 실제로 준비되어 있다
- [ ] `DOCMESH_AUTH_MODE`는 비워두었다 (첫 시도 기준)
- [ ] Keycloak 설정에 의존하지 않는다
- [ ] `metadata_path`와 문서 저장 디렉터리에 쓰기 권한이 있다

---

## 10. 관련 파일

- `docs/api.md`
- `docs/prd.md`
- `docs/srs.md`
- `docs/test.md`
- `README.md`
