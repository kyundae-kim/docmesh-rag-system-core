# DocMesh RAG Core Service PRD

## 1. 문서 개요

- **문서명:** Product Requirements Document (PRD)
- **대상 제품:** DocMesh RAG Core Service
- **문서 목적:** DocMesh RAG 코어의 요구사항과 현재 MVP 구현 기준을 명확히 정의한다.
- **문서 상태:** Updated for current implementation

---

## 2. 제품 배경

DocMesh 프로젝트는 문서를 적재하고, 관련 컨텍스트를 검색한 뒤, LLM으로 답변을 생성하는 RAG(Retrieval-Augmented Generation) 코어가 필요하다.

초기 단계에서는 **단일 클래스 진입점(`RAGCore`)** 으로 빠르게 개발하되, 내부는 ingestion / retrieval / generation 책임으로 분리하여 이후 API 서버, 비동기 처리, 서비스 분리로 확장할 수 있어야 한다.

또한 멀티 유저 환경을 고려하여, 각 사용자의 문서/청크/검색 결과가 서로 섞이지 않도록 **token 기반 사용자 스코프 격리**를 보장해야 한다.

---

## 3. 제품 목표

### 3.1 핵심 목표

1. 개인 및 멀티 유저를 지원하는 RAG 코어를 제공한다.
2. 텍스트 및 파일 기반 문서 적재를 지원한다.
3. 문서 적재, 청킹, 임베딩, 검색, 답변 생성의 일관된 흐름을 제공한다.
4. 최소한의 persistence를 제공하여 재시작 이후에도 메타데이터와 검색 복구가 가능해야 한다.
5. 단일 클래스 인터페이스를 유지하되 내부 책임 분리가 가능해야 한다.

### 3.2 성공 기준

- 사용자는 텍스트, 파일 스트림, 파일 경로로 문서를 적재할 수 있다.
- 사용자는 자신의 token 스코프에 속한 문서만 검색할 수 있다.
- 시스템은 문서와 청크 메타데이터를 영속화할 수 있다.
- 시스템은 재시작 후 저장된 청크/임베딩과 동일한 Milvus Lite 컬렉션을 기반으로 retrieval을 복원할 수 있다.
- 문서 삭제 시 메타데이터, 청크, 문서 자산, Milvus Lite 검색 엔트리가 함께 정리된다.

---

## 4. 범위 정의

### 4.1 포함 범위 (In Scope)

- Knowledge ingestion
- 문서 전처리 및 고정 길이 청킹
- 배치 임베딩 호출 구조
- lightweight Milvus Lite vector store 기반 검색
- LLM 기반 답변 생성
- token 기반 사용자 식별
- user_id 기반 멀티 유저 데이터 격리
- SQLAlchemy ORM + SQLite 기반 문서/청크 메타데이터 persistence
- 문서 자산 저장 (`memory`, `local`)
- 문서별 청크 조회
- ingestion 파이프라인 진행 상태 기록/조회
- 문서 삭제 및 연관 데이터 정리

### 4.2 제외 범위 (Out of Scope)

초기 MVP에서는 아래 항목을 제외한다.

- 외부 공개용 API 서버
- UI / Frontend
- 대규모 분산 아키텍처(MSA) 운영 환경
- 고급 캐싱
- 고급 reranking
- 복잡한 권한 체계 및 조직 단위 멀티테넌시
- production-grade distributed vector database 운영

---

## 5. 주요 사용자 및 사용 시나리오

### 5.1 주요 사용자

1. **개인 사용자**
   - 자신의 문서를 적재하고 질의응답을 수행하려는 사용자
2. **멀티 유저 환경의 상위 애플리케이션**
   - 여러 사용자의 문서를 분리 저장하고 사용자별 응답을 제공하려는 시스템

### 5.2 핵심 사용 시나리오

#### 시나리오 1: 문서 적재
- 사용자는 문자열, 파일 스트림, 파일 경로 형태로 문서를 입력한다.
- 시스템은 전처리, 청킹, 임베딩을 수행한다.
- 시스템은 문서 자산과 문서/청크 메타데이터를 기록한다.
- 시스템은 벡터 검색용 Milvus Lite 저장소에 청크를 적재한다.

#### 시나리오 2: 사용자별 질의응답
- 사용자는 `token`으로 식별된다.
- 시스템은 `token`을 현재 구현상 `user_id` 스코프로 사용한다.
- 시스템은 해당 사용자 스코프의 청크만 검색한다.
- 시스템은 검색된 컨텍스트를 기반으로 프롬프트를 구성하고 답변을 생성한다.

#### 시나리오 3: 재시작 이후 검색 복원
- 프로세스 재시작 이후에도 문서 및 청크 메타데이터는 유지되어야 한다.
- 시스템은 저장된 청크/임베딩 및 동일한 Milvus Lite 컬렉션을 다시 사용해 retrieval을 복원할 수 있어야 한다.

#### 시나리오 4: 문서 단위 관리
- 사용자는 특정 문서의 청크 목록을 조회할 수 있어야 한다.
- 사용자는 특정 문서를 삭제할 수 있어야 하며, 관련 청크와 문서 자산도 함께 제거되어야 한다.

---

## 6. 제품 요구사항

### 6.1 사용자 관리 요구사항

#### PRD-FR-1. 사용자 식별
- 시스템은 token 기반으로 사용자를 식별해야 한다.
- 현재 MVP에서는 **token 문자열 자체를 user scope로 사용**한다.
- token이 없거나 공백이면 `single-user` 스코프를 사용한다.

#### PRD-FR-2. 멀티 유저 지원
- 시스템은 사용자별 데이터 격리를 지원해야 한다.
- 모든 문서 메타데이터와 청크 메타데이터에는 `user_id`가 포함되어야 한다.
- 검색 시 `user_id` 기반 필터링이 반드시 적용되어야 한다.

### 6.2 문서 관리 요구사항

#### PRD-FR-3. 문서 입력
- 시스템은 텍스트 기반 문서 입력을 지원해야 한다.
- MVP 기준 입력 방식은 다음 세 가지다.
  - `ingest_text(...)`
  - `ingest_file_stream(...)`
  - `ingest_file_path(...)`

#### PRD-FR-4. 문서 저장
- 시스템은 문서를 처리 과정에서 사용할 저장 방식을 선택 가능해야 한다.
- MVP 지원 옵션:
  - `memory`
  - `local`
- 문서 본문은 메타데이터에 직접 저장하지 않고, `storage_path` 기반 자산 관리 방식을 사용한다.

#### PRD-FR-5. 문서 메타데이터 관리
- 시스템은 문서별 메타데이터를 저장해야 한다.
- 최소 메타데이터 스키마는 아래 정보를 포함해야 한다.

```json
{
  "doc_id": "uuid",
  "user_id": "string",
  "source": "file_name",
  "created_at": "timestamp",
  "storage_path": "string | null"
}
```

#### PRD-FR-6. 문서 관리 API
- 시스템은 문서 목록 조회를 지원해야 한다.
- 시스템은 문서 단위 청크 조회를 지원해야 한다.
- 시스템은 문서 조회 시 현재 user scope 기준 접근 제어를 적용해야 한다.
- 시스템은 문서 삭제를 지원해야 한다.
- 문서 삭제 시 문서 메타데이터, 청크 메타데이터, 저장 자산, 메모리 내 검색 엔트리를 함께 정리해야 한다.

### 6.3 Knowledge Ingestion 요구사항

#### PRD-FR-7. 문서 처리 파이프라인
시스템은 아래 순서의 문서 처리 파이프라인을 제공해야 한다.

1. Load
2. Preprocess
3. Chunking
4. Embedding
5. Chunk persistence
6. Vector Store 저장

시스템은 각 문서에 대해 위 단계의 진행 상태를 조회할 수 있도록 ingestion progress 데이터를 저장해야 한다.
각 진행 상태 row는 ingestion 실행 단위를 구분하는 `job_id`를 포함해야 한다.
각 단계는 최소 `running`, `completed`, `failed` 상태를 표현할 수 있어야 한다.

#### PRD-FR-8. Chunking
- 시스템은 문서를 청크 단위로 분할할 수 있어야 한다.
- MVP 최소 지원 방식:
  - 고정 길이 청킹
- 확장 가능성:
  - semantic chunking으로 교체/확장 가능한 구조
- 청크 간 overlap 설정을 지원해야 한다.

### 6.4 Embedding 요구사항

#### PRD-FR-9. 임베딩 생성
- 시스템은 embedding client를 통해 임베딩을 생성해야 한다.
- 성능 최적화를 위해 batch 처리를 지원해야 한다.

#### PRD-FR-10. 임베딩 서비스 분리
- 시스템은 embedding 처리와 generation 처리를 논리적으로 분리해야 한다.
- embedding client는 generation client와 별도로 주입 가능해야 한다.

### 6.5 Vector Storage 요구사항

#### PRD-FR-11. 벡터 저장소
- MVP는 Milvus Lite 기반 로컬 persistent vector store를 사용한다.
- 향후 Milvus 서버/외부 vector DB로 교체 가능한 구조여야 한다.

#### PRD-FR-12. 멀티테넌트 구조
- 현재 구현은 청크 메타데이터와 검색 시 `user_id` 필터로 사용자 격리를 유지한다.
- 향후 collection per user, partition per user 등의 구조로 확장 가능해야 한다.

### 6.6 Retrieval 요구사항

#### PRD-FR-13. 유사도 검색
- 시스템은 질의에 대한 embedding을 생성해야 한다.
- 시스템은 top-k 기반 유사도 검색을 수행해야 한다.

#### PRD-FR-14. 사용자 필터링
- 검색 결과는 반드시 해당 `user_id` 범위로 제한되어야 한다.
- 다른 사용자 데이터가 검색 결과에 포함되어서는 안 된다.

### 6.7 Generation 요구사항

#### PRD-FR-15. 프롬프트 생성
시스템은 아래 요소를 조합해 프롬프트를 구성해야 한다.

```text
[System Prompt]
[Retrieved Context]
[User Query]
```

#### PRD-FR-16. 답변 생성
- 시스템은 generation client를 통해 응답을 생성해야 한다.
- 응답은 검색된 컨텍스트를 기반으로 생성되어야 한다.

### 6.8 Persistence 요구사항

#### PRD-FR-17. 문서/청크 영속화
- 시스템은 SQLAlchemy ORM + SQLite를 통해 문서 및 청크 메타데이터를 저장해야 한다.
- 청크 row에는 검색 복원에 필요한 embedding 정보가 포함되어야 한다.

#### PRD-FR-18. 재시작 복원
- 시스템은 재시작 시 저장된 청크와 embedding을 다시 로드하여 retrieval 가능 상태를 복원해야 한다.

---

## 7. 비기능 요구사항

### 7.1 성능
- embedding은 batch 처리로 최적화되어야 한다.
- retrieval latency는 가능한 낮게 유지되어야 한다.
- 문서 삭제는 문서 단위 정리 작업을 일관되게 수행해야 한다.

### 7.2 확장성
- 초기 구현은 단일 클래스 구조로 시작하되, 서비스 단위 분리가 가능해야 한다.
- 향후 FastAPI 기반 API 서버 또는 MSA로 확장 가능한 구조여야 한다.

### 7.3 데이터 격리
- 사용자 데이터는 절대 혼합되어서는 안 된다.
- 저장, 검색, 문서 조회, 문서 삭제 전 과정에서 `user_id` 스코프가 일관되게 유지되어야 한다.

### 7.4 안정성
- 최소한의 persistence를 보장해야 한다.
- 프로세스 재시작 이후에도 문서 및 청크 메타데이터는 유지되어야 한다.
- 재시작 이후 retrieval 복원이 가능해야 한다.

### 7.5 유지보수성
- ingestion, retrieval, generation 책임은 구조적으로 분리되어야 한다.
- 메타데이터 계층은 SQLAlchemy 기반으로 관리되어야 한다.
- 향후 독립 서비스로 분리 가능한 수준의 모듈화가 필요하다.

---

## 8. 시스템 아키텍처 개요

```text
[RAGCore]
 ├ IngestionService
 ├ RetrievalService
 └ GenerationService

[Storage]
 ├ Milvus Lite Vector Store
 ├ MetadataStore (SQLAlchemy ORM + SQLite)
 └ DocumentStorage (memory | local)

[Model Clients]
 ├ EmbeddingClient
 └ GenerationClient
```

### 8.1 설계 원칙
- 외부 인터페이스는 단순하게 유지한다.
- 내부 구현은 ingestion / retrieval / generation 책임별로 분리한다.
- 문서 자산 저장과 메타데이터 저장을 분리한다.
- persistence 계층과 검색 계층은 분리하되 재시작 시 재구성 가능해야 한다.

### 8.2 현재 코어 인터페이스

```python
class RAGCore:
    def ingest_text(self, *, text: str, source: str, token: str | None = None) -> IngestResult: ...
    def ingest_file_stream(self, *, file_stream, source: str | None = None, token: str | None = None) -> IngestResult: ...
    def ingest_file_path(self, *, file_path, token: str | None = None, source: str | None = None) -> IngestResult: ...
    def query(self, *, question: str, top_k: int = 3, token: str | None = None) -> QueryResult: ...
    def list_documents(self, token: str | None = None) -> list[DocumentRecord]: ...
    def get_document(self, doc_id: str, *, token: str | None = None) -> DocumentRecord | None: ...
    def list_document_chunks(self, doc_id: str, *, token: str | None = None) -> list[ChunkRecord]: ...
    def list_ingestion_progress(self, doc_id: str, *, token: str | None = None, job_id: str | None = None) -> list[IngestionProgressRecord]: ...
    def delete_document(self, doc_id: str, *, token: str | None = None) -> bool: ...
```

---

## 9. 세부 서비스 책임

### 9.1 IngestionService
책임:
- 문서 로드
- 전처리
- 청킹
- 임베딩 생성
- 문서 메타데이터 기록
- 청크 및 embedding 저장
- vector store 적재

핵심 메서드:
- `ingest_text()`
- `ingest_file_stream()`
- `ingest_file_path()`
- `preprocess()`
- `chunk()`
- `embed()`
- `store()`

### 9.2 RetrievalService
책임:
- 질의 임베딩 생성
- 벡터 검색 수행
- 사용자 스코프 검색 보장

핵심 메서드:
- `embed_query()`
- `vector_search()`
- `search()`

### 9.3 GenerationService
책임:
- 프롬프트 구성
- 컨텍스트 기반 답변 생성

핵심 메서드:
- `build_prompt()`
- `call_llm()`
- `generate()`

### 9.4 MetadataStore
책임:
- SQLAlchemy ORM 기반 문서/청크 저장
- ingestion progress 저장
- 문서 조회 / 목록 조회
- 문서별 청크 조회
- 문서별 ingestion progress 조회
- 문서 삭제
- 재시작 복원용 chunk 메타데이터 관리

---

## 10. 데이터 모델 요구사항

### 10.1 documents

필수 필드:

```text
doc_id (PK)
user_id
source
created_at
storage_path
```

### 10.2 chunks

필수 필드:

```text
chunk_id (PK, Milvus generated id mirrored into metadata store)
doc_id (FK -> documents.doc_id)
user_id
chunk_index
content
metadata_json
```

### 10.3 ingestion_progress

필수 필드:

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

### 10.4 public records

외부 반환 모델:

```text
DocumentRecord
doc_id
user_id
source
created_at
storage_path

ChunkRecord
chunk_id
doc_id
user_id
content
metadata
```

---

## 11. 제약사항 및 리스크

### R1. 모델 리소스 경쟁
- embedding과 generation이 동일 자원을 과도하게 점유할 수 있다.
- 대응: client 분리, batch 처리, 호출 계층 분리

### R2. 멀티 유저 데이터 혼합
- 사용자 필터링 누락 시 심각한 데이터 혼합 문제가 발생할 수 있다.
- 대응: 문서/청크 저장과 검색 모두 `user_id` 기준 강제

### R3. memory 저장의 휘발성
- `memory` 문서 저장은 재시작 시 자산이 유지되지 않는다.
- 대응: 메타데이터 및 청크 persistence는 SQLite에 유지

### R4. Milvus Lite 운영 한계
- 현재 검색 저장소는 단일 파일 기반 Milvus Lite이므로 대규모 운영에 부적합하다.
- 대응: 향후 외부 vector DB로 교체 가능한 구조 유지

### R5. 단일 클래스 구조의 확장 한계
- 초기 구현이 지나치게 결합되면 이후 분리가 어려워질 수 있다.
- 대응: 서비스 책임 분리 및 명시적 API 유지

---

## 12. 릴리스 범위 정의

### 12.1 현재 MVP 범위
- 단일 클래스 기반 `RAGCore` 제공
- 텍스트 / 파일 스트림 / 파일 경로 적재
- 기본 전처리 및 고정 길이 청킹
- 배치 임베딩 호출 구조
- Milvus Lite vector search
- 사용자별 질의응답
- SQLAlchemy ORM + SQLite 기반 문서/청크 메타데이터 저장
- 재시작 시 retrieval 복원
- 문서별 청크 조회
- ingestion progress 조회
- 문서 삭제 및 연관 데이터 정리

### 12.2 이후 확장 로드맵

#### Phase 1
- 현재 단일 클래스 기반 RAG MVP 안정화

#### Phase 2
- FastAPI 기반 API 서비스 제공
- Async 처리 도입
- 외부 vector DB 연동

#### Phase 3
- MSA 전환
  - ingestion-service
  - retrieval-service
  - generation-service

#### Phase 4
- multi-tenant scaling
- caching
- reranking
- advanced auth/authorization

---

## 13. 수용 기준 (Acceptance Criteria)

1. 사용자 token을 통해 user scope를 식별할 수 있다.
2. token이 없거나 공백이면 `single-user` 스코프로 동작한다.
3. 문서를 문자열, 파일 스트림, 파일 경로 형태로 적재할 수 있다.
4. 적재된 문서는 청킹 및 임베딩 과정을 거쳐 vector store와 chunk persistence에 반영된다.
5. 시스템은 문서별 ingestion 파이프라인 진행 상태를 조회할 수 있다.
6. ingestion progress row는 `job_id`를 포함하고, 단계 상태로 `running`, `completed`, `failed`를 기록할 수 있다.
7. 문서 메타데이터에는 `doc_id`, `user_id`, `source`, `created_at`, `storage_path`가 포함된다.
8. 청크 메타데이터에는 `chunk_id`, `doc_id`, `user_id`, `content`, `metadata`, `embedding` 정보가 저장된다.
9. 질의 시 query embedding을 생성하고 top-k 검색을 수행할 수 있다.
10. 검색 결과는 반드시 해당 user scope로 제한된다.
11. 시스템은 검색된 컨텍스트를 포함한 프롬프트로 응답을 생성할 수 있다.
12. 프로세스 재시작 이후에도 문서/청크 메타데이터가 유지된다.
13. 프로세스 재시작 이후에도 저장된 청크/임베딩을 통해 retrieval이 복원된다.
14. 사용자는 특정 문서의 chunk 목록을 조회할 수 있다.
15. 사용자는 특정 문서의 ingestion progress를 조회할 수 있다.
16. 사용자는 특정 문서를 삭제할 수 있으며, 삭제 시 메타데이터/청크/문서 자산/메모리 인덱스가 함께 정리된다.
17. 내부 구조는 ingestion / retrieval / generation / metadata 책임으로 분리되어 향후 서비스화가 가능하다.

---

## 14. 요약

DocMesh RAG Core Service는 문서 적재, 검색, 생성의 전 과정을 담당하는 RAG 핵심 모듈이다. 현재 MVP는 `RAGCore` 단일 진입점을 유지하면서도 내부 책임을 분리하고, token 기반 사용자 격리, SQLAlchemy ORM + SQLite 기반 persistence, 재시작 이후 retrieval 복원, 문서 단위 관리 기능을 제공하는 방향으로 구현되어 있다.
