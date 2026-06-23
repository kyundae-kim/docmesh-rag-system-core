# DocMesh RAG Core Test Specification

## 1. 목적

이 문서는 `DocMesh RAG Core`의 **현재 구현**을 검증하기 위한 테스트 목적, 범위, 실행 기준, 그리고 `docs/srs.md` 요구사항 ID 기준의 추적 관계를 정의한다.

핵심 목적:
- `docs/srs.md`의 기능/비기능/데이터 요구사항이 실제 테스트로 추적 가능한지 명시한다.
- user scope, ingestion, retrieval, persistence, document deletion, health check, DocMesh integration의 현재 검증 범위를 정리한다.
- 현재 저장소의 테스트 파일 및 대표 테스트 케이스를 요구사항 ID와 연결한다.
- 이미 자동화된 검증 범위와 아직 보강이 필요한 검증 범위를 분리한다.

### 1.1 용어 기준

본 문서는 `docs/prd.md`, `docs/srs.md`와 동일한 용어 기준을 사용한다.

- **user scope**: 현재 요청에 대해 해석된 사용자 경계
- **resolved user identity**: token 또는 Keycloak 검증으로부터 해석된 사용자 식별 결과
- **`user_id`**: persistence 및 filtering에 사용되는 저장된 사용자 식별자
- **metadata store**: SQLite + SQLAlchemy 기반 document / chunk / ingestion progress persistence 계층
- **vector store**: Milvus Lite 기반 embedding 저장 및 retrieval 계층
- **document asset storage**: 문서 원문 자산을 `storage_path`로 추적하는 저장 계층
- **restart recovery**: 동일한 metadata store 및 vector store 구성을 다시 열어 상태를 재사용하는 동작
- **health check**: metadata 및 사용 가능한 의존 서비스 상태를 집계하는 점검 동작

---

## 2. 테스트 범위

### 2.1 포함 범위
- `RAGCore` public API 동작
- `IngestionService`, `RetrievalService`, `GenerationService` 통합 동작
- SQLAlchemy ORM + SQLite metadata store persistence
- restart recovery
- document asset storage (`memory`, `local`)
- document deletion 및 rollback 특성
- composition 계층 동작
- Keycloak 모드 resolved user identity 해석
- Ollama adapter의 정상/오류/health-check 동작
- `docs/srs.md` 요구사항 ID 기준 추적성 검증

### 2.2 제외 범위
- 실제 외부 Ollama 서버와의 네트워크 통신
- 원격 Milvus 서버 통합 테스트
- 성능/부하/내구성 테스트
- HTTP API 서버 계약 테스트
- PDF/이미지/복합 문서 파싱 테스트

---

## 3. 테스트 원칙

1. **Public API 우선 검증**
   - 구현 세부사항보다 외부에서 보이는 계약을 우선 검증한다.
2. **요구사항 ID 추적성 유지**
   - 모든 핵심 테스트 시나리오는 가능하면 하나 이상의 `SRS-FR-*`, `SRS-NFR-*`, `SRS-DR-*`에 매핑한다.
3. **실제 persistence 검증**
   - SQLite 파일, ORM 테이블, 재초기화 후 조회/검색까지 확인한다.
4. **사용자 격리 우선**
   - token 또는 Keycloak 기반 user scope 간 데이터 혼합이 없어야 한다.
5. **restart recovery 포함**
   - 저장 성공뿐 아니라 재초기화 후 restart recovery까지 확인한다.
6. **실패 경로 포함**
   - malformed adapter response, Milvus chunk id mismatch, chunk persistence 실패, delete 실패 등 오류 경로를 검증한다.
7. **문서-테스트 정렬 유지**
   - 테스트 문서는 현재 테스트 파일 배치와 실제 검증 시나리오를 반영해야 한다.

---

## 4. 테스트 대상 인터페이스

### 4.1 `RAGCore`
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

### 4.2 Composition / helper
- `bootstrap_rag_core(...)`
- `DocmeshRAGServiceFactory`
- `create_rag_embedding_client(...)`
- `create_rag_generation_client(...)`
- `create_rag_vector_store(...)`
- `create_rag_metadata_store(...)`
- `create_rag_document_storage(...)`
- `create_rag_chunker(...)`
- `resolve_user_id(...)`

### 4.3 Adapter / protocol boundary
- `OllamaEmbeddingClient`
- `OllamaGenerationClient`
- `EmbeddingClient`
- `GenerationClient`

---

## 5. 현재 테스트 파일 매핑

현재 테스트는 기능별로 분리되어 있다.

### 5.1 Domain API / 동작
- `test_rag_system_core/domain/test_ingestion_api.py`
- `test_rag_system_core/domain/test_query.py`
- `test_rag_system_core/domain/test_metadata_and_progress.py`
- `test_rag_system_core/domain/test_deletion_and_rollback.py`

### 5.2 Composition / integration
- `test_rag_system_core/composition/test_bootstrap.py`
- `test_rag_system_core/composition/test_docmesh_integration.py`
- `test_rag_system_core/composition/test_core_configuration.py`
- `test_rag_system_core/composition/test_auth_runtime.py`

### 5.3 Adapter
- `test_rag_system_core/adapters/test_ollama_embedding_client.py`
- `test_rag_system_core/adapters/test_ollama_generation_client.py`

### 5.4 보조 파일
- `test_rag_system_core/conftest.py`
- `test_rag_system_core/support.py`

---

## 6. 요구사항 추적형 테스트 매트릭스

아래 표는 `docs/srs.md`의 요구사항 ID와 현재 테스트 범위를 연결한다.

### 6.1 기능 요구사항 (`SRS-FR-*`)

| SRS ID | 요구사항 요약 | 검증 상태 | 관련 테스트 파일 | 대표 테스트 |
|---|---|---|---|---|
| SRS-FR-001 ~ 003 | 기본 token 기반 user scope 및 `single-user` fallback | 검증됨 | `domain/test_ingestion_api.py`, `composition/test_auth_runtime.py` | `test_ingest_text_uses_token_as_user_scope`, `test_ingest_text_without_token_uses_single_user_scope`, `test_blank_token_falls_back_to_single_user_scope`, `test_resolve_user_id_defaults_to_single_user` |
| SRS-FR-004 ~ 007 | Keycloak 기반 resolved user identity 해석 | 검증됨 | `composition/test_docmesh_integration.py` | `test_resolve_user_id_uses_keycloak_when_auth_mode_enabled` |
| SRS-FR-008 ~ 011 | `user_id` 부착 및 user scope 기반 조회/검색/삭제 제한 | 검증됨 | `domain/test_query.py`, `domain/test_metadata_and_progress.py`, `domain/test_deletion_and_rollback.py` | `test_query_filters_results_by_token_derived_user_id`, `test_get_document_is_limited_to_current_token_scope` |
| SRS-FR-012 ~ 023 | ingestion API, pipeline order, progress status | 검증됨 | `domain/test_ingestion_api.py`, `domain/test_metadata_and_progress.py` | `test_ingest_file_stream_requires_explicit_source`, `test_ingestion_progress_rows_are_persisted_in_pipeline_order`, `test_ingestion_progress_records_failed_step_when_ingest_errors` |
| SRS-FR-024 ~ 029 | document asset storage (`memory`, `local`, `storage_path`) | 검증됨 | `domain/test_ingestion_api.py`, `domain/test_deletion_and_rollback.py` | `test_ingest_text_stores_string_input_as_managed_asset`, `test_ingest_text_memory_storage_uses_logical_asset_path`, `test_ingest_file_stream_copies_input_stream_into_managed_storage` |
| SRS-FR-030 ~ 037 | embedding batch 호출, generation 호출 계약, prompt 구조 | 검증됨 | `domain/test_query.py`, `domain/test_deletion_and_rollback.py`, `adapters/test_ollama_embedding_client.py`, `adapters/test_ollama_generation_client.py` | `test_embedding_requests_are_batched_for_chunk_ingestion`, `test_query_prompt_includes_system_query_and_context` |
| SRS-FR-038 ~ 044 | Milvus Lite 기본 vector store 및 fallback 설정 해석 | 검증됨 | `composition/test_core_configuration.py`, `composition/test_docmesh_integration.py` | `test_rag_core_uses_milvus_fallback_settings_when_docmesh_settings_are_unavailable`, `test_rag_core_reads_milvus_configuration_from_environment` |
| SRS-FR-045 ~ 052 | metadata store, ORM, restart recovery | 검증됨 | `domain/test_metadata_and_progress.py` | `test_metadata_store_uses_sqlalchemy_orm_models_and_chunk_table`, `test_chunk_rows_are_persisted_and_rehydrated_across_restarts`, `test_metadata_persists_across_restarts` |
| SRS-FR-053 ~ 063 | document management, document deletion, rollback/retry | 검증됨 | `domain/test_deletion_and_rollback.py`, `domain/test_metadata_and_progress.py` | `test_delete_document_removes_metadata_chunks_asset_and_query_visibility`, `test_delete_document_leaves_metadata_intact_when_milvus_delete_fails_and_allows_retry` |
| SRS-FR-064 ~ 072 | health check 및 composition / DocMesh integration | 검증됨 | `composition/test_bootstrap.py`, `composition/test_docmesh_integration.py`, `composition/test_core_configuration.py` | `test_bootstrap_rag_core_builds_core_from_service_factory`, `test_package_root_exports_bootstrap_helper`, `test_rag_core_health_check_uses_docmesh_aggregate_when_available`, `test_ollama_factories_use_docmesh_service_factory_when_available` |

### 6.2 비기능 요구사항 (`SRS-NFR-*`)

| SRS ID | 요구사항 요약 | 검증 상태 | 관련 테스트 파일 | 비고 |
|---|---|---|---|---|
| SRS-NFR-001 | ingestion batch embedding | 검증됨 | `domain/test_deletion_and_rollback.py` | `test_embedding_requests_are_batched_for_chunk_ingestion` |
| SRS-NFR-002 | 단순하고 예측 가능한 top-k retrieval 흐름 | 부분 검증 | `domain/test_query.py` | 동작은 검증되나 정량 성능 기준은 없음 |
| SRS-NFR-003 | health check의 빠른 실패 감지 가능성 | 부분 검증 | `composition/test_docmesh_integration.py` | aggregate/fallback 경로는 검증되나 시간 기준은 없음 |
| SRS-NFR-004 ~ 005 | 단일 public entry point 유지 및 확장 가능한 내부 분리 | 부분 검증 | `domain/*`, `composition/*` | 구조적 성격이 강해 테스트보다 코드 구조/문서 정렬로 보강 |
| SRS-NFR-006 ~ 007 | cross-user mixing 방지 및 전 과정 user scope 유지 | 검증됨 | `domain/test_query.py`, `domain/test_ingestion_api.py`, `domain/test_deletion_and_rollback.py` | user scope 시나리오로 검증 |
| SRS-NFR-008 ~ 010 | restart survival 및 부분 삭제 손실 최소화 | 검증됨 | `domain/test_metadata_and_progress.py`, `domain/test_deletion_and_rollback.py` | restart recovery 및 delete failure retry 시나리오로 검증 |
| SRS-NFR-011 ~ 013 | `RAGCore` 중심 API, explicit types/protocols, 분리된 통합 구조 | 부분 검증 | `domain/*`, `adapters/*`, `composition/*` | interface/adapter/composition 경계는 간접 검증 |
| SRS-NFR-014 | Python 3.11+ 및 선언된 의존성 환경 | 미검증(문서/환경 전제) | 해당 없음 | 설치/CI 환경 검증으로 별도 관리 필요 |

### 6.3 데이터 요구사항 (`SRS-DR-*`)

| SRS ID | 요구사항 요약 | 검증 상태 | 관련 테스트 파일 | 대표 테스트 |
|---|---|---|---|---|
| SRS-DR-001 | unique `doc_id` 기반 document record | 검증됨 | `domain/test_metadata_and_progress.py`, `domain/test_ingestion_api.py` | ingestion 결과 및 metadata persistence 시나리오로 검증 |
| SRS-DR-002 | chunk의 document / `user_id` 연계 | 검증됨 | `domain/test_metadata_and_progress.py`, `domain/test_query.py` | persisted/rehydrated chunk 검증 |
| SRS-DR-003 | progress record traceability (`job_id`, `doc_id`, `user_id`, `step_name`, `status`) | 검증됨 | `domain/test_metadata_and_progress.py` | `test_ingestion_progress_rows_are_persisted_in_pipeline_order`, `test_ingestion_progress_records_failed_step_when_ingest_errors` |
| SRS-DR-004 | `metadata_json` persistence | 검증됨 | `domain/test_metadata_and_progress.py` | `test_metadata_store_uses_sqlalchemy_orm_models_and_chunk_table` |
| SRS-DR-005 | SQLite-backed metadata persistence across restart | 검증됨 | `domain/test_metadata_and_progress.py` | `test_metadata_persists_across_restarts` |
| SRS-DR-006 | `memory` storage mode 비영속성 | 부분 검증 | `domain/test_ingestion_api.py`, `domain/test_deletion_and_rollback.py` | memory storage path / delete 동작은 검증되나 restart 기준 명시 테스트는 추가 여지 있음 |

---

## 7. 대표 테스트 시나리오

### 7.1 User scope / resolved user identity
- `test_ingest_text_uses_token_as_user_scope`
- `test_ingest_text_without_token_uses_single_user_scope`
- `test_blank_token_falls_back_to_single_user_scope`
- `test_query_filters_results_by_token_derived_user_id`
- `test_resolve_user_id_uses_keycloak_when_auth_mode_enabled`

### 7.2 Ingestion / progress
- `test_ingest_file_stream_requires_explicit_source`
- `test_ragcore_exposes_explicit_stream_and_path_ingest_methods`
- `test_ingestion_progress_rows_are_persisted_in_pipeline_order`
- `test_ingestion_progress_records_failed_step_when_ingest_errors`
- `test_embedding_requests_are_batched_for_chunk_ingestion`

### 7.3 Metadata store / restart recovery
- `test_metadata_store_uses_sqlalchemy_orm_models_and_chunk_table`
- `test_ingest_text_persists_milvus_generated_chunk_ids_to_metadata`
- `test_chunk_rows_are_persisted_and_rehydrated_across_restarts`
- `test_metadata_persists_across_restarts`

### 7.4 Document deletion / rollback
- `test_delete_document_removes_metadata_chunks_asset_and_query_visibility`
- `test_ingestion_service_store_rolls_back_milvus_chunks_when_chunk_persistence_fails`
- `test_ingestion_service_store_rolls_back_milvus_chunks_when_generated_id_count_is_mismatched`
- `test_delete_document_leaves_metadata_intact_when_milvus_delete_fails_and_allows_retry`

### 7.5 Composition / health check
- `test_bootstrap_rag_core_builds_core_from_service_factory`
- `test_package_root_exports_bootstrap_helper`
- `test_ollama_factories_use_docmesh_service_factory_when_available`
- `test_rag_core_health_check_uses_docmesh_aggregate_when_available`
- `test_rag_core_uses_milvus_fallback_settings_when_docmesh_settings_are_unavailable`

### 7.6 Adapter contracts
- `test_ollama_embedding_client_uses_injected_client`
- `test_ollama_embedding_client_wraps_ollama_transport_errors`
- `test_ollama_embedding_client_rejects_malformed_embeddings_response`
- `test_ollama_generation_client_uses_injected_client`
- `test_ollama_generation_client_wraps_transport_errors`
- `test_ollama_generation_client_rejects_malformed_response`

---

## 8. 권장 실행 방법

프로젝트 루트에서 실행:

```bash
uv run pytest -q
```

영역별 실행 예시:

```bash
uv run pytest test_rag_system_core/domain -q
uv run pytest test_rag_system_core/composition -q
uv run pytest test_rag_system_core/adapters -q
```

단일 시나리오 예시:

```bash
uv run pytest test_rag_system_core/domain/test_deletion_and_rollback.py::test_delete_document_leaves_metadata_intact_when_milvus_delete_fails_and_allows_retry -q
uv run pytest test_rag_system_core/composition/test_docmesh_integration.py::test_resolve_user_id_uses_keycloak_when_auth_mode_enabled -q
```

---

## 9. 테스트 통과 기준

다음을 만족하면 현재 구현이 `docs/srs.md`와 실질적으로 정렬된다고 본다.

1. 기능 요구사항(`SRS-FR-*`)에 대해 문서상 `검증됨`으로 분류된 항목의 자동화 테스트가 통과한다.
2. user scope, metadata store, vector store, restart recovery, document deletion 관련 핵심 시나리오가 통과한다.
3. adapter 계약 테스트가 통과한다.
4. composition / health check 관련 테스트가 통과한다.
5. cross-user leakage가 발생하지 않는다.

---

## 10. 미검증/부분 검증 항목 및 보강 권장사항

### 10.1 부분 검증 또는 문서 전제 항목
- `SRS-NFR-002`: top-k retrieval의 “예측 가능성”은 동작 수준으로는 검증되나 정량 기준은 없다.
- `SRS-NFR-003`: health check의 “빠른 실패 감지”는 시간 기준 테스트가 없다.
- `SRS-NFR-004 ~ 005`: 확장성/구조 분리는 주로 코드 구조 성격이라 직접 자동화 검증 범위가 제한적이다.
- `SRS-NFR-011 ~ 013`: API/타입/통합 분리 원칙은 간접 검증 중심이다.
- `SRS-NFR-014`: 실행 환경/의존성은 CI 또는 설치 검증 문서로 별도 관리가 필요하다.
- `SRS-DR-006`: `memory` storage mode의 재시작 후 비영속성은 명시적 재시작 테스트를 추가하면 더 좋다.

### 10.2 향후 추가 권장 테스트
- Keycloak 응답에 `sub`가 없고 `preferred_username`만 있는 경우 검증
- Keycloak 응답에 둘 다 없는 경우 실패 검증
- `health_check()` local fallback 결과 shape 검증
- `memory` storage mode의 재시작 후 비영속성 명시 검증
- UTF-8 decode 불가 파일 입력 시 실패 동작 명시 검증
- custom vector store 구현체 contract test 추가
- 비기능 요구사항 중 시간/성능 기준이 필요한 항목의 정량 테스트 분리
