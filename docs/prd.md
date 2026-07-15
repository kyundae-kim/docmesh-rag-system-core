# DocMesh RAG Core Service PRD

## 1. 문서 개요

- **문서명:** Product Requirements Document (PRD)
- **대상 제품:** DocMesh RAG Core Service
- **문서 목적:** 현재 저장소에 구현된 `rag_system_core`의 제품 목표, 범위, 제약, 운영 경계를 코드 기준으로 정의한다.
- **문서 상태:** Aligned with current implementation

이 문서는 미래 희망사항보다 **현재 코드가 실제로 제공하는 제품 동작**을 우선 서술한다.

### 1.1 용어 기준

본 문서는 `docs/api.md`, `docs/srs.md`, `docs/test.md`와 동일한 용어 기준을 사용한다.

- **user scope**: 현재 요청에 대해 해석된 사용자 경계
- **authenticated user**: 상위 애플리케이션이 전달하는 `docmesh_py_core.AuthenticatedUser`
- **`user_id`**: persistence 및 filtering에 사용되는 저장된 사용자 식별자
- **metadata store**: SQLite + SQLAlchemy 기반 document / chunk / ingestion progress persistence 계층
- **vector store**: Milvus Lite 기반 embedding 저장 및 retrieval 계층
- **document asset storage**: 문서 원문 자산을 `storage_path`로 추적하는 저장 계층
- **restart recovery**: 동일한 metadata store 및 vector store 구성을 다시 열어 상태를 재사용하는 동작
- **health check**: metadata 및 사용 가능한 의존 서비스 상태를 집계하는 점검 동작

---

## 2. 제품 배경

DocMesh RAG Core는 문서를 적재하고, 관련 컨텍스트를 검색한 뒤, generation client를 이용해 답변을 생성하는 **임베디드 Python RAG 라이브러리**다.

현재 구현의 핵심 의도:
- 상위 애플리케이션이 `RAGCore`를 통해 ingestion / retrieval / generation / document management를 단일 진입점으로 사용할 수 있어야 한다.
- metadata store와 vector store를 분리해 restart recovery가 가능해야 한다.
- user scope를 기준으로 멀티유저 데이터가 섞이지 않아야 한다.
- DocMesh settings / registry / health integration 경로를 선택적으로 사용할 수 있어야 한다.

---

## 3. 제품 목표

### 3.1 핵심 목표

1. 조립 가능한 `RAGCore` 중심 API를 제공한다.
2. 텍스트, 파일 스트림, 파일 경로 ingestion을 지원한다.
3. 사용자별 문서/청크/검색 결과 격리를 보장한다.
4. SQLite metadata + Milvus Lite vector store 기반 persistence를 제공한다.
5. factory / service-factory 기반 구성 경로를 제공한다.
6. health check와 DocMesh integration 경로를 제공한다.

### 3.2 성공 기준

- 사용자는 `RAGCore(...)`를 직접 조립할 수 있다.
- 사용자는 `bootstrap_rag_core(...)`를 service factory와 함께 사용할 수 있다.
- 사용자는 세 가지 ingestion 경로(`ingest_text`, `ingest_file_stream`, `ingest_file_path`)를 사용할 수 있다.
- query는 항상 현재 user scope로 제한된 chunk만 사용한다.
- metadata는 SQLite에 유지되고, 동일한 vector store 구성을 재사용하면 retrieval이 복원된다.
- 문서 삭제 성공 시 metadata / progress / asset / Milvus 엔트리가 함께 제거된다.
- health check는 metadata 및 사용 가능한 의존 서비스 상태를 집계한다.

---

## 4. 범위 정의

### 4.1 포함 범위 (In Scope)

- 단일 클래스 진입점 `RAGCore`
- service factory 기반 helper `bootstrap_rag_core`
- 구성 helper (`create_rag_embedding_client`, `create_rag_generation_client`, `create_rag_vector_store`, `create_rag_metadata_store`, `create_rag_document_storage`, `create_rag_chunker`)
- 텍스트 / 파일 스트림 / 파일 경로 ingestion
- 고정 길이 chunking + overlap
- embedding batch 호출
- Milvus Lite 기반 vector search
- generation client 기반 답변 생성
- `AuthenticatedUser.sub` 기반 user scope
- SQLAlchemy ORM + SQLite metadata persistence
- document asset storage (`memory`, `local`)
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

1. **단일 사용자 / 로컬 실행자**
   - 최소한의 구성으로 문서를 적재하고 질의하려는 사용자
2. **멀티유저 상위 애플리케이션**
   - 여러 사용자 데이터를 user scope 기준으로 분리해야 하는 시스템
3. **DocMesh 통합 개발자**
   - DocMesh settings / registry / health path를 재사용하려는 개발자

### 5.2 핵심 사용 시나리오

#### 시나리오 1: 직접 조립 기반 실행
- 사용자는 embedding client, generation client, vector store, metadata store, document storage, chunker를 준비한다.
- 사용자는 `RAGCore(...)`를 조립한다.
- 사용자는 `ingest_text(...)` 또는 파일 기반 ingestion 후 `query(...)`를 호출한다.

#### 시나리오 2: service factory 기반 실행
- 사용자는 DocMesh settings / registry 또는 사용자 정의 factory를 준비한다.
- 사용자는 `bootstrap_rag_core(...)`로 코어를 조립한다.
- helper는 service factory를 통해 의존 구성요소를 생성한다.

#### 시나리오 3: 사용자별 query
- 상위 애플리케이션은 인증된 `AuthenticatedUser`를 제공한다.
- 시스템은 `user.sub`를 user scope로 사용한다.
- retrieval과 조회/삭제는 해당 user scope만 대상으로 한다.

#### 시나리오 4: restart recovery
- 프로세스가 재시작되어도 SQLite metadata는 유지된다.
- 동일한 Milvus URI/collection을 다시 열면 기존 retrieval이 복원된다.

#### 시나리오 5: document management / deletion
- 사용자는 문서 목록, 특정 문서, 청크, ingestion progress를 조회할 수 있다.
- 사용자는 문서를 삭제할 수 있다.
- vector store 삭제 실패 시 metadata / asset은 보존되어 재시도할 수 있다.

#### 시나리오 6: health check
- 사용자는 `health_check()`로 metadata와 사용 가능한 의존 서비스 상태를 확인한다.
- DocMesh aggregate health path가 가능하면 이를 우선 사용한다.

---

## 6. 제품 요구사항

### 6.1 사용자 식별 요구사항

#### PRD-FR-1. 기본 사용자 식별
- 시스템은 `docmesh_py_core.AuthenticatedUser`를 입력으로 받아야 한다.
- 시스템은 `AuthenticatedUser.sub`를 `user_id`로 사용해야 한다.
- 인증과 사용자 모델 생성은 상위 애플리케이션의 책임이어야 한다.

#### PRD-FR-3. 멀티유저 격리
- 모든 document metadata와 chunk metadata에는 `user_id`가 포함되어야 한다.
- query는 반드시 `user_id` 기준 필터링을 적용해야 한다.
- 문서 조회/청크 조회/progress 조회/삭제도 현재 user scope 기준으로 제한되어야 한다.

### 6.2 문서 입력 및 저장 요구사항

#### PRD-FR-4. 문서 입력 방식
- 시스템은 다음 세 가지 ingestion API를 제공해야 한다.
  - `ingest_text(...)`
  - `ingest_file_stream(...)`
  - `ingest_file_path(...)`
- `ingest_file_stream(...)`는 `source`가 없거나 공백이면 실패해야 한다.
- 파일 기반 ingestion은 현재 구현상 UTF-8 decode 가능한 텍스트를 전제해야 한다.

#### PRD-FR-5. document asset storage
- 시스템은 `memory`와 `local` 두 가지 asset storage mode를 지원해야 한다.
- 문서 본문은 metadata row에 직접 저장하지 않고 `storage_path`로 추적해야 한다.
- `local` 모드에서는 저장 파일명이 원본 파일명과 다를 수 있으며 `doc_id + suffix` 형태가 가능해야 한다.

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
- progress status는 `running`, `completed`, `failed`를 표현할 수 있어야 한다.
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

#### PRD-FR-16. restart recovery
- metadata는 재시작 이후에도 유지되어야 한다.
- retrieval 복원은 동일한 Milvus 저장소/collection을 다시 여는 방식으로 가능해야 한다.
- SQLite가 embedding 벡터를 직접 재생성하지는 않아야 한다.

#### PRD-FR-17. document deletion
- 성공 경로에서 문서 삭제는 다음 데이터를 정리해야 한다.
  - document metadata
  - chunk metadata
  - ingestion progress metadata
  - stored asset
  - Milvus 엔트리
- vector store 삭제가 실패하면 metadata / asset 삭제를 진행하지 않아야 한다.
- 실패 후 재시도 가능해야 한다.

### 6.7 구성 및 운영성 요구사항

#### PRD-FR-18. health check
- 시스템은 metadata health check를 항상 포함해야 한다.
- vector store / embedding client / generation client가 `check()`를 제공하면 함께 포함해야 한다.
- DocMesh aggregate health path 사용을 우선 시도해야 한다.
- 실패 시 local health result로 fallback 해야 한다.

#### PRD-FR-19. 구성 helper 및 DocMesh integration
- 시스템은 구성 helper를 통해 `RAGCore` 조립을 단순화해야 한다.
- 시스템은 `docmesh_py_core.load_settings()`와 `ServiceFactoryRegistry`를 활용할 수 있어야 한다.
- `bootstrap_rag_core(...)`는 service factory를 받아 코어 조립을 수행해야 한다.
- `DocmeshRAGServiceFactory`는 DocMesh settings / registry와 함께 사용할 수 있어야 한다.

---

## 7. 비기능 요구사항

### 7.1 성능
- ingestion의 embedding 호출은 batch 방식이어야 한다.
- retrieval은 top-k 기반으로 단순하고 예측 가능해야 한다.
- health check는 빠르게 실패를 감지할 수 있어야 한다.

### 7.2 확장성
- 단일 public entry point를 유지하되 내부 책임은 ingestion / retrieval / generation / storage / composition으로 분리되어야 한다.
- 향후 API 서버나 다른 vector store 조합으로 확장 가능한 구조여야 한다.

### 7.3 데이터 격리
- 서로 다른 `AuthenticatedUser.sub` 간 데이터 혼합이 발생해서는 안 된다.
- 저장, 검색, 조회, 삭제 전 과정에서 user scope가 유지되어야 한다.

### 7.4 안정성
- metadata store persistence는 재시작 후에도 유지되어야 한다.
- 동일한 vector store 구성을 재사용하면 restart recovery가 가능해야 한다.
- document deletion 실패 시 부분 삭제로 인한 metadata 손실이 최소화되어야 한다.

### 7.5 유지보수성
- public API는 `RAGCore` 중심으로 단순해야 한다.
- 타입/프로토콜은 `rag_system_core.types`에서 명확히 정의되어야 한다.
- DocMesh integration 코드와 domain 로직은 분리되어야 한다.

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
 ├─ bootstrap_rag_core
 ├─ DocmeshRAGServiceFactory
 ├─ create_rag_embedding_client
 ├─ create_rag_generation_client
 ├─ create_rag_vector_store
 ├─ create_rag_metadata_store
 ├─ create_rag_document_storage
 ├─ create_rag_chunker
 └─ load_docmesh_settings
```

### 8.1 설계 원칙
- 외부 인터페이스는 단순해야 한다.
- 내부 구현은 역할별로 분리되어야 한다.
- 구성은 직접 조립과 service-factory 조립을 모두 허용해야 한다.
- persistence와 retrieval은 결합되지만 저장소 역할은 분리되어야 한다.

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

### R1. 조립형 생성자
- `RAGCore`는 고수준 convenience 생성자가 아니라 fully assembled dependency graph를 요구한다.
- 따라서 사용자는 factory helper 또는 자체 조립 코드를 준비해야 한다.

### R2. 비텍스트 파일 처리 제한
- 파일 ingestion은 현재 UTF-8 decode 가능한 텍스트를 가정한다.
- 바이너리 문서, PDF, 이미지 등은 직접 지원하지 않는다.

### R3. Milvus Lite 운영 한계
- 기본 검색 저장소는 로컬/경량 Milvus Lite다.
- 대규모 운영, 고가용성, 복잡한 멀티테넌시에는 부적합하다.

### R4. 분산 트랜잭션 부재
- delete는 vector store와 metadata / asset 전체에 대해 강한 원자성을 제공하지 않는다.

### R5. memory storage의 휘발성
- `memory` storage mode 자산은 프로세스 재시작 시 사라진다.

---

## 11. 릴리스 범위

### 11.1 현재 구현 범위
- `RAGCore`
- `bootstrap_rag_core`
- `DocmeshRAGServiceFactory`
- 구성 helper 일체
- 세 가지 ingestion API
- query / document management API
- progress persistence / 조회
- health check
- DocMesh settings / registry integration
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

1. 모든 user-scoped 공개 메서드는 `AuthenticatedUser`를 받는다.
2. `AuthenticatedUser.sub`가 저장 및 검색의 `user_id`로 사용된다.
3. 텍스트, 파일 스트림, 파일 경로 입력을 각각 적재할 수 있다.
4. `ingest_file_stream()`은 `source`가 없으면 실패한다.
5. ingestion은 `load -> preprocess -> chunking -> embedding -> vector_store -> chunk_persistence` 순서의 progress를 남긴다.
6. embedding은 chunk 전체에 대해 batch 1회 호출로 처리된다.
7. query 결과는 반드시 현재 user scope의 chunk만 포함한다.
8. prompt에는 `[System Prompt]`, `[Retrieved Context]`, `[User Query]`가 포함된다.
9. metadata는 SQLite에 저장된다.
10. 동일한 vector store 구성을 다시 사용하면 재시작 후 retrieval이 가능하다.
11. 문서별 chunk 목록과 ingestion progress를 조회할 수 있다.
12. 삭제 성공 시 document / chunk / progress / asset / Milvus 엔트리가 함께 정리된다.
13. vector store 삭제가 실패하면 metadata는 유지되어 재시도가 가능하다.
14. health check는 metadata 및 사용 가능한 의존 서비스 상태를 집계한다.
15. `bootstrap_rag_core(...)`는 service factory를 사용해 코어를 조립할 수 있다.

---

## 13. 요약

DocMesh RAG Core Service는 현재 **조립 가능한 Python RAG 라이브러리**로 구현되어 있다. 제품의 핵심 가치는 `RAGCore` 중심 API, user scope 격리, SQLite + Milvus Lite 기반 경량 persistence, 세분화된 document management API, 그리고 factory / DocMesh integration 경로에 있다. 이 PRD는 현재 코드가 실제로 보장하는 범위를 기준으로 유지한다.
