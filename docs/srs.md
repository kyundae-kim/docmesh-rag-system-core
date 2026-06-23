# DocMesh RAG Core Service SRS

## 1. 문서 개요

- **문서명:** Software Requirements Specification (SRS)
- **대상 제품:** DocMesh RAG Core Service
- **기준 문서:** `docs/prd.md`
- **문서 목적:** 현재 구현과 정렬된 제품 요구를 소프트웨어 요구사항 수준으로 구체화하여, 개발/테스트/검증의 기준선을 제공한다.
- **문서 상태:** Derived from current PRD and aligned with repository development docs

본 문서는 `docs/prd.md`의 제품 요구를 소프트웨어 관점에서 재구성한 것이다. 기능 요구사항, 인터페이스, 데이터 요구사항, 제약사항, 검증 기준을 명시하며, 미래 희망사항보다 **현재 코드가 보장해야 하는 소프트웨어 동작**을 우선한다.

---

## 2. 시스템 개요

DocMesh RAG Core Service는 문서를 적재하고, 사용자 스코프에 따라 관련 컨텍스트를 검색하며, LLM 기반 답변을 생성하는 Python RAG 코어 라이브러리다.

시스템의 핵심 책임은 다음과 같다.

1. 단일 진입점 `RAGCore`를 통해 ingestion / retrieval / generation 기능을 제공한다.
2. 사용자별 문서, 청크, 검색 결과를 격리한다.
3. SQLite metadata와 Milvus Lite vector store를 사용해 재시작 후에도 상태를 재사용할 수 있게 한다.
4. DocMesh 설정/서비스 팩토리/health/auth 구성과 통합 가능한 조립 경로를 제공한다.

---

## 3. 범위

### 3.1 포함 범위

- `RAGCore` 공개 API
- `bootstrap_rag_core_from_docmesh()` 기반 조립 경로
- 텍스트 / 파일 스트림 / 파일 경로 ingestion
- 문서 전처리, chunking, embedding, vector 저장, chunk metadata 저장
- 사용자 스코프 기반 retrieval 및 generation
- SQLite 기반 metadata persistence
- Milvus Lite 기반 vector persistence
- 문서 자산 저장 (`memory`, `local`)
- 문서 조회 / 청크 조회 / progress 조회 / 삭제
- health check 집계
- 선택적 Keycloak 기반 `token -> user_id` 해석

### 3.2 제외 범위

- 외부 공개용 HTTP API 서버
- UI / Frontend
- 비동기 background job queue
- 고급 reranking
- 복잡한 조직/역할 기반 권한 체계
- 분산 트랜잭션 보장
- production-grade 분산 vector DB 운영
- PDF/이미지 등 범용 비텍스트 문서 파싱

---

## 4. 이해관계자와 사용자

### 4.1 주요 사용자

1. **단일 사용자 환경**
   - 로컬 또는 단일 서비스 인스턴스에서 문서를 적재하고 질의응답을 수행하는 사용자
2. **멀티유저 상위 애플리케이션**
   - 사용자별 데이터 격리가 필요한 서비스
3. **DocMesh 통합 환경 운영자/개발자**
   - `docmesh_py_core` 설정 및 서비스 레지스트리를 활용해 코어를 조립하는 개발자

### 4.2 사용자 목표

- 최소한의 공개 API만으로 문서를 적재하고 질의할 수 있어야 한다.
- 서로 다른 사용자 간 데이터가 섞이지 않아야 한다.
- 프로세스 재시작 이후에도 metadata 및 검색 기능을 복구할 수 있어야 한다.
- 운영 중 health 상태를 확인할 수 있어야 한다.

---

## 5. 운영 환경 및 전제조건

### 5.1 소프트웨어 전제조건

- Python `>= 3.11`
- `docmesh-py-core`
- `pydantic-settings`
- `pymilvus[milvus-lite]`
- Ollama adapter를 사용하는 경우 Python 패키지 `ollama`

### 5.2 런타임 전제조건

- embedding/generation 모델에 접근 가능한 런타임이 준비되어 있어야 한다.
- SQLite 및 Milvus Lite 파일을 생성할 수 있는 쓰기 가능한 디렉터리가 있어야 한다.
- DocMesh 통합 경로 사용 시 settings 및 service registry 구성이 유효해야 한다.
- Keycloak 모드 사용 시 관련 인증 설정이 유효해야 한다.

---

## 6. 시스템 컨텍스트 및 구조

```text
[Client/Application]
        |
        v
     [RAGCore]
   /     |      \
  v      v       v
Ingestion Retrieval Generation
   |        |        |
   v        v        v
Metadata  Vector   Model Clients
 Store    Store    (Embedding/Generation)
   |
   v
Document Storage

[Composition Layer]
 - bootstrap_rag_core_from_docmesh
 - create_rag_embedding_client
 - create_rag_generation_client
 - create_rag_vector_store
 - load_docmesh_settings
 - resolve_user_id
```

### 6.1 설계 원칙

- 공개 인터페이스는 `RAGCore` 중심으로 단순해야 한다.
- 내부 책임은 ingestion / retrieval / generation / persistence / composition 으로 분리되어야 한다.
- 사용자 스코프는 저장, 조회, 검색, 삭제 전 과정에서 일관되게 적용되어야 한다.
- DocMesh 통합은 선택 가능하지만 우선 지원 경로여야 한다.

---

## 7. 외부 인터페이스 요구사항

### 7.1 공개 생성 경로

시스템은 다음 생성 경로를 제공해야 한다.

1. `RAGCore(...)`
2. `bootstrap_rag_core_from_docmesh(...)`

### 7.2 공개 데이터 타입

시스템은 최소 다음 public record를 제공해야 한다.

- `DocumentRecord`
- `ChunkRecord`
- `IngestResult`
- `IngestionProgressRecord`
- `QueryResult`

### 7.3 공개 프로토콜

시스템은 최소 다음 클라이언트 계약을 지원해야 한다.

- `EmbeddingClient.embed(texts: list[str]) -> list[list[float]]`
- `GenerationClient.generate(prompt: str) -> str`

### 7.4 공개 동작 API

시스템은 다음 동작 API를 제공해야 한다.

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

---

## 8. 기능 요구사항

### 8.1 사용자 식별 및 인증

#### SRS-FR-1. 기본 사용자 식별
- 시스템은 token 기반 사용자 식별을 지원해야 한다.
- 기본 auth 모드에서는 token 문자열 자체를 `user_id`로 사용해야 한다.
- token이 없거나 공백이면 `single-user`를 `user_id`로 사용해야 한다.

#### SRS-FR-2. Keycloak 기반 사용자 해석
- `DOCMESH_AUTH_MODE=keycloak`일 때 시스템은 Keycloak 검증을 통해 `user_id`를 해석해야 한다.
- 응답에 `sub`가 있으면 이를 우선 사용해야 한다.
- `sub`가 없고 `preferred_username`이 있으면 이를 사용해야 한다.
- 두 값이 모두 없으면 시스템은 오류를 발생시켜야 한다.

#### SRS-FR-3. 사용자 스코프 격리
- 모든 문서 metadata와 chunk metadata는 `user_id`를 포함해야 한다.
- query는 반드시 현재 `user_id` 범위의 chunk만 검색 대상으로 사용해야 한다.
- 문서 조회, 청크 조회, progress 조회, 삭제 역시 현재 `user_id` 범위로 제한되어야 한다.

### 8.2 문서 입력 및 자산 저장

#### SRS-FR-4. ingestion 입력 방식
- 시스템은 문자열, 파일 스트림, 파일 경로 기반 ingestion을 지원해야 한다.
- 이를 위해 `ingest_text(...)`, `ingest_file_stream(...)`, `ingest_file_path(...)`를 제공해야 한다.
- `ingest_file_stream(...)`는 `source`가 비어 있거나 누락되면 실패해야 한다.

#### SRS-FR-5. 문서 자산 저장 모드
- 시스템은 `memory`와 `local` 두 가지 asset storage mode를 지원해야 한다.
- 문서 본문 전체를 document metadata row에 직접 저장해서는 안 된다.
- 시스템은 자산 위치를 `storage_path`로 추적해야 한다.
- `local` 모드에서는 저장 파일명이 원본 파일명과 다를 수 있으며 `doc_id + suffix` 규칙을 허용해야 한다.

#### SRS-FR-6. 문서 metadata 구조
- 시스템은 최소 다음 필드를 유지해야 한다.

```json
{
  "doc_id": "string",
  "user_id": "string",
  "source": "string",
  "created_at": "ISO-8601 string",
  "storage_path": "string | null"
}
```

### 8.3 ingestion 파이프라인

#### SRS-FR-7. 파이프라인 순서
시스템은 ingestion 시 다음 단계 순서를 사용해야 한다.

1. `load`
2. `preprocess`
3. `chunking`
4. `embedding`
5. `vector_store`
6. `chunk_persistence`

#### SRS-FR-8. 전처리와 청킹
- 전처리는 현재 구현 기준 `strip()` 수준이어야 한다.
- 시스템은 고정 길이 window + overlap chunking을 수행해야 한다.
- 전처리 후 빈 텍스트는 ingest할 수 없어야 한다.

#### SRS-FR-9. ingestion progress 추적
- 각 ingestion 실행은 `job_id`로 구분되어야 한다.
- 각 단계는 `running`, `completed`, `failed` 상태를 기록할 수 있어야 한다.
- progress 조회는 문서와 현재 user scope 기준으로 제한되어야 한다.

### 8.4 embedding / generation

#### SRS-FR-10. embedding 호출 계약
- 시스템은 embedding batch 호출을 지원해야 한다.
- ingestion 시 chunk 전체는 단일 `embed(chunks)` 호출로 처리되어야 한다.
- 반환 벡터 개수는 입력 chunk 수와 정확히 일치해야 한다.

#### SRS-FR-11. generation 호출 계약
- generation은 완성된 단일 prompt 문자열을 입력으로 받아야 한다.
- generation 결과는 최종 답변 문자열이어야 한다.

#### SRS-FR-12. prompt 구성
시스템이 생성하는 prompt는 최소 다음 섹션을 포함해야 한다.

```text
[System Prompt]
[Retrieved Context]
[User Query]
```

### 8.5 retrieval 및 vector store

#### SRS-FR-13. 기본 vector store
- 기본 vector store 구현은 Milvus Lite여야 한다.
- collection이 없으면 첫 insert 시 embedding dimension을 기준으로 생성해야 한다.
- 검색은 반드시 `user_id` filter를 강제해야 한다.

#### SRS-FR-14. vector store 설정 해석
- 시스템은 Milvus runtime 설정을 우선적으로 DocMesh settings에서 읽어야 한다.
- 설정이 없으면 다음 fallback을 사용해야 한다.
  - URI: `metadata_path.with_suffix(".milvus.db")`
  - Collection: `rag_chunks`
  - Timeout: `30.0`

### 8.6 persistence 및 삭제

#### SRS-FR-15. metadata persistence
- 시스템은 SQLite와 SQLAlchemy ORM을 사용해야 한다.
- 최소 `documents`, `chunks`, `ingestion_progress` 테이블을 유지해야 한다.

#### SRS-FR-16. 재시작 복원
- metadata는 재시작 이후에도 유지되어야 한다.
- retrieval은 동일한 Milvus 저장소/collection을 다시 열어 복원 가능해야 한다.
- SQLite는 embedding 벡터 자체를 재생성하는 책임을 가져서는 안 된다.

#### SRS-FR-17. 문서 삭제
- 삭제 성공 경로에서 시스템은 다음 대상을 정리해야 한다.
  - document metadata
  - chunk metadata
  - ingestion progress metadata
  - stored asset
  - Milvus 엔트리
- vector store 삭제가 실패하면 metadata/asset 삭제를 진행해서는 안 된다.
- 실패 후 재시도 가능해야 한다.

### 8.7 운영성 및 통합

#### SRS-FR-18. health check
- 시스템은 metadata health check를 항상 포함해야 한다.
- vector store / embedding client / generation client가 `check()`를 제공하면 함께 포함해야 한다.
- DocMesh 공통 health aggregator를 우선 사용해야 한다.
- 공통 aggregator 사용에 실패하면 로컬 health 결과로 fallback 해야 한다.

#### SRS-FR-19. DocMesh 통합
- 시스템은 `docmesh_py_core.load_settings()`와 `ServiceFactoryRegistry`를 활용할 수 있어야 한다.
- bootstrap helper는 DocMesh 환경에서 코어 조립을 단순화해야 한다.

---

## 9. 데이터 요구사항

### 9.1 documents 테이블

```text
doc_id (PK)
user_id
source
created_at
storage_path
```

### 9.2 chunks 테이블

```text
chunk_id (PK, Milvus auto-id mirrored to metadata DB)
doc_id (FK -> documents.doc_id)
user_id
chunk_index
content
metadata_json
```

### 9.3 ingestion_progress 테이블

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

### 9.4 데이터 무결성 요구사항

- 각 document는 하나의 `doc_id`를 가져야 한다.
- 각 chunk는 소속 document와 `user_id`를 가져야 한다.
- progress row는 `job_id`, `doc_id`, `user_id`, `step_name`, `status`를 통해 추적 가능해야 한다.
- chunk metadata는 `metadata_json` 형태로 저장 가능해야 한다.

---

## 10. 비기능 요구사항

### 10.1 성능
- ingestion의 embedding 호출은 batch 방식이어야 한다.
- retrieval은 top-k 기반의 단순하고 예측 가능한 흐름이어야 한다.
- health check는 빠르게 실패를 감지할 수 있어야 한다.

### 10.2 확장성
- 시스템은 단일 entry point를 유지하면서 내부 책임을 분리해야 한다.
- 향후 API 서버, 외부 vector store adapter, background ingestion으로 확장 가능한 구조여야 한다.

### 10.3 데이터 격리
- 서로 다른 사용자 간 데이터가 저장, 조회, 검색, 삭제 과정에서 혼합되어서는 안 된다.

### 10.4 안정성
- metadata persistence는 재시작 후에도 유지되어야 한다.
- Milvus 설정이 동일하면 retrieval이 재개 가능해야 한다.
- 삭제 실패 시 부분 삭제로 인한 metadata 손실이 최소화되어야 한다.

### 10.5 유지보수성
- public API는 `RAGCore` 중심으로 단순해야 한다.
- 타입과 프로토콜은 명확히 분리되어야 한다.
- DocMesh 통합 코드와 도메인 로직은 분리되어야 한다.

---

## 11. 제약사항 및 리스크

### 11.1 비텍스트 파일 처리 제한
- 현재 파일 ingestion은 UTF-8 decode 가능한 텍스트를 전제로 한다.
- 바이너리, PDF, 이미지 등은 직접 지원하지 않는다.

### 11.2 Keycloak 구성 의존성
- Keycloak 모드에서는 외부 auth 설정이 잘못되면 `user_id` 해석이 실패할 수 있다.

### 11.3 Milvus Lite 운영 한계
- 기본 vector store는 경량/로컬 Milvus Lite다.
- 대규모 운영, 고가용성, 복잡한 멀티테넌시에 적합하지 않다.

### 11.4 분산 트랜잭션 부재
- vector store와 metadata/asset 전부에 대한 강한 원자성을 보장하지 않는다.

### 11.5 memory storage 휘발성
- `memory` storage mode의 자산은 프로세스 재시작 시 유지되지 않는다.

---

## 12. 검증 및 수용 기준

### 12.1 기능 수용 기준

1. token이 없거나 공백이면 `single-user` 스코프로 동작해야 한다.
2. 기본 auth 모드에서 token은 그대로 user scope가 되어야 한다.
3. Keycloak 모드에서는 토큰으로부터 사용자 식별자를 해석할 수 있어야 한다.
4. 텍스트, 파일 스트림, 파일 경로 입력을 각각 적재할 수 있어야 한다.
5. `ingest_file_stream()`은 `source`가 없으면 실패해야 한다.
6. ingestion은 `load -> preprocess -> chunking -> embedding -> vector_store -> chunk_persistence` 순서의 progress를 남겨야 한다.
7. embedding은 chunk 전체에 대해 batch 1회 호출로 처리되어야 한다.
8. query 결과는 반드시 현재 user scope의 chunk만 포함해야 한다.
9. prompt에는 `[System Prompt]`, `[Retrieved Context]`, `[User Query]`가 포함되어야 한다.
10. metadata는 SQLite에 저장되어야 한다.
11. 동일한 Milvus 설정을 다시 사용하면 재시작 후 retrieval이 가능해야 한다.
12. 문서별 chunk 목록과 ingestion progress를 조회할 수 있어야 한다.
13. 삭제 성공 시 document/chunk/progress/asset/Milvus 엔트리가 함께 정리되어야 한다.
14. vector store 삭제가 실패하면 metadata는 유지되어 재시도가 가능해야 한다.
15. health check는 metadata 및 사용 가능한 의존 서비스 상태를 집계해야 한다.
16. bootstrap helper는 DocMesh settings와 service registry를 사용해 코어를 조립할 수 있어야 한다.

### 12.2 테스트 정렬 기준

이 SRS는 `docs/test.md`의 다음 검증 축과 정렬되어야 한다.

- 사용자 스코프 및 인증
- 문서 적재 API
- 문서 자산 저장
- SQLAlchemy ORM persistence
- ingestion progress
- embedding / query / prompt
- 재시작 복원
- 삭제 및 rollback 특성
- DocMesh 통합
- Ollama adapter 계약

---

## 13. 요구사항 추적표

| PRD 요구 | SRS 요구 | 설명 |
|---|---|---|
| PRD-FR-1 ~ 3 | SRS-FR-1 ~ 3 | 사용자 식별 및 격리 |
| PRD-FR-4 ~ 6 | SRS-FR-4 ~ 6 | 입력 방식 및 문서 metadata |
| PRD-FR-7 ~ 9 | SRS-FR-7 ~ 9 | ingestion 파이프라인 및 progress |
| PRD-FR-10 ~ 12 | SRS-FR-10 ~ 12 | embedding / generation / prompt |
| PRD-FR-13 ~ 14 | SRS-FR-13 ~ 14 | vector store 및 설정 해석 |
| PRD-FR-15 ~ 17 | SRS-FR-15 ~ 17 | persistence / 복원 / 삭제 |
| PRD-FR-18 ~ 19 | SRS-FR-18 ~ 19 | health / DocMesh 통합 |

---

## 14. 요약

본 SRS는 `docs/prd.md`의 제품 요구를 구현/테스트 가능한 소프트웨어 요구사항으로 구체화한 문서다. 핵심은 다음 네 가지다.

1. `RAGCore` 중심의 단순한 공개 인터페이스
2. 사용자 스코프 기반 데이터 격리
3. SQLite + Milvus Lite 기반의 경량 persistence 및 재시작 복원
4. DocMesh 설정, 인증, health 체계와의 통합 가능성

이 문서는 현재 저장소 구현을 기준으로 유지되어야 하며, 기능/인터페이스/데이터 구조 변경 시 `docs/prd.md`, `docs/api.md`, `docs/test.md`와 함께 동기화되어야 한다.
