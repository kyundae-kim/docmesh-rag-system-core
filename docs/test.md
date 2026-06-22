# DocMesh RAG Core Test Specification

## 1. 목적

이 문서는 `DocMesh RAG Core`의 **현재 구현**을 검증하기 위한 테스트 목적, 범위, 시나리오, 실행 방법을 정의한다.

핵심 목적:
- 사용자 scope 해석이 올바른지 검증
- ingestion/query/document management public API가 의도대로 동작하는지 검증
- SQLite metadata 및 Milvus Lite 기반 retrieval 복원이 동작하는지 검증
- DocMesh 통합(설정, factory, bootstrap, health check, Keycloak auth)이 올바르게 연결되는지 검증
- 기본 제공 Ollama adapter의 계약과 오류 처리 방식이 코드와 일치하는지 검증

---

## 2. 테스트 범위

### 2.1 포함 범위
- `RAGCore` public API 동작
- `IngestionService`, `RetrievalService`, `GenerationService` 통합 동작
- SQLAlchemy ORM + SQLite persistence
- 재시작 후 retrieval 복원
- 문서 자산 저장 (`memory`, `local`)
- 문서 삭제 및 rollback 성격 검증
- DocMesh composition 계층 동작
- Keycloak 모드 user id 해석
- Ollama adapter의 정상/오류/health-check 동작

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
2. **실제 persistence 검증**
   - SQLite 파일, ORM 테이블, 재초기화 후 조회/검색까지 확인한다.
3. **사용자 격리 우선**
   - token 또는 Keycloak 기반 user scope 간 데이터 혼합이 없어야 한다.
4. **재시작 시나리오 포함**
   - 저장 성공뿐 아니라 재초기화 후 retrieval 복원까지 확인한다.
5. **실패 경로 검증**
   - malformed adapter response, Milvus chunk id mismatch, chunk persistence 실패, delete 실패 등 오류 경로를 검증한다.
6. **DocMesh 통합 검증**
   - settings/service registry/health/auth 연동이 실제 조립 흐름과 일치하는지 확인한다.

---

## 4. 테스트 대상 public API

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
- `bootstrap_rag_core_from_docmesh(...)`
- `create_rag_embedding_client(...)`
- `create_rag_generation_client(...)`
- `create_rag_vector_store(...)`
- `resolve_user_id(...)`

### 4.3 Adapter / protocol boundary
- `OllamaEmbeddingClient`
- `OllamaGenerationClient`
- `EmbeddingClient`
- `GenerationClient`

---

## 5. 핵심 테스트 시나리오

### 5.1 사용자 스코프 및 인증
- token이 있으면 기본 auth 모드에서 token 문자열이 그대로 user scope가 되어야 한다.
- token이 없거나 공백이면 `single-user`로 fallback 되어야 한다.
- 서로 다른 token 간 query 결과가 섞이면 안 된다.
- `get_document(...)`, `list_document_chunks(...)`, `list_ingestion_progress(...)`, `delete_document(...)`는 현재 scope 기준으로 제한되어야 한다.
- `DOCMESH_AUTH_MODE=keycloak`일 때 token에서 `sub` 또는 `preferred_username`를 해석해야 한다.

### 5.2 문서 적재 API
- 텍스트 적재가 성공해야 한다.
- 파일 스트림 적재가 성공해야 한다.
- 파일 경로 적재가 성공해야 한다.
- 파일 스트림 적재는 `source`가 없을 때 실패해야 한다.
- `RAGCore`, `IngestionService`, `DocumentStorage`가 각 경로에 대한 명시적 메서드를 가져야 한다.
- `ingest_file` 또는 `store_bytes` 같은 legacy-style 단일 메서드에 의존하지 않아야 한다.

### 5.3 문서 자산 저장
- `local` 모드에서는 managed asset 파일이 실제로 저장되어야 한다.
- `memory` 모드에서는 `memory://...` 논리 경로가 기록되어야 한다.
- metadata는 문서 본문 대신 `storage_path`를 저장해야 한다.
- 파일명은 원본 `source`와 다를 수 있으며 `doc_id + suffix` 형태가 된다.

### 5.4 SQLAlchemy ORM persistence
- `documents`, `chunks`, `ingestion_progress` 테이블이 생성되어야 한다.
- `DocumentModel`, `ChunkModel`, `IngestionProgressModel`이 구현되어 있어야 한다.
- 문서 row, chunk row, progress row가 기대 값으로 저장되어야 한다.
- chunk metadata는 `metadata_json`으로 저장되어야 한다.

### 5.5 ingestion progress
- 문서 적재 후 단계별 progress row가 저장되어야 한다.
- 단계 순서는 `load -> preprocess -> chunking -> embedding -> vector_store -> chunk_persistence` 여야 한다.
- 각 단계는 정상 시 `running`, `completed` 전이를 남겨야 한다.
- 오류 시 적절한 단계에 `failed` 상태가 기록되어야 한다.
- 같은 문서에 대해 여러 ingest가 발생하면 `job_id`로 그룹화할 수 있어야 한다.

### 5.6 embedding / query / prompt
- ingestion은 chunk 전체에 대해 batch 1회 embedding 호출을 수행해야 한다.
- query는 현재 user scope에 맞는 chunk만 반환해야 한다.
- prompt에는 `[System Prompt]`, `[Retrieved Context]`, `[User Query]`가 포함되어야 한다.
- generation 결과는 `QueryResult.answer`로 반환되어야 한다.

### 5.7 재시작 복원
- 재초기화 후에도 문서 metadata가 조회되어야 한다.
- 동일한 Milvus 저장소/collection을 사용할 때 query가 계속 가능해야 한다.
- fallback Milvus 설정과 환경 변수 기반 설정 둘 다 검증해야 한다.

### 5.8 삭제 및 rollback 특성
- 문서 삭제 성공 시 metadata, chunk, progress, asset, 검색 결과 가시성이 함께 제거되어야 한다.
- chunk persistence 실패 시 이미 생성된 Milvus chunk id는 rollback 삭제되어야 한다.
- Milvus가 chunk id 개수를 잘못 반환하면 metadata 저장 전에 rollback 되어야 한다.
- document delete에서 Milvus 삭제가 실패하면 metadata는 유지되어야 하고 재시도가 가능해야 한다.

### 5.9 DocMesh 통합
- bootstrap helper가 DocMesh settings/runtime/factory를 사용해야 한다.
- factory는 DocMesh service registry를 우선 사용해야 한다.
- Ollama model 설정이 비어 있으면 factory는 실패해야 한다.
- health check는 가능한 경우 DocMesh aggregate를 사용해야 한다.
- DocMesh settings가 없을 때는 Milvus fallback 경로를 사용해야 한다.

### 5.10 Ollama adapter 계약
- `OllamaEmbeddingClient`는 injected client를 사용해야 한다.
- embedding transport 오류는 지정된 RuntimeError로 감싸야 한다.
- malformed embeddings response는 지정된 RuntimeError로 처리해야 한다.
- `OllamaGenerationClient`는 injected client를 사용해야 한다.
- generation transport 오류와 malformed generation response도 각각 지정된 RuntimeError로 처리해야 한다.
- 두 adapter 모두 health check를 내부 client로 위임해야 한다.

---

## 6. 현재 테스트 파일 매핑

현재 테스트는 단일 파일이 아니라 기능별로 분리되어 있다.

### 6.1 Domain API / 동작
- `test_rag_system_core/domain/test_ingestion_api.py`
- `test_rag_system_core/domain/test_query.py`
- `test_rag_system_core/domain/test_metadata_and_progress.py`
- `test_rag_system_core/domain/test_deletion_and_rollback.py`

### 6.2 Composition / DocMesh integration
- `test_rag_system_core/composition/test_bootstrap.py`
- `test_rag_system_core/composition/test_docmesh_integration.py`
- `test_rag_system_core/composition/test_core_configuration.py`
- `test_rag_system_core/composition/test_auth_runtime.py`

### 6.3 Adapter
- `test_rag_system_core/adapters/test_ollama_embedding_client.py`
- `test_rag_system_core/adapters/test_ollama_generation_client.py`

### 6.4 보조 파일
- `test_rag_system_core/conftest.py`
- `test_rag_system_core/support.py`

---

## 7. 대표 테스트 항목

### 7.1 Ingestion / user scope
- `test_ingest_text_uses_token_as_user_scope`
- `test_ingest_text_without_token_uses_single_user_scope`
- `test_blank_token_falls_back_to_single_user_scope`
- `test_ingest_file_stream_requires_explicit_source`
- `test_ragcore_exposes_explicit_stream_and_path_ingest_methods`

### 7.2 Query / prompt
- `test_query_filters_results_by_token_derived_user_id`
- `test_query_prompt_includes_system_query_and_context`

### 7.3 Metadata / progress / restart
- `test_metadata_store_uses_sqlalchemy_orm_models_and_chunk_table`
- `test_ingest_text_persists_milvus_generated_chunk_ids_to_metadata`
- `test_ingestion_progress_rows_are_persisted_in_pipeline_order`
- `test_ingestion_progress_records_failed_step_when_ingest_errors`
- `test_chunk_rows_are_persisted_and_rehydrated_across_restarts`
- `test_metadata_persists_across_restarts`

### 7.4 Deletion / rollback
- `test_delete_document_removes_metadata_chunks_asset_and_query_visibility`
- `test_ingestion_service_store_rolls_back_milvus_chunks_when_chunk_persistence_fails`
- `test_ingestion_service_store_rolls_back_milvus_chunks_when_generated_id_count_is_mismatched`
- `test_delete_document_leaves_metadata_intact_when_milvus_delete_fails_and_allows_retry`
- `test_embedding_requests_are_batched_for_chunk_ingestion`

### 7.5 Composition / auth / health
- `test_bootstrap_rag_core_from_docmesh_uses_docmesh_runtime`
- `test_ollama_factories_use_docmesh_service_factory_when_available`
- `test_rag_core_health_check_uses_docmesh_aggregate_when_available`
- `test_resolve_user_id_uses_keycloak_when_auth_mode_enabled`
- `test_rag_core_uses_milvus_fallback_settings_when_docmesh_settings_are_unavailable`

### 7.6 Adapter
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

다음을 만족하면 현재 구현이 문서와 일치한다고 본다.

1. 모든 public API 테스트가 통과한다.
2. 모든 adapter 계약 테스트가 통과한다.
3. 모든 composition / DocMesh integration 테스트가 통과한다.
4. 재시작 복원 및 삭제 rollback 관련 시나리오가 통과한다.
5. 사용자 격리 관련 시나리오에서 cross-user leakage가 없어야 한다.

---

## 10. 향후 추가 권장 테스트

- Keycloak 응답에 `sub`가 없고 `preferred_username`만 있는 경우 검증
- Keycloak 응답에 둘 다 없는 경우 실패 검증
- `health_check()` 로컬 fallback 결과 shape 검증
- `memory` storage mode에서 delete 이후 메모리 자산 제거 검증 강화
- UTF-8 decode 불가 파일 입력 시 실패 동작 명시 검증
- custom vector store 구현체 contract test 추가
