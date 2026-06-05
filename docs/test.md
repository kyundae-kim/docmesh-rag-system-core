# DocMesh RAG Core Test Specification

## 1. 목적

이 문서는 `DocMesh RAG Core`의 현재 구현을 검증하기 위한 테스트 목적, 범위, 주요 시나리오를 정의한다.

핵심 목적은 다음과 같다.
- token 기반 사용자 격리가 유지되는지 검증
- 문서 적재 API가 명시적으로 분리되어 있는지 검증
- 문서/청크 persistence가 재시작 이후에도 유지되는지 검증
- ingestion progress persistence와 조회가 올바르게 동작하는지 검증
- 문서 관리 API(문서 조회, 청크 조회, 삭제)가 올바르게 동작하는지 검증
- retrieval/generation 흐름이 컨텍스트 기반으로 동작하는지 검증

---

## 2. 테스트 범위

### 2.1 포함 범위
- `RAGCore` public API 동작 검증
- `IngestionService`, `RetrievalService`, `GenerationService`의 통합 동작 검증
- SQLAlchemy ORM + SQLite persistence 검증
- 재시작 후 retrieval 복원 검증
- 문서 자산 저장(`memory`, `local`) 검증

### 2.2 제외 범위
- 실제 Ollama 연동 테스트
- 원격 Milvus 서버 연동 테스트
- 성능/부하 테스트
- 외부 API 서버 계약 테스트

---

## 3. 테스트 원칙

1. **행동 기반 검증**
   - 내부 구현 세부사항보다 public API의 동작 결과를 우선 검증한다.
2. **실제 persistence 검증**
   - SQLite 파일 및 SQLAlchemy ORM 테이블 생성/조회까지 확인한다.
3. **사용자 격리 우선 검증**
   - token 간 데이터 혼합이 없는지 반드시 확인한다.
4. **재시작 시나리오 포함**
   - 단순 저장 성공뿐 아니라 재초기화 후 retrieval 복원까지 검증한다.
5. **문서 생명주기 검증**
   - ingest → query → chunk listing → delete 흐름을 검증한다.

---

## 4. 테스트 대상 API

- `ingest_text(...)`
- `ingest_file_stream(...)`
- `ingest_file_path(...)`
- `query(...)`
- `list_documents(...)`
- `get_document(...)`
- `list_document_chunks(...)`
- `list_ingestion_progress(...)`
- `delete_document(...)`

---

## 5. 핵심 테스트 시나리오

### 5.1 사용자 스코프
- token이 있으면 해당 token 문자열이 user scope로 사용되어야 한다.
- token이 없으면 `single-user`로 동작해야 한다.
- 공백 token도 `single-user`로 fallback 되어야 한다.
- 서로 다른 token 간 query 결과가 섞이면 안 된다.
- `get_document(...)`는 현재 token scope에 속한 문서만 반환해야 한다.

### 5.2 문서 적재
- 텍스트 적재가 성공해야 한다.
- 파일 스트림 적재가 성공해야 한다.
- 파일 경로 적재가 성공해야 한다.
- 파일 스트림 적재는 `source`가 없을 때 실패해야 한다.
- chunk 생성 및 embedding batch 호출이 이루어져야 한다.

### 5.3 문서 자산 저장
- `local` 모드에서 문서 파일이 실제로 저장되어야 한다.
- `memory` 모드에서 `memory://...` 경로가 기록되어야 한다.
- 메타데이터는 문서 본문 대신 `storage_path`를 보관해야 한다.

### 5.4 SQLAlchemy ORM persistence
- `documents` 테이블이 생성되어야 한다.
- `chunks` 테이블이 생성되어야 한다.
- `DocumentModel`, `ChunkModel`이 노출되어야 한다.
- 문서 row와 chunk row가 기대한 값으로 저장되어야 한다.

### 5.5 재시작 복원
- 재초기화 후에도 문서 메타데이터가 조회되어야 한다.
- 재초기화 후에도 Milvus Lite가 관리하는 embedding을 통해 query가 가능해야 한다.

### 5.6 ingestion progress
- 문서 적재 후 파이프라인 단계별 progress row가 저장되어야 한다.
- progress row는 `load -> preprocess -> chunking -> embedding -> vector_store -> chunk_persistence` 순서를 유지해야 한다.
- progress row는 ingestion 실행 단위를 구분하는 `job_id`를 포함해야 한다.
- progress 상태는 최소 `running`, `completed`, `failed`를 표현해야 한다.
- progress 조회도 현재 token scope로 제한되어야 한다.

### 5.7 문서 단위 관리
- 특정 `doc_id`의 chunk만 조회할 수 있어야 한다.
- 문서 삭제 시 다음이 함께 정리되어야 한다.
  - document metadata
  - chunk metadata
  - ingestion progress metadata
  - stored asset
  - Milvus Lite vector store entry
- 삭제된 문서의 chunk는 query 결과에 포함되지 않아야 한다.

### 5.8 프롬프트 생성
- 생성 프롬프트에 아래 섹션이 포함되어야 한다.
  - `[System Prompt]`
  - `[Retrieved Context]`
  - `[User Query]`

---

## 6. 현재 테스트 파일 매핑

현재 구현 기준 주요 테스트는 아래 파일에 위치한다.

- `test_rag_system_core/test_rag_core.py`

대표 테스트 예시:
- `test_ingest_text_uses_token_as_user_scope`
- `test_ingest_text_without_token_uses_single_user_scope`
- `test_ingest_file_stream_requires_explicit_source`
- `test_query_filters_results_by_token_derived_user_id`
- `test_metadata_store_uses_sqlalchemy_orm_models_and_chunk_table`
- `test_ingest_text_persists_milvus_generated_chunk_ids_to_metadata`
- `test_ingestion_progress_rows_are_persisted_in_pipeline_order`
- `test_ingestion_progress_records_running_and_completed_statuses_per_job`
- `test_ingestion_progress_records_failed_step_when_ingest_errors`
- `test_ingestion_progress_can_be_grouped_by_job_id_for_same_document`
- `test_ingestion_progress_is_limited_to_current_token_scope`
- `test_chunk_rows_are_persisted_and_rehydrated_across_restarts`
- `test_list_document_chunks_returns_only_requested_document_chunks`
- `test_get_document_is_limited_to_current_token_scope`
- `test_delete_document_removes_metadata_chunks_asset_and_query_visibility`

---

## 7. 권장 실행 방법

프로젝트 의존성 기준으로 다음 명령을 사용한다.

```bash
uv run pytest -q
```

특정 시나리오만 검증할 때 예시:

```bash
uv run pytest test_rag_system_core/test_rag_core.py::test_list_document_chunks_returns_only_requested_document_chunks -q
uv run pytest test_rag_system_core/test_rag_core.py::test_delete_document_removes_metadata_chunks_asset_and_query_visibility -q
```

---

## 8. 향후 추가 권장 테스트

- 잘못된 token으로 다른 사용자의 문서 삭제 시 실패 검증
- 삭제 후 재시작 시 복원 무결성 검증
- `memory` 모드 삭제 동작 검증
- 대량 chunk 입력 시 batch embedding 호출 수/크기 검증
- 향후 외부 vector DB 교체 시 adapter contract test 추가
