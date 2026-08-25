# DocMesh RAG Core Service PRD

## 1. 문서 개요

- **문서명:** Product Requirements Document (PRD)
- **대상 제품:** DocMesh RAG Core Service
- **문서 목적:** 현재 저장소에 구현된 `rag_system_core`의 제품 목표, 범위, 제약, 운영 경계를 코드 기준으로 정의한다.
- **문서 상태:** `rag-system-core v0.4.0` implementation baseline (declared runtime contract: `dms-core>=0.9.0`, `ollama>=0.6.2`, `pydantic-settings>=2.14.1`, `pymilvus[milvus-lite]>=3.0.1`)

이 문서는 미래 희망사항보다 **현재 코드가 실제로 제공하는 제품 동작**을 우선 서술한다.

### 1.1 용어 기준

본 문서는 `README.md`와 `docs/srs.md`에서 사용하는 용어 기준과 구현 계약을 따른다.

- **user scope**: 현재 요청에 대해 해석된 사용자 경계
- **authenticated user**: 상위 애플리케이션이 전달하는 `rag_system_core.types.AuthenticatedUser`
- **`user_id`**: persistence 및 filtering에 사용되는 저장된 사용자 식별자
- **metadata store**: SQLite + SQLAlchemy 기반 document / chunk / ingestion progress persistence 계층
- **vector store**: 표준 composition에서 Milvus adapter가 담당하는 embedding 저장 및 retrieval 계층
- **document asset storage**: dms-core가 관리하는 source asset을 opaque `asset_reference`로 추적하는 저장 계층
- **restart recovery**: 동일한 metadata store 및 vector store 구성을 다시 열어 상태를 재사용하는 동작


---

## 2. 제품 배경

DocMesh RAG Core는 문서를 적재하고, 관련 컨텍스트를 검색한 뒤, generation client를 이용해 답변을 생성하는 **임베디드 Python RAG 라이브러리**다.

현재 구현의 핵심 의도:
- 상위 애플리케이션이 `RAGCore`를 통해 ingestion / retrieval / generation / document management를 단일 진입점으로 사용할 수 있어야 한다.
- metadata store와 vector store를 분리해 restart recovery가 가능해야 한다.
- user scope를 기준으로 멀티유저 데이터가 섞이지 않아야 한다.
- 표준 composition 경로에서는 `rag_system_core.composition`의 RAG runtime settings/ServiceBundle과 dms-core client assembly를 사용하고, 테스트·사용자 정의 경로에서는 동일한 port를 구현한 의존성을 직접 주입할 수 있어야 한다.

---

## 3. 제품 목표

### 3.1 핵심 목표

1. 조립 가능한 `RAGCore` 중심 API를 제공한다.
2. 텍스트, 파일 스트림, 파일 경로 ingestion을 지원한다.
3. 사용자별 문서/청크/검색 결과 격리를 보장한다.
4. SQLite RAG metadata + Milvus vector store adapter + dms-core source asset lifecycle을 제공한다.
5. factory / service-factory 기반 구성 경로를 제공한다.
6. host-owned client 기반 service-factory 조립과 명시적 collaborator 주입을 제공하되, caller-owned 자원과 compatibility metadata store의 lifecycle 경계를 명확히 한다.


### 3.2 성공 기준

- 사용자는 `RAGCore(...)`를 직접 조립할 수 있다.
- 사용자는 `DocmeshRAGServiceFactory.from_host_clients(...)`로 직접 만든 DMS용 SQLAlchemy `Engine`, metadata용 SQLAlchemy `Engine`, MinIO, Ollama, Milvus transport client와 명시적 model/store 설정을 전달하고 `create_rag_core(...)`를 호출하거나, 이미 구성된 의존성으로 `DocmeshRAGServiceFactory.from_clients(...)`를 직접 조립할 수 있다.
- 사용자는 세 가지 ingestion 경로(`ingest_text`, `ingest_file_stream`, `ingest_file_path`)를 사용할 수 있다.
- query는 항상 현재 user scope로 제한된 chunk만 사용한다.
- metadata는 SQLite에 유지되고, 동일한 vector store 구성을 재사용하면 retrieval이 복원된다.
- 문서 삭제 성공 시 metadata / progress / Milvus 엔트리가 제거되고 DMS asset은 soft delete된다.


---

## 4. 범위 정의

### 4.1 포함 범위 (In Scope)

- 단일 클래스 진입점 `RAGCore`
- host-owned client 기반 `DocmeshRAGServiceFactory.from_host_clients(...)`
- 구성 helper 및 `DocmeshRAGServiceFactory`
- 텍스트 / 파일 스트림 / 파일 경로 ingestion
- 고정 길이 chunking + overlap
- embedding batch 호출
- `MilvusLiteVectorStore` adapter 기반 vector search (local Milvus Lite 또는 주입된 remote Milvus client)
- generation client 기반 답변 생성
- `AuthenticatedUser.sub` 기반 user scope
- SQLAlchemy ORM + SQLite metadata persistence
- dms-core 기반 document asset storage (MinIO object storage + PostgreSQL/SQLite DMS metadata)
- 문서 목록/단건/청크/progress 및 단계별 최종 상태 조회
- 문서 삭제


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
   - composition-layer settings / assembled service clients를 재사용하려는 개발자

### 5.2 핵심 사용 시나리오

#### 시나리오 1: 직접 조립 기반 실행
- 사용자는 embedding client, generation client, vector store, metadata store, document storage, chunker를 준비한다.
- 사용자는 `RAGCore(...)`를 조립한다.
- 사용자는 `ingest_text(...)` 또는 파일 기반 ingestion 후 `query(...)`를 호출한다.

#### 시나리오 2: service factory 기반 직접 조립
- 사용자는 composition layer의 `ServiceConfigs`/`ServiceBundle`을 사용해 필요한 RAG adapter를 먼저 준비하고, DMS용 SQLAlchemy `Engine`과 MinIO client를 준비한다.
- 사용자는 명시적으로 준비한 RAG collaborator와 DMS client를 `DocmeshRAGServiceFactory.from_clients(..., metadata_engine=...)`에 전달한다. 이 classmethod는 dms-core SDK를 생성해 Factory에 보관하지만, dms-core v0.9 SDK에는 `close()` lifecycle이 없어 Factory context 종료 시 DMS SDK를 닫지 않는다.
- `DocmeshRAGServiceFactory`는 settings나 `ServiceBundle`을 보관하지 않고, 전달된 collaborator만 반환한다. 주입된 Engine, MinIO client, RAG collaborator의 lifecycle은 호출자가 관리한다.

#### 시나리오 2-1: host-owned client 기반 실행
- 상위 애플리케이션은 DMS용 SQLAlchemy `Engine`, metadata용 SQLAlchemy `Engine`, MinIO client, DMS bucket name, Ollama client, Milvus client와 embedding/generation model 및 vector-store 설정을 직접 준비한다.
- `DocmeshRAGServiceFactory.from_host_clients(...)`는 DMS 입력을 `create_dms_sdk_from_clients()`를 통해 dms-core의 `DocumentManagementSDKFactory`에 전달하고, metadata용 Engine과 Ollama/Milvus transport client로 RAG embedding client, generation client, vector store를 조립한 Factory를 반환한다. `create_rag_core(...)`가 이를 `RAGCore`에 전달한다.
- 이 경로는 DocMesh/DMS 환경 설정을 읽지 않는다. Factory는 생성한 DMS SDK를 보관하지만 dms-core v0.9의 SDK에 `close()`가 없으므로 context 종료 시 닫지 않는다. DMS/metadata Engine과 MinIO, Ollama, Milvus raw transport client는 상위 애플리케이션이 소유하고 정리한다.

#### 시나리오 3: 사용자별 query
- 상위 애플리케이션은 인증된 `AuthenticatedUser`를 제공한다.
- 시스템은 `user.sub`를 user scope로 사용한다.
- retrieval과 조회/삭제는 해당 user scope만 대상으로 한다.

#### 시나리오 4: restart recovery
- 프로세스가 재시작되어도 SQLite metadata는 유지된다.
- 동일한 Milvus URI/collection을 다시 열면 기존 retrieval이 복원된다.

#### 시나리오 5: document management / deletion
- 사용자는 문서 목록, 특정 문서, 청크, ingestion progress와 단계별 최종 상태를 조회할 수 있다.
- 사용자는 문서를 삭제할 수 있다.
- vector store 삭제 실패 시 metadata / asset은 보존되어 재시도할 수 있다.
- DMS soft delete 실패 시 RAG metadata는 보존되어 재시도할 수 있다.

---

## 6. 제품 요구사항

### 6.1 사용자 식별 요구사항

#### PRD-FR-1. 기본 사용자 식별
- 시스템은 `rag_system_core.types.AuthenticatedUser`를 입력으로 받아야 한다.

#### PRD-FR-2. resolved user identity
- 시스템은 `AuthenticatedUser.sub`를 저장 및 filtering에 사용하는 `user_id`로 해석해야 한다.
- 인증과 사용자 모델 생성은 상위 애플리케이션의 책임이어야 한다.

#### PRD-FR-3. 멀티유저 격리
- 모든 document metadata와 chunk metadata에는 `user_id`가 포함되어야 한다.
- query는 반드시 `user_id` 기준 필터링을 적용해야 한다.
- 문서 조회/청크 조회/progress 조회/삭제도 현재 user scope 기준으로 제한되어야 한다.
- 삭제 격리는 `RAGCore`가 먼저 user-scoped document lookup을 성공한 경우에만 vector/DMS 삭제를 호출하는 방식으로 보장해야 한다.

### 6.2 문서 입력 및 저장 요구사항

#### PRD-FR-4. 문서 입력 방식
- 시스템은 다음 세 가지 ingestion API를 제공해야 한다.
  - `ingest_text(...)`
  - `ingest_file_stream(...)`
  - `ingest_file_path(...)`
- `ingest_file_stream(...)`는 `source`가 없거나 공백이면 실패해야 한다.
- 파일 기반 ingestion은 현재 구현상 UTF-8 decode 가능한 텍스트를 전제해야 한다.

#### PRD-FR-5. document asset storage
- 표준 production composition은 dms-core SDK를 통해 document source asset을 저장해야 한다.
- 문서 본문은 RAG metadata row에 직접 저장하지 않고 opaque `asset_reference`로 추적해야 한다.
- DMS 업로드에는 RAG의 `doc_id`를 동일한 `document_id`로 전달하고, 내부 MinIO key는 노출하지 않아야 한다.
- DMS가 요청한 `doc_id`와 다른 `document_id`를 반환하면 계약 위반으로 실패해야 한다.
- `ingest_text`의 DMS 업로드는 `user_id`, `source`, ingestion `job_id` 기반 idempotency 정보를 DMS에 전달해야 한다. 현재 file-stream/file-path 업로드 adapter는 DMS 호출에 idempotency key를 전달하지 않는다.
- `ingest_text`는 `strip()`으로 정규화된 텍스트를 저장하고, file-stream API는 읽은 byte payload를, file-path API는 업로드 시점의 source file 내용을 source asset으로 저장해야 한다. file-path API의 `source`가 없으면 파일명을 사용한다.
- DMS asset이 없거나 이미 삭제된 경우 asset load는 `None`을 반환해야 한다.

#### PRD-FR-6. 문서 metadata
- 문서 metadata는 최소 다음 필드를 가져야 한다.

```json
{
  "doc_id": "string",
  "user_id": "string",
  "source": "string",
  "created_at": "ISO-8601 string",
  "asset_reference": "string | null"
}
```

### 6.3 Ingestion 파이프라인 요구사항

#### PRD-FR-7. 파이프라인 단계
시스템은 progress tracking 시작 전에 API 경로별 source 읽기/UTF-8 decode와 DMS asset 업로드를 수행하고, `_finalize_ingest` 진입 후 document metadata를 생성한 뒤 다음 후속 처리 단계를 progress로 추적해야 한다.

1. `load`
2. `preprocess`
3. `chunking`
4. `embedding`
5. `vector_store`
6. `chunk_persistence`

#### PRD-FR-8. 전처리/청킹
- 전처리는 현재 구현 기준 `strip()` 수준이어야 한다.
- 표준 factory가 제공하는 chunking은 고정 길이 window + overlap 방식을 사용해야 한다.
- `chunk_size`는 양수, `chunk_overlap`은 0 이상이면서 `chunk_size`보다 작아야 한다.
- 빈 텍스트는 ingest할 수 없어야 한다.

#### PRD-FR-9. progress persistence
- 각 ingestion 실행은 `job_id`로 구분되어야 한다.
- progress status는 `running`, `completed`, `failed`를 표현할 수 있어야 한다.
- progress 조회는 문서와 user scope 기준으로 제한되어야 한다.
- `RAGCore.get_ingestion_step_statuses(...)`는 각 정의된 파이프라인 단계의 최종 확인 상태를 반환해야 하며, 아직 실행되지 않은 후속 단계는 `not_started`로 표시해야 한다.
- vector insert 후 해당 단계의 `completed` progress 저장이 실패하면 방금 생성한 vector를 보상 삭제해야 한다.
- vector store가 chunk 수와 다른 개수의 ID를 반환하면 반환된 ID를 보상 삭제하고 ingestion을 실패시켜야 한다.
- chunk metadata 저장이 실패하면 생성한 vector를 보상 삭제해야 한다.
- `chunk_persistence=completed` progress 저장이 실패하면 metadata chunk와 vector를 모두 보상 삭제해야 한다.
- 복수 보상 작업 중 하나가 실패해도 나머지 보상은 계속 실행하고, cleanup 오류는 원래 pipeline 오류를 대체하지 않아야 한다.
- 위 보상 범위는 vector와 chunk metadata이며, 이미 생성된 document metadata, DMS asset, progress row의 전체 rollback을 보장하지 않아야 한다.

### 6.4 Embedding / Generation 요구사항

#### PRD-FR-10. embedding 호출
- embedding은 batch 호출을 지원해야 한다.
- ingestion 시 chunk 전체는 하나의 `embed(chunks)` 호출로 처리되어야 한다.
- embedding/vector-store adapter 계약은 chunk와 vector 개수 일치를 요구해야 하며, 표준 Milvus adapter는 불일치를 감지하면 ingestion을 실패시켜야 한다.

#### PRD-FR-11. generation 호출
- generation은 완성된 단일 prompt 문자열을 입력으로 받아야 한다.
- generation 결과는 최종 답변 문자열이어야 한다.
- 표준 Ollama adapter는 비어 있지 않은 embedding/generation model 설정을 요구하고 transport 또는 응답 형식 오류를 명확한 runtime 오류로 변환해야 한다.

#### PRD-FR-12. prompt 구조
prompt는 최소 아래 섹션을 포함해야 한다.

```text
[System Prompt]
[Retrieved Context]
[User Query]
```

### 6.5 Vector Store 요구사항

#### PRD-FR-13. 기본 vector store
- 표준 `DocmeshRAGServiceFactory`는 `MilvusLiteVectorStore` adapter를 제공해야 하며, 실제 local/remote 연결 방식은 주입되거나 composition layer가 조립한 Milvus client/configuration을 따라야 한다.
- collection이 없으면 첫 insert 시 embedding dimension 기준으로 생성해야 한다.
- 검색은 `user_id` filter를 강제해야 한다.

#### PRD-FR-14. 설정 해석
- Milvus service client는 명시적으로 주입하거나 composition-layer RAG settings / `ServiceBundle`에서 조립해야 한다.
- service client를 조립할 수 없으면 명확한 구성 오류로 실패해야 한다.
- collection과 timeout이 명시되지 않았고 composition-layer 설정에도 값이 없으면 각각 `rag_chunks`, `30.0`을 사용해야 한다.
- 명시적 Milvus client는 client 생성을 대체한다. `settings`/`bundle`이 없으면 collection/timeout은 각각 `rag_chunks`, `30.0`을 사용하며 process environment variable은 읽지 않는다.

### 6.6 Persistence 및 삭제 요구사항

#### PRD-FR-15. metadata persistence
- `metadata_path` 호환 경로에서 표준 `DocmeshRAGServiceFactory`는 SQLite + SQLAlchemy ORM metadata store를 생성해야 하며, host-client 경로에서는 caller가 제공한 SQLAlchemy `Engine`에 metadata store를 바인딩해야 한다. 직접 조립 경로는 다른 `MetadataRepository` 구현을 주입할 수 있어야 한다.
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
  - DMS asset (soft delete)
  - Milvus 엔트리
- vector store 삭제가 실패하면 metadata / asset 삭제를 진행하지 않아야 한다.
- DMS soft delete가 실패하면 RAG metadata를 삭제하지 않아야 한다.
- DMS에서 이미 없거나 이미 삭제된 자산은 삭제 완료로 취급해야 한다.
- 삭제 순서는 vector → DMS soft delete → RAG metadata여야 한다.
- vector 삭제 실패 시 asset과 metadata를 보존해야 한다.
- DMS soft delete 실패 시 metadata는 보존하지만 vector는 이미 삭제됐을 수 있어야 한다.
- metadata 삭제 실패 시 vector와 DMS asset은 이미 정리됐을 수 있으며 분산 rollback을 제공하지 않아야 한다.

### 6.7 구성 및 운영성 요구사항

#### PRD-FR-19. 구성 helper 및 DocMesh integration
- 시스템은 구성 helper를 통해 `RAGCore` 조립을 단순화해야 한다.
- 시스템은 composition layer의 `build_docmesh_runtime_plan()`과
  `assemble_docmesh_services()`를 활용할 수 있어야 한다. `assemble_docmesh_services()`는
  명시적으로 전달된 `ServiceConfigs`를 `RuntimePlan`, `ServiceBundle`과 함께 사용한다.
- `create_rag_embedding_client`, `create_rag_generation_client`,
  `create_rag_vector_store`는 명시적 settings, `ServiceBundle`, 또는 client를
  받아 RAG adapter/store를 구성할 수 있어야 한다.
- `DocmeshRAGServiceFactory`는 생성하거나 직접 주입받은 DMS SDK와 명시적으로 주입된 embedding/generation/vector collaborator를 사용해야 하며, settings나 `ServiceBundle`을 내부에 보관하거나 이를 통해 지연 생성해서는 안 된다.
- DMS 조립은 현재 프로세스 환경을 읽지 않고, caller가 제공한 SQLAlchemy `Engine`, MinIO client, bucket 이름을 통해 명시적으로 수행해야 한다.
- `assemble_docmesh_services()`가 반환하는 `ServiceBundle`은 caller가 정상/예외 종료 모두에서 `close()`해야 한다. DMS SDK는 dms-core v0.9에서 `close()`를 제공하지 않으므로 underlying DMS Engine과 MinIO client의 lifecycle은 caller가 관리한다.
- `DocmeshRAGServiceFactory.from_clients(...)`와 `from_host_clients(...)`는 생성한 DMS SDK와 주입된 Engine/raw transport client를 context 종료 시 닫지 않는다. `metadata_engine`이 주입된 경우 MetadataStore도 Factory가 닫지 않으며, `metadata_path` 호환 경로로 Factory가 생성해 추적한 MetadataStore만 Factory `close()`에서 정리한다.

---

## 7. 비기능 요구사항

### 7.1 성능
- ingestion의 embedding 호출은 batch 방식이어야 한다.
- retrieval은 top-k 기반으로 단순하고 예측 가능해야 한다.


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
- 공개 record는 `rag_system_core.types`, dependency protocol의 canonical owner는
  `rag_system_core.ports`여야 한다. 기존 `rag_system_core.types` protocol import는
  호환 경로로 유지할 수 있다.
- DocMesh RAG runtime, DMS runtime, domain 로직은 서로 분리되어야 한다.

---

## 8. 시스템 아키텍처 개요

```text
[RAGCore]
 ├─ IngestionService
 ├─ RetrievalService
 ├─ GenerationService
 ├─ MetadataStore (SQLite + SQLAlchemy)
 ├─ DmsDocumentStorage (dms-core + MinIO)
 └─ MilvusLiteVectorStore (default)

[Composition Layer]
 ├─ service_factory.py (DMS-backed Factory and RAGCore assembly)
 ├─ rag_factories.py (RAG adapter/store construction)
 ├─ factories.py (stable advanced re-export surface)
 ├─ docmesh_runtime (Ollama / Milvus settings and assembly)
 └─ dms_runtime (explicit host-client DMS SDK assembly)

[Contract Layer]
 ├─ types.py (public records)
 └─ ports.py (dependency protocols)
```

### 8.1 설계 원칙
- 외부 인터페이스는 단순해야 한다.
- 내부 구현은 역할별로 분리되어야 한다.
- 구성은 직접 조립과 service-factory 조립을 모두 허용해야 한다.
- persistence와 retrieval은 결합되지만 저장소 역할은 분리되어야 한다.
- DMS client assembly는 RAG용 DocMesh runtime assembly와 별도 module이 소유하며, process environment를 해석하지 않는다.

---

## 9. 데이터 모델 요구사항

### 9.1 documents

```text
doc_id (PK)
user_id
source
created_at
storage_path (DB 호환 column명, public record에서는 asset_reference)
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

### 9.5 public surface 계층

| 계층 | 지원 인터페이스 |
|---|---|
| package root `rag_system_core` | `RAGCore`, `RAGServiceFactory`, `DocmeshRAGServiceFactory`, 두 Ollama adapter, public records, `EmbeddingClient`/`GenerationClient`, `AuthenticatedUser` |
| `rag_system_core.composition` | `assemble_docmesh_services`, `create_dms_sdk_from_clients`, `create_docmesh_service_client`, 두 service-factory type |
| `rag_system_core.composition.factories` | `create_rag_embedding_client`, `create_rag_generation_client`, `create_rag_vector_store` |

`build_docmesh_runtime_plan()`, `ServiceBundle` 같은 advanced composition/runtime helper는 package-root 또는 `rag_system_core.composition` re-export가 아니며 module-qualified import를 사용해야 한다.

---

## 10. 제약사항 및 리스크

### R1. 조립형 생성자
- `RAGCore`는 고수준 convenience 생성자가 아니라 fully assembled dependency graph를 요구한다.
- 따라서 사용자는 factory helper 또는 자체 조립 코드를 준비해야 한다.
- `DocmeshRAGServiceFactory.create_rag_core()`는 `metadata_engine`이 주입된 Factory에서 바로 사용할 수 있다. `metadata_engine`이 없으면 `create_metadata_store(metadata_path=...)`는 사용할 수 있지만 `create_rag_core()`가 `metadata_path`를 대신 받아 주지는 않는다.

### R2. 비텍스트 파일 처리 제한
- 파일 ingestion은 현재 UTF-8 decode 가능한 텍스트를 가정한다.
- 바이너리 문서, PDF, 이미지 등은 직접 지원하지 않는다.

### R3. Milvus 운영 경계
- 표준 adapter의 실제 연결 방식은 Milvus client/configuration에 따르며 local file URI와 외부 Milvus 연결을 모두 사용할 수 있다.
- 이 라이브러리는 외부 Milvus의 배포, 고가용성, 용량 계획을 제공하지 않는다.

### R4. 분산 트랜잭션 부재
- delete는 vector store와 metadata / asset 전체에 대해 강한 원자성을 제공하지 않는다.

### R5. 부분 ingestion 잔여물
- source 읽기/일부 UTF-8 decode, asset 업로드, document metadata 저장은 progress로 추적되는 후속 처리보다 앞서 수행된다.
- 후속 단계가 실패하면 progress에는 실패가 기록되지만 document metadata와 DMS asset이 자동으로 모두 제거되는 강한 트랜잭션은 제공하지 않는다.
- file-path payload의 UTF-8 decode는 DMS 업로드 뒤 수행되므로 decode 실패 시 document metadata 없이 DMS asset만 남을 수 있다.

### R6. lifecycle 소유권
- 직접 구성한 `RAGCore`, collaborator, Engine, raw transport client의 lifecycle은 caller가 관리해야 한다.
- `ServiceBundle.close()`는 bundle이 조립한 client 중 `close()`를 제공하는 client를 정리한다.
- `DocmeshRAGServiceFactory`는 dms-core v0.9 SDK에 close API가 없으므로 DMS SDK나 주입된 DMS/metadata Engine, MinIO, Ollama, Milvus client를 정리하지 않는다. Factory가 `metadata_path`로 생성해 추적한 MetadataStore만 Factory `close()`에서 정리한다.

---

## 11. 릴리스 범위

### 11.1 현재 구현 범위
- `RAGCore`
- `DocmeshRAGServiceFactory.from_host_clients(...)`
- `DocmeshRAGServiceFactory`
- `RAGServiceFactory`
- module-qualified advanced helpers: `create_rag_embedding_client`, `create_rag_generation_client`, `create_rag_vector_store`
- 세 가지 ingestion API
- query / document management API
- progress persistence / 조회

- composition-layer settings / `ServiceBundle` integration
- dms-core SDK / MinIO 기반 document asset lifecycle
- 명시적 host-owned client 기반 DMS/RAG 조립
- SQLite metadata persistence
- configured Milvus retrieval persistence

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
5. 선행 source/DMS/document 작업 이후 ingestion은 `load -> preprocess -> chunking -> embedding -> vector_store -> chunk_persistence` 순서의 progress를 남긴다.
6. embedding은 chunk 전체에 대해 batch 1회 호출로 처리된다.
7. query 결과는 반드시 현재 user scope의 chunk만 포함한다.
8. prompt에는 `[System Prompt]`, `[Retrieved Context]`, `[User Query]`가 포함된다.
9. metadata는 SQLite에 저장된다.
10. 동일한 vector store 구성을 다시 사용하면 재시작 후 retrieval이 가능하다.
11. 문서별 chunk 목록과 ingestion progress를 조회할 수 있다.
12. 삭제 성공 시 document / chunk / progress / Milvus 엔트리가 제거되고 DMS asset은 soft delete된다.
13. vector store 또는 DMS soft delete가 실패하면 metadata는 유지된다. DMS 실패 시 vector는 이미 삭제됐을 수 있다.
14. `DocmeshRAGServiceFactory.from_host_clients(...)`는 환경 설정을 읽지 않고 직접 전달된 DMS/metadata Engine, DMS, Ollama, Milvus clients와 명시적 model/store 설정으로 RAG adapters를 조립한다. Factory context는 dms-core v0.9 SDK와 host-owned clients를 닫지 않으며, compatibility `metadata_path`로 생성된 MetadataStore만 정리한다.
15. `ingest_text`의 DMS 업로드는 RAG `doc_id`, 사용자 metadata, ingestion `job_id` 기반 idempotency 정보를 보존한다. file-stream/file-path 업로드는 현재 idempotency key를 전달하지 않는다.

---

## 13. 요약

DocMesh RAG Core Service는 현재 **조립 가능한 Python RAG 라이브러리**로 구현되어 있다. 제품의 핵심 가치는 `RAGCore` 중심 API, user scope 격리, SQLite + configured Milvus adapter 기반 검색 persistence, dms-core 기반 source asset lifecycle, 세분화된 document management API, 그리고 caller-owned client를 명시적으로 조립하는 DocMesh integration 경로에 있다. 이 PRD는 현재 코드가 실제로 보장하는 범위를 기준으로 유지한다.
