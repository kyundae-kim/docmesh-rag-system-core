# DocMesh RAG Core Service PRD

## 1. 문서 개요

- **문서명:** Product Requirements Document (PRD)
- **대상 제품:** DocMesh RAG Core Service
- **문서 목적:** 현재 저장소에 구현된 `rag_system_core`의 제품 요구사항과 동작 경계를 코드 기준으로 정의한다.
- **문서 상태:** Aligned with current implementation

이 문서는 미래 희망사항보다 **현재 실제 코드가 보장하는 것**을 우선 서술한다.

---

## 2. 제품 배경

DocMesh RAG Core는 문서를 적재하고, 관련 컨텍스트를 검색한 뒤, LLM을 이용해 답변을 생성하는 핵심 라이브러리다.

현재 구현은 다음 목적을 갖는다.
- 상위 애플리케이션이 단일 진입점 `RAGCore`만으로 문서 적재/검색/질의를 수행할 수 있게 한다.
- 문서 metadata와 검색 인덱스를 재시작 이후에도 재사용 가능하게 한다.
- 멀티유저 환경에서 사용자별 문서와 검색 결과가 섞이지 않도록 user scope를 강제한다.
- 이후 API 서버나 서비스 분리로 확장 가능한 내부 책임 분리를 유지한다.

---

## 3. 제품 목표

### 3.1 핵심 목표

1. 단일 entry point 기반의 간단한 RAG 사용성을 제공한다.
2. 텍스트, 파일 스트림, 파일 경로 기반 ingestion을 지원한다.
3. 사용자별 문서/청크/검색 결과 격리를 보장한다.
4. SQLite metadata + Milvus Lite vector store 기반의 경량 persistence를 제공한다.
5. DocMesh 공통 설정/서비스 팩토리와 연동 가능해야 한다.
6. 운영 상태 확인을 위한 health check를 제공한다.

### 3.2 성공 기준

- 사용자는 `RAGCore` 또는 `bootstrap_rag_core_from_docmesh()`로 코어를 생성할 수 있다.
- 사용자는 세 가지 ingestion 경로(`ingest_text`, `ingest_file_stream`, `ingest_file_path`)를 사용할 수 있다.
- query는 항상 현재 user scope로 제한된 chunk만 사용한다.
- metadata는 SQLite에 유지되고, 동일한 Milvus 설정을 재사용하면 검색이 복원된다.
- 문서 삭제 시 성공 경로에서는 metadata, progress, asset, Milvus 엔트리가 함께 제거된다.
- health check는 metadata 및 사용 가능한 의존 서비스 상태를 집계한다.

---

## 4. 범위 정의

### 4.1 포함 범위 (In Scope)

- 단일 클래스 진입점 `RAGCore`
- DocMesh 설정 기반 bootstrap helper
- 텍스트 / 파일 스트림 / 파일 경로 ingestion
- 고정 길이 chunking + overlap
- embedding batch 호출
- Milvus Lite 기반 vector search
- generation client 기반 답변 생성
- token 기반 user scope
- 선택적 Keycloak 기반 `token -> user_id` 해석
- SQLAlchemy ORM + SQLite metadata persistence
- 문서 자산 저장 (`memory`, `local`)
- 문서 목록/단건/청크/progress 조회
- 문서 삭제
- health check 집계

### 4.2 제외 범위 (Out of Scope)

- 외부 공개용 HTTP API 서버
- UI / Frontend
- 비동기 job queue
- 고급 reranking
- 조직/역할 기반 복잡한 권한 모델
- 분산 트랜잭션 보장
- production-grade distributed vector database 운영
- 바이너리/비텍스트 파일의 범용 파싱

---

## 5. 핵심 사용자 및 시나리오

### 5.1 주요 사용자

1. **개인 사용자 / 단일 서비스 인스턴스**
   - 자신의 문서를 적재하고 질의응답을 수행하려는 사용자
2. **멀티유저 상위 애플리케이션**
   - 여러 사용자의 문서를 분리 저장하고 사용자별 답변을 제공하려는 시스템
3. **DocMesh 통합 환경**
   - `docmesh_py_core` 설정과 service factory를 통해 공통 인프라를 재사용하려는 시스템

### 5.2 핵심 사용 시나리오

#### 시나리오 1: 텍스트/파일 ingestion
- 사용자는 문자열, 파일 스트림, 파일 경로 중 하나를 입력한다.
- 시스템은 문서를 전처리하고 chunking 한다.
- 시스템은 chunk 전체를 한 번의 embedding batch 호출로 처리한다.
- 시스템은 Milvus Lite에 벡터를 저장하고 SQLite metadata를 기록한다.

#### 시나리오 2: 사용자별 query
- 사용자는 `token`을 제공한다.
- 시스템은 이를 현재 auth 모드에 따라 user scope로 해석한다.
- 검색은 해당 user scope의 chunk만 대상으로 수행된다.
- generation은 검색된 context만을 포함한 prompt를 기반으로 수행된다.

#### 시나리오 3: 재시작 이후 검색 복원
- 프로세스가 재시작되어도 SQLite metadata는 유지된다.
- 동일한 Milvus URI/collection을 다시 열면 기존 벡터 검색을 재사용할 수 있다.

#### 시나리오 4: 문서 단위 관리
- 사용자는 문서 목록, 특정 문서, 특정 문서의 chunk, ingestion progress를 조회할 수 있다.
- 사용자는 문서를 삭제할 수 있다.
- 삭제 성공 시 문서 metadata, chunk metadata, progress metadata, stored asset, Milvus 엔트리가 함께 제거된다.

#### 시나리오 5: 운영 상태 확인
- 사용자는 `health_check()`를 호출해 metadata/vector store/model adapter의 상태를 확인할 수 있다.
- DocMesh 공통 health aggregator가 있으면 이를 사용하고, 없으면 로컬 집계를 사용한다.

---

## 6. 제품 요구사항

### 6.1 사용자 식별 요구사항

#### PRD-FR-1. 기본 사용자 식별
- 시스템은 token 기반 사용자 식별을 지원해야 한다.
- 기본 모드에서는 token 문자열 자체를 `user_id`로 사용해야 한다.
- token이 없거나 공백이면 `single-user` 스코프를 사용해야 한다.

#### PRD-FR-2. Keycloak 기반 해석
- `DOCMESH_AUTH_MODE=keycloak`일 때 시스템은 Keycloak 검증을 통해 `user_id`를 해석해야 한다.
- `sub`가 있으면 이를 우선 사용해야 한다.
- `sub`가 없고 `preferred_username`이 있으면 이를 사용해야 한다.
- 둘 다 없으면 오류를 발생시켜야 한다.

#### PRD-FR-3. 멀티유저 격리
- 모든 문서 metadata와 chunk metadata에는 `user_id`가 포함되어야 한다.
- query는 반드시 `user_id` 기준 필터링을 적용해야 한다.
- 문서 조회/청크 조회/progress 조회/삭제도 현재 user scope 기준으로 제한되어야 한다.

### 6.2 문서 입력 및 저장 요구사항

#### PRD-FR-4. 문서 입력 방식
- 시스템은 다음 세 가지 ingestion API를 제공해야 한다.
  - `ingest_text(...)`
  - `ingest_file_stream(...)`
  - `ingest_file_path(...)`
- `ingest_file_stream(...)`는 `source`가 없거나 공백이면 실패해야 한다.

#### PRD-FR-5. 문서 자산 저장
- 시스템은 `memory`와 `local` 두 가지 asset storage mode를 지원해야 한다.
- 문서 본문은 metadata row에 직접 저장하지 않고 `storage_path`를 통해 추적해야 한다.
- `local` 모드에서는 자산 파일명이 원본 파일명 그대로가 아니라 `doc_id + suffix` 형식이 될 수 있다.

#### PRD-FR-6. 문서 metadata
- 문서 metadata는 최소 다음 필드를 가져야 한다.

```json
{
  "doc_id": "string",
  "user_id": "string",
  "source": "string",
  "created_at": "ISO-8601 string",
  "storage_path": "string | null"
}
```

### 6.3 Ingestion 파이프라인 요구사항

#### PRD-FR-7. 파이프라인 단계
시스템은 다음 순서의 파이프라인 단계를 사용해야 한다.

1. `load`
2. `preprocess`
3. `chunking`
4. `embedding`
5. `vector_store`
6. `chunk_persistence`

#### PRD-FR-8. 전처리/청킹
- 전처리는 현재 구현 기준 `strip()` 수준이어야 한다.
- chunking은 고정 길이 window + overlap 방식을 사용해야 한다.
- 빈 텍스트는 ingest할 수 없어야 한다.

#### PRD-FR-9. progress persistence
- 각 ingestion 실행은 `job_id`로 구분되어야 한다.
- 각 단계의 status 전이는 `running`, `completed`, `failed`를 표현할 수 있어야 한다.
- progress 조회는 문서와 user scope 기준으로 제한되어야 한다.

### 6.4 Embedding / Generation 요구사항

#### PRD-FR-10. embedding 호출
- embedding은 batch 호출을 지원해야 한다.
- ingestion 시 chunk 전체는 하나의 `embed(chunks)` 호출로 처리되어야 한다.
- embedding 반환 벡터 수는 chunk 수와 일치해야 한다.

#### PRD-FR-11. generation 호출
- generation은 완성된 단일 prompt 문자열을 입력으로 받아야 한다.
- generation 결과는 최종 답변 문자열이어야 한다.

#### PRD-FR-12. prompt 구조
prompt는 최소 아래 섹션을 포함해야 한다.

```text
[System Prompt]
[Retrieved Context]
[User Query]
```

### 6.5 Vector Store 요구사항

#### PRD-FR-13. 기본 vector store
- 기본 구현은 Milvus Lite 기반 vector store여야 한다.
- collection이 없으면 첫 insert 시 embedding dimension 기준으로 생성해야 한다.
- 검색은 `user_id` filter를 강제해야 한다.

#### PRD-FR-14. 설정 해석
- Milvus runtime 설정은 가능하면 DocMesh settings에서 읽어야 한다.
- 설정이 없으면 fallback을 사용해야 한다.
  - URI: `metadata_path.with_suffix(".milvus.db")`
  - Collection: `rag_chunks`
  - Timeout: `30.0`

### 6.6 Persistence 및 삭제 요구사항

#### PRD-FR-15. metadata persistence
- SQLite + SQLAlchemy ORM을 사용해야 한다.
- `documents`, `chunks`, `ingestion_progress` 테이블을 유지해야 한다.

#### PRD-FR-16. 재시작 복원
- metadata는 재시작 이후에도 유지되어야 한다.
- retrieval 복원은 동일한 Milvus 저장소/collection을 다시 여는 방식으로 가능해야 한다.
- SQLite가 embedding 벡터를 직접 재생성하지는 않아야 한다.

#### PRD-FR-17. 문서 삭제
- 성공 경로에서 문서 삭제는 다음 데이터를 정리해야 한다.
  - document metadata
  - chunk metadata
  - ingestion progress metadata
  - stored asset
  - Milvus 엔트리
- vector store 삭제가 실패하면 metadata/asset 삭제를 진행하지 않아야 한다.
- 실패 후 재시도 가능해야 한다.

### 6.7 운영성 요구사항

#### PRD-FR-18. health check
- 시스템은 metadata health check를 항상 포함해야 한다.
- vector store / embedding client / generation client가 `check()`를 제공하면 함께 포함해야 한다.
- DocMesh 공통 health aggregator 사용을 우선 시도해야 한다.
- 실패 시 로컬 health result로 fallback 해야 한다.

#### PRD-FR-19. DocMesh integration
- 시스템은 `docmesh_py_core.load_settings()`와 `ServiceFactoryRegistry`를 활용할 수 있어야 한다.
- bootstrap helper는 DocMesh 환경에서 코어를 쉽게 조립할 수 있어야 한다.

---

## 7. 비기능 요구사항

### 7.1 성능
- ingestion의 embedding 호출은 batch 방식이어야 한다.
- retrieval은 top-k 기반으로 단순하고 예측 가능해야 한다.
- health check는 빠르게 실패를 감지할 수 있어야 한다.

### 7.2 확장성
- 단일 entry point를 유지하되 내부 책임은 ingestion / retrieval / generation / storage / composition으로 분리되어야 한다.
- 향후 API 서버나 서비스 분리로 확장 가능한 구조여야 한다.

### 7.3 데이터 격리
- 서로 다른 사용자 token/subject 간 데이터 혼합이 발생해서는 안 된다.
- 저장, 검색, 조회, 삭제 전 과정에서 user scope가 유지되어야 한다.

### 7.4 안정성
- metadata persistence는 재시작 후에도 유지되어야 한다.
- Milvus 설정이 동일하면 retrieval이 재개 가능해야 한다.
- 삭제 실패 시 부분 삭제로 인한 metadata 손실이 최소화되어야 한다.

### 7.5 유지보수성
- public API는 `RAGCore` 중심으로 단순해야 한다.
- 타입/프로토콜은 `rag_system_core.types`에서 명확히 정의되어야 한다.
- DocMesh 통합 코드와 도메인 로직은 분리되어야 한다.

---

## 8. 시스템 아키텍처 개요

```text
[RAGCore]
 ├─ IngestionService
 ├─ RetrievalService
 ├─ GenerationService
 ├─ MetadataStore (SQLite + SQLAlchemy)
 ├─ DocumentStorage (memory | local)
 └─ MilvusLiteVectorStore (default)

[Composition Layer]
 ├─ bootstrap_rag_core_from_docmesh
 ├─ create_rag_embedding_client
 ├─ create_rag_generation_client
 ├─ create_rag_vector_store
 ├─ load_docmesh_settings
 └─ resolve_user_id
```

### 8.1 설계 원칙
- 외부 인터페이스는 단순해야 한다.
- 내부 구현은 역할별로 분리되어야 한다.
- DocMesh 통합은 선택 가능하되 우선 경로로 지원해야 한다.
- persistence와 retrieval은 결합되지만, 저장소 역할은 분리되어야 한다.

---

## 9. 데이터 모델 요구사항

### 9.1 documents

```text
doc_id (PK)
user_id
source
created_at
storage_path
```

### 9.2 chunks

```text
chunk_id (PK, Milvus auto-id mirrored to metadata DB)
doc_id (FK -> documents.doc_id)
user_id
chunk_index
content
metadata_json
```

### 9.3 ingestion_progress

```text
progress_id (PK)
job_id
doc_id (FK -> documents.doc_id)
user_id
source
step_name
step_order
status
created_at
```

### 9.4 public records

```text
DocumentRecord
ChunkRecord
IngestResult
IngestionProgressRecord
QueryResult
```

---

## 10. 제약사항 및 리스크

### R1. 비텍스트 파일 처리 제한
- 파일 ingestion은 현재 UTF-8 decode 가능한 텍스트를 가정한다.
- 바이너리 문서, PDF, 이미지 등은 직접 지원하지 않는다.

### R2. Keycloak 설정 의존성
- Keycloak 모드에서는 DocMesh auth 설정이 올바르지 않으면 user_id 해석이 실패한다.

### R3. Milvus Lite 운영 한계
- 기본 검색 저장소는 로컬/경량 Milvus Lite다.
- 대규모 운영, 고가용성, 복잡한 멀티테넌시에는 부적합하다.

### R4. 분산 트랜잭션 부재
- delete는 vector store와 metadata/asset 전체에 대해 강한 원자성을 제공하지 않는다.

### R5. memory storage의 휘발성
- `memory` storage mode 자산은 프로세스 재시작 시 사라진다.

---

## 11. 릴리스 범위

### 11.1 현재 구현 범위
- `RAGCore`
- `bootstrap_rag_core_from_docmesh`
- 세 가지 ingestion API
- query / document management API
- progress persistence / 조회
- health check
- DocMesh settings/service registry 통합
- SQLite metadata persistence
- Milvus Lite retrieval persistence

### 11.2 이후 확장 가능 범위
- FastAPI 기반 서비스 래핑
- async ingestion / background jobs
- 외부 vector DB adapter
- richer document parsing
- advanced reranking / authorization

---

## 12. 수용 기준 (Acceptance Criteria)

1. token이 없거나 공백이면 `single-user` 스코프로 동작한다.
2. 기본 auth 모드에서 token은 그대로 user scope가 된다.
3. Keycloak 모드에서는 토큰으로부터 사용자 식별자를 해석할 수 있다.
4. 텍스트, 파일 스트림, 파일 경로 입력을 각각 적재할 수 있다.
5. `ingest_file_stream()`은 `source`가 없으면 실패한다.
6. ingestion은 `load -> preprocess -> chunking -> embedding -> vector_store -> chunk_persistence` 순서의 progress를 남긴다.
7. embedding은 chunk 전체에 대해 batch 1회 호출로 처리된다.
8. query 결과는 반드시 현재 user scope의 chunk만 포함한다.
9. prompt에는 `[System Prompt]`, `[Retrieved Context]`, `[User Query]`가 포함된다.
10. metadata는 SQLite에 저장된다.
11. 동일한 Milvus 설정을 다시 사용하면 재시작 후 retrieval이 가능하다.
12. 문서별 chunk 목록과 ingestion progress를 조회할 수 있다.
13. 삭제 성공 시 document/chunk/progress/asset/Milvus 엔트리가 함께 정리된다.
14. vector store 삭제가 실패하면 metadata는 유지되어 재시도가 가능하다.
15. health check는 metadata 및 사용 가능한 의존 서비스 상태를 집계한다.
16. bootstrap helper는 DocMesh settings와 service registry를 사용해 코어를 조립할 수 있다.

---

## 13. 요약

DocMesh RAG Core Service는 현재 **DocMesh 통합형 Python RAG 라이브러리**로 구현되어 있다. 제품의 핵심 가치는 단순한 `RAGCore` entry point, 사용자 scope 격리, SQLite + Milvus Lite 기반 경량 persistence, 세분화된 문서 관리 API, 그리고 DocMesh 설정/health/auth 연동에 있다. 이 PRD는 현재 코드가 실제로 보장하는 범위를 기준으로 작성되며, 미래 확장 항목은 별도 roadmap로 취급한다.
