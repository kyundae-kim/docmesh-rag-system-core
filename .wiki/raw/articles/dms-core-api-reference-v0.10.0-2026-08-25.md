---
source_url: https://github.com/kyundae-kim/dms-core/wiki/API-Reference-v0.10.0
ingested: 2026-08-25
sha256: a436f8d1927f70be1b8ad11ac3b54c88c7e5a5b7f2a0cfa13c01da3a928270cc
---
# DMS SDK 공개 API 레퍼런스 (v0.10.0)

- 기준 버전: `0.10.0`
- 기준 소스: `dms-core` commit `d508b7c2ea82fb79bfcf008c948a364fcaa962d9` (`feature-v0.9.0-dev`, `pyproject.toml` 버전 `0.10.0`)
- 대상: 다른 Python 애플리케이션에서 `import`하여 사용하는 SDK
- 권장 import 경계: `dms` package root
- 사용 예제: [Examples-v0.10.0](Examples-v0.10.0.md)
- 추적 규칙: `source path:line`, `test path::test_function`, `E-xx` 예제 anchor

이 문서는 기준 checkout의 `dms.__all__` 55개 이름과 네 가지 공개 facade의 모든 public method를 기록한다. `dms.sdk.__all__`은 54개이며, `dms.__all__`은 여기에 `DocumentStatus`를 추가한다. 각 이름과 작업은 아래 표에서 실제 source, 테스트 근거, 예제 anchor 및 기능별 trace ID로 연결한다. 이전 Wiki 페이지는 과거 release 기록으로 보존하며, 새 소비 코드는 이 페이지의 `0.10.0` signature와 경계를 사용한다.

> **중요한 경계**
>
> DMS는 독립 실행형 API 서버가 아니라 host 애플리케이션에 주입되어 사용되는 Python SDK다. SQLAlchemy engine, MinIO client, 저장소 component의 생성·readiness·종료는 host가 담당한다. SDK facade에는 전역 `close()`, `aclose()`, `check_health()`가 없다.

## 1. 공개 import 경계

소비 프로젝트는 기본적으로 다음 경계에서 import한다.

```python
from dms import DocumentManagementSDKFactory, UploadDocumentRequest
```

`dms.sdk`도 대부분 같은 공개 이름을 재-export하지만, 안정적인 소비자 계약은 `from dms import ...`다. 내부 adapter와 저장소 port는 공개 import 경계가 아니다.

### 1.1 package root 공개 이름 전체

아래 55개 이름은 모두 `from dms import ...`로 접근할 수 있다. 표의 source line은 기준 commit의 실제 정의 위치이며, 테스트가 통합 테스트인 경우 환경이 없으면 skip될 수 있다. `source-only`는 source와 예제는 있지만 해당 세부 동작을 직접 실행하는 focused test가 없는 경우다.

| 공개 이름 | 종류 | source | 테스트 근거 | example | trace |
| --- | --- | --- | --- | --- | --- |
| `AccessContext` | immutable access context | `dms/sdk/contracts.py:66` | `test_dms/test_sdk_multi_user.py::test_user_id_is_available_to_access_policy_and_public_serialization` | [E-10](Examples-v0.10.0.md#example-e10) | `TR-POLICY` |
| `AccessDeniedError` | SDK exception | `dms/sdk/errors.py:34` | `test_dms/test_sdk_multi_user.py::test_user_scoped_facades_isolate_upload_list_read_and_delete` | [E-10](Examples-v0.10.0.md#example-e10), [E-12](Examples-v0.10.0.md#example-e12) | `TR-ERR` |
| `AsyncDocumentContentStream` | async content stream | `dms/sdk/types.py:210` | `test_dms/test_sdk_contract_completion.py::test_async_closing_iterator_closes_on_exhaustion_and_explicit_early_stop` | [E-06](Examples-v0.10.0.md#example-e06), [E-11](Examples-v0.10.0.md#example-e11) | `TR-ASYNC` |
| `AsyncDocumentManagementSDK` | async facade | `dms/sdk/async_sdk.py:103` | `test_dms/test_sdk_contract_completion.py::test_async_facade_runs_metadata_list_delete_without_global_lifecycle` | [E-11](Examples-v0.10.0.md#example-e11) | `TR-ASYNC` |
| `AsyncDocumentManagementSDKFactory` | native async factory | `dms/sdk/factory.py:115` | `test_dms/test_sdk_factory_integration.py::test_async_factory_round_trips_document_through_postgres_and_minio` (integration) | [E-02](Examples-v0.10.0.md#example-e02), [E-11](Examples-v0.10.0.md#example-e11) | `TR-ASM` |
| `AsyncScopedDocumentManagementSDK` | async scoped facade | `dms/sdk/async_sdk.py:569` | `test_dms/test_sdk_multi_user.py::test_async_scoped_facade_preserves_user_isolation` | [E-10](Examples-v0.10.0.md#example-e10), [E-11](Examples-v0.10.0.md#example-e11) | `TR-ASYNC` |
| `BatchReconciliationResult` | batch recovery result | `dms/sdk/types.py:448` | `test_dms/test_sdk_reconciliation.py::test_batch_summary_properties_are_stable` | [E-09](Examples-v0.10.0.md#example-e09) | `TR-REC` |
| `ConfigurationError` | configuration exception | `dms/sdk/errors.py:20` | `test_dms/test_sdk_factory.py::test_factory_rejects_blank_bucket_before_adapter_assembly` | [E-01](Examples-v0.10.0.md#example-e01), [E-12](Examples-v0.10.0.md#example-e12) | `TR-ERR` |
| `ConsistencyError` | consistency exception | `dms/sdk/errors.py:85` | `test_dms/test_sdk_behavior.py::test_upload_document_cleans_up_object_when_metadata_save_fails` | [E-03](Examples-v0.10.0.md#example-e03), [E-09](Examples-v0.10.0.md#example-e09), [E-12](Examples-v0.10.0.md#example-e12) | `TR-ERR` |
| `DataResetError` | partial reset exception | `dms/sdk/errors.py:92` | `test_dms/test_sdk_data_reset.py::test_clear_all_data_reports_partial_cleanup_and_continues_other_stores` | [E-07](Examples-v0.10.0.md#example-e07), [E-12](Examples-v0.10.0.md#example-e12) | `TR-RESET` |
| `DataResetResult` | reset result | `dms/sdk/types.py:329` | `test_dms/test_sdk_data_reset.py::test_data_reset_result_exposes_json_schema` | [E-07](Examples-v0.10.0.md#example-e07) | `TR-RESET` |
| `DataResetter` | runtime-checkable reset protocol | `dms/sdk/contracts.py:226` | `test_dms/test_sdk_data_reset.py::test_default_sdk_satisfies_data_resetter_contract` | [E-07](Examples-v0.10.0.md#example-e07), [E-10](Examples-v0.10.0.md#example-e10) | `TR-CONTRACT` |
| `DefaultDocumentManagementSDK` | sync facade | `dms/sdk/implementation.py:71` | `test_dms/test_sdk_factory.py::test_sdk_accepts_injected_storage_ports` | [E-01](Examples-v0.10.0.md#example-e01), [E-02](Examples-v0.10.0.md#example-e02) | `TR-ASM` |
| `DeleteDocumentResult` | delete result | `dms/sdk/types.py:309` | `test_dms/test_sdk_requirement_feedback.py::test_public_models_have_stable_json_serialization` | [E-07](Examples-v0.10.0.md#example-e07) | `TR-DEL` |
| `DmsError` | base SDK exception | `dms/sdk/errors.py:6` | `test_dms/test_sdk_requirement_feedback.py::test_all_public_sdk_errors_expose_structured_contract` (subclass contract) | [E-12](Examples-v0.10.0.md#example-e12) | `TR-ERR` |
| `DmsOperationContext` | immutable operation context | `dms/sdk/contracts.py:91` | `test_dms/test_sdk_consumer_integration_contracts.py::test_scoped_operation_context_supplies_opaque_default_metadata` | [E-10](Examples-v0.10.0.md#example-e10), [E-11](Examples-v0.10.0.md#example-e11) | `TR-POLICY` |
| `DocumentAccessPolicy` | host authorization protocol | `dms/sdk/contracts.py:81` | `test_dms/test_sdk_consumer_integration_contracts.py::test_access_policy_filters_before_paging_and_covers_privileged_reads` | [E-10](Examples-v0.10.0.md#example-e10) | `TR-POLICY` |
| `DocumentContent` | eager content result | `dms/sdk/types.py:145` | `test_dms/test_sdk_behavior.py::test_upload_document_persists_metadata_and_content` | [E-06](Examples-v0.10.0.md#example-e06), [E-11](Examples-v0.10.0.md#example-e11) | `TR-READ` |
| `DocumentContentStream` | sync content stream | `dms/sdk/types.py:155` | `test_dms/test_sdk_lifecycle_and_conflicts.py::test_document_content_stream_context_manager_closes_idempotently` | [E-06](Examples-v0.10.0.md#example-e06) | `TR-READ` |
| `DocumentCopyResult` | sink copy result | `dms/sdk/contracts.py:144` | `test_dms/test_sdk_consumer_integration_contracts.py::test_copy_document_to_closes_source_and_keeps_sink_open` | [E-06](Examples-v0.10.0.md#example-e06) | `TR-READ` |
| `DocumentDeletedError` | deleted-content exception | `dms/sdk/errors.py:55` | `test_dms/test_sdk_public_contract.py::test_deleted_document_content_and_stream_raise_deleted_error` | [E-07](Examples-v0.10.0.md#example-e07), [E-12](Examples-v0.10.0.md#example-e12) | `TR-ERR` |
| `DocumentDeleter` | runtime-checkable delete protocol | `dms/sdk/contracts.py:218` | `test_dms/test_sdk_consumer_integration_contracts.py::test_default_sdk_satisfies_public_capability_protocols` | [E-07](Examples-v0.10.0.md#example-e07), [E-10](Examples-v0.10.0.md#example-e10) | `TR-CONTRACT` |
| `DocumentInspection` | consistency inspection result | `dms/sdk/types.py:406` | `test_dms/test_sdk_reconciliation_core.py::test_inspect_missing_metadata_is_a_typed_result_not_not_found` | [E-09](Examples-v0.10.0.md#example-e09) | `TR-REC` |
| `DocumentLister` | runtime-checkable list protocol | `dms/sdk/contracts.py:204` | `test_dms/test_sdk_consumer_integration_contracts.py::test_default_sdk_satisfies_public_capability_protocols` | [E-05](Examples-v0.10.0.md#example-e05), [E-10](Examples-v0.10.0.md#example-e10) | `TR-CONTRACT` |
| `DocumentManagementClient` | composed capability protocol | `dms/sdk/contracts.py:237` | `test_dms/test_sdk_consumer_integration_contracts.py::test_default_sdk_satisfies_public_capability_protocols` | [E-10](Examples-v0.10.0.md#example-e10) | `TR-CONTRACT` |
| `DocumentManagementSDKFactory` | sync client factory | `dms/sdk/factory.py:63` | `test_dms/test_sdk_factory.py::test_factory_assembles_sdk_from_sqlalchemy_engine_and_minio_client` | [E-01](Examples-v0.10.0.md#example-e01) | `TR-ASM` |
| `DocumentMetadata` | storage-bearing management metadata | `dms/domain/models.py:40` | `test_dms/test_sdk_public_contract.py::test_privileged_metadata_access_is_explicit` | [E-04](Examples-v0.10.0.md#example-e04), [E-09](Examples-v0.10.0.md#example-e09) | `TR-DATA` |
| `DocumentNotFoundError` | missing/hidden-document exception | `dms/sdk/errors.py:48` | `test_dms/test_sdk_behavior.py::test_get_document_metadata_raises_document_not_found_for_missing_id` | [E-07](Examples-v0.10.0.md#example-e07), [E-12](Examples-v0.10.0.md#example-e12) | `TR-ERR` |
| `DocumentPage` | cursor page result | `dms/sdk/types.py:367` | `test_dms/test_sdk_pagination.py::test_cursor_page_is_stable_opaque_and_status_bound` | [E-05](Examples-v0.10.0.md#example-e05) | `TR-READ` |
| `DocumentReader` | runtime-checkable read protocol | `dms/sdk/contracts.py:183` | `test_dms/test_sdk_consumer_integration_contracts.py::test_default_sdk_satisfies_public_capability_protocols` | [E-06](Examples-v0.10.0.md#example-e06), [E-10](Examples-v0.10.0.md#example-e10) | `TR-CONTRACT` |
| `DocumentWriter` | runtime-checkable upload protocol | `dms/sdk/contracts.py:160` | `test_dms/test_sdk_consumer_integration_contracts.py::test_default_sdk_satisfies_public_capability_protocols` | [E-03](Examples-v0.10.0.md#example-e03), [E-10](Examples-v0.10.0.md#example-e10) | `TR-CONTRACT` |
| `DuplicateDocumentError` | duplicate-ID exception | `dms/sdk/errors.py:62` | `test_dms/test_sdk_lifecycle_and_conflicts.py::test_upload_document_maps_database_conflict_to_duplicate_and_rolls_back_object` | [E-03](Examples-v0.10.0.md#example-e03), [E-12](Examples-v0.10.0.md#example-e12) | `TR-ERR` |
| `IdempotencyConflictError` | idempotency fingerprint conflict | `dms/sdk/errors.py:113` | source-only: persistent replay/conflict focused test gap in this checkout | [E-08](Examples-v0.10.0.md#example-e08), [E-12](Examples-v0.10.0.md#example-e12) | `TR-ERR` |
| `IdempotencyInProgressError` | pending idempotency exception | `dms/sdk/errors.py:120` | `test_dms/test_sdk_requirement_feedback.py::test_all_public_sdk_errors_expose_structured_contract` (contract-only) | [E-08](Examples-v0.10.0.md#example-e08), [E-12](Examples-v0.10.0.md#example-e12) | `TR-ERR` |
| `MetadataStoreError` | metadata persistence exception | `dms/sdk/errors.py:77` | `test_dms/test_sdk_behavior.py::test_get_document_metadata_raises_metadata_store_error_for_backend_failure` | [E-04](Examples-v0.10.0.md#example-e04), [E-12](Examples-v0.10.0.md#example-e12) | `TR-ERR` |
| `OperationEvent` | observer event model | `dms/sdk/contracts.py:115` | `test_dms/test_sdk_consumer_integration_contracts.py::test_operation_observer_receives_safe_success_and_failure_events` | [E-10](Examples-v0.10.0.md#example-e10) | `TR-OBS` |
| `OperationObserver` | observer callback protocol | `dms/sdk/contracts.py:140` | `test_dms/test_sdk_consumer_integration_contracts.py::test_observer_failure_does_not_change_document_result` | [E-10](Examples-v0.10.0.md#example-e10) | `TR-OBS` |
| `PayloadTooLargeError` | configured-size exception | `dms/sdk/errors.py:41` | `test_dms/test_sdk_feedback_async_cursor.py::test_configured_file_size_limit_has_distinct_public_error` | [E-03](Examples-v0.10.0.md#example-e03), [E-12](Examples-v0.10.0.md#example-e12) | `TR-ERR` |
| `PublicDocumentMetadata` | public-safe metadata | `dms/sdk/types.py:66` | `test_dms/test_sdk_public_contract.py::test_default_metadata_and_upload_results_hide_storage_key` | [E-04](Examples-v0.10.0.md#example-e04), [E-05](Examples-v0.10.0.md#example-e05) | `TR-DATA` |
| `ReconciliationPlan` | immutable recovery plan | `dms/sdk/types.py:517` | `test_dms/test_sdk_reconciliation.py::test_dry_run_exports_plan_and_execution_revalidates_stale_items_with_best_effort_audit` | [E-09](Examples-v0.10.0.md#example-e09) | `TR-REC` |
| `ReconciliationPlanItem` | immutable plan item | `dms/sdk/types.py:503` | `test_dms/test_independent_review_regressions.py::test_plan_is_immutable_action_bound_and_preserves_empty_batch_origin` | [E-09](Examples-v0.10.0.md#example-e09) | `TR-REC` |
| `ReconciliationResult` | single recovery result | `dms/sdk/types.py:428` | `test_dms/test_sdk_reconciliation_core.py::test_batch_is_bounded_status_restricted_dry_run_and_preserves_item_errors` | [E-09](Examples-v0.10.0.md#example-e09) | `TR-REC` |
| `RecoveryAction` | recovery action enum | `dms/sdk/types.py:399` | `test_dms/test_sdk_reconciliation_core.py::test_complete_deletion_requires_deleting_and_absent_object_then_soft_or_hard` | [E-09](Examples-v0.10.0.md#example-e09) | `TR-REC` |
| `RecoveryAuditEvent` | recovery audit event | `dms/sdk/types.py:536` | `test_dms/test_sdk_reconciliation.py::test_recovery_audit_records_actor_and_time_and_plan_requires_dry_run` | [E-09](Examples-v0.10.0.md#example-e09), [E-10](Examples-v0.10.0.md#example-e10) | `TR-OBS` |
| `RecoveryIssue` | consistency issue enum | `dms/sdk/types.py:391` | `test_dms/test_sdk_reconciliation_core.py::test_inspect_missing_metadata_is_a_typed_result_not_not_found` | [E-09](Examples-v0.10.0.md#example-e09) | `TR-REC` |
| `ScopedDocumentManagementSDK` | sync scoped facade | `dms/sdk/implementation.py:1012` | `test_dms/test_sdk_consumer_integration_contracts.py::test_scoped_operation_context_supplies_opaque_default_metadata` | [E-10](Examples-v0.10.0.md#example-e10), [E-11](Examples-v0.10.0.md#example-e11) | `TR-POLICY` |
| `StorageError` | object-storage exception | `dms/sdk/errors.py:69` | `test_dms/test_sdk_behavior.py::test_delete_document_storage_failure_marks_metadata_failed` | [E-03](Examples-v0.10.0.md#example-e03), [E-09](Examples-v0.10.0.md#example-e09), [E-12](Examples-v0.10.0.md#example-e12) | `TR-ERR` |
| `UploadDocumentRequest` | bytes upload request | `dms/sdk/types.py:15` | `test_dms/test_sdk_behavior.py::test_upload_document_persists_metadata_and_content` | [E-01](Examples-v0.10.0.md#example-e01), [E-03](Examples-v0.10.0.md#example-e03) | `TR-UPL` |
| `UploadDocumentResult` | upload result | `dms/sdk/types.py:48` | `test_dms/test_sdk_public_contract.py::test_default_metadata_and_upload_results_hide_storage_key` | [E-03](Examples-v0.10.0.md#example-e03), [E-04](Examples-v0.10.0.md#example-e04) | `TR-UPL` |
| `UploadDocumentStreamRequest` | known-size stream request | `dms/sdk/types.py:29` | `test_dms/test_sdk_stream_upload_contract.py::test_stream_request_is_public_and_uploads_without_buffering_as_bytes` | [E-03](Examples-v0.10.0.md#example-e03) | `TR-UPL` |
| `UploadOperationNotFoundError` | missing operation exception | `dms/sdk/errors.py:128` | `test_dms/test_sdk_factory_integration.py::test_factory_isolates_multiple_users_across_postgres_and_minio` (integration) | [E-08](Examples-v0.10.0.md#example-e08), [E-12](Examples-v0.10.0.md#example-e12) | `TR-ERR` |
| `UploadOperationResult` | idempotency operation result | `dms/sdk/types.py:125` | `test_dms/test_sdk_factory_integration.py::test_factory_isolates_multiple_users_across_postgres_and_minio` (integration) | [E-08](Examples-v0.10.0.md#example-e08) | `TR-UPL` |
| `ValidationError` | input/policy/cursor exception | `dms/sdk/errors.py:27` | `test_dms/test_sdk_stream_upload_contract.py::test_stream_upload_enforces_declared_size_and_rolls_back` | [E-03](Examples-v0.10.0.md#example-e03), [E-05](Examples-v0.10.0.md#example-e05), [E-09](Examples-v0.10.0.md#example-e09), [E-12](Examples-v0.10.0.md#example-e12) | `TR-ERR` |
| `public_metadata` | public projection function | `dms/sdk/types.py:112` | `test_dms/test_sdk_metadata.py::test_public_metadata_projection_accepts_metadata_and_upload_result_without_storage_key` | [E-04](Examples-v0.10.0.md#example-e04) | `TR-DATA` |
| `DocumentStatus` | document lifecycle enum; root-only addition | `dms/domain/models.py:9` | `test_dms/test_sdk_pagination.py::test_cursor_page_is_stable_opaque_and_status_bound` | [E-05](Examples-v0.10.0.md#example-e05), [E-09](Examples-v0.10.0.md#example-e09) | `TR-DATA` |

Package-root assembly itself is defined by `dms/__init__.py:1-5` and `dms/sdk/__init__.py:1-123`. The export-membership test is a contract check, not behavior coverage; the rows above keep source-only gaps visible.

### 1.2 공개하지 않는 이름과 기능

현재 package root 공개 API에는 다음이 포함되지 않는다.

- 환경변수에서 client를 생성하는 factory와 환경 진단 helper
- `MetadataStore`, `ObjectStore`, `UploadOperationStore` 및 async storage port의 구체 구현·내부 import 경로
- `UploadOperationState`와 내부 persistence 모델
- SDK가 자체 관리하는 인증·권한 정책 저장소
- `HealthStatus`, `ServiceHealth`, readiness endpoint 및 `check_health()`
- SDK 전역 resource `close()`/`aclose()` lifecycle
- HTTP response/error descriptor 모델
- 검색·일반 metadata filtering, presigned URL, message broker API
- unknown-size 또는 async input stream 직접 upload
- 독립 실행형 API 서버

`AsyncDocumentManagementSDK.from_async_components()`는 host가 이미 준비한 async storage component를 전달하는 고급 조립 경계지만, 그 component type 자체는 package root public export가 아니다.

## 2. 조립 API와 소유권

### 2.1 동기 client factory

`DocumentManagementSDKFactory`는 host가 만든 SQLAlchemy `Engine`과 MinIO client를 storage adapter에 연결한다.

```text
DocumentManagementSDKFactory(
    *,
    engine: Engine,
    minio_client: Minio,
    bucket_name: str,
    logger: logging.Logger | None = None,
    max_file_size: int | None = None,
    recovery_audit_hook: Callable[[RecoveryAuditEvent], object] | None = None,
    operation_observer: OperationObserver | None = None,
    access_policy: DocumentAccessPolicy | None = None,
) -> None

factory.create() -> DefaultDocumentManagementSDK
```

- `engine.dialect.name`은 `postgresql` 또는 `sqlite`여야 한다. 그 밖의 dialect는 `ConfigurationError`다.
- 공백만 있는 `bucket_name`은 factory 생성 시 `ConfigurationError`다.
- `max_file_size`가 지정되면 양수여야 하며, 위반은 factory에서 `ValueError`다.
- factory는 bucket이 없으면 생성할 수 있지만, 주입된 client와 bucket의 종료·삭제 lifecycle은 host가 소유한다.
- sync factory에는 `create_async()`가 없다. native async 조립에는 별도의 `AsyncDocumentManagementSDKFactory`를 사용한다.
- factory가 조립한 operation store는 engine을 사용하므로, idempotency upload와 operation 조회가 필요하면 factory 경로를 사용할 수 있다.

### 2.2 native async factory

```text
AsyncDocumentManagementSDKFactory(
    *,
    engine: AsyncEngine,
    minio_client: Minio,
    bucket_name: str,
    logger: logging.Logger | None = None,
    max_file_size: int | None = None,
    recovery_audit_hook: Callable[[RecoveryAuditEvent], object] | None = None,
    operation_observer: OperationObserver | None = None,
    access_policy: DocumentAccessPolicy | None = None,
) -> None

factory.create() -> AsyncDocumentManagementSDK
await factory.create_async() -> AsyncDocumentManagementSDK
```

- `engine`은 `AsyncEngine`이어야 한다. 잘못된 engine은 `ConfigurationError`다.
- `create()`는 lazy native async SDK를 반환하며 첫 await에서 초기화가 수행된다.
- `create_async()`는 SDK를 만들고 `ready()`까지 기다린 뒤 반환한다.
- 동기 factory에서 만든 SDK를 awaitable compatibility facade로 감싸려면 `AsyncDocumentManagementSDK(sync_sdk)`를 사용할 수 있다. 두 경로를 같은 native async assembly로 혼동하지 않는다.
- 비동기 facade도 전역 client lifecycle을 소유하지 않는다.

### 2.3 component 직접 조립

host가 이미 준비한 component를 직접 전달할 때는 다음 signature를 사용한다.

```text
DefaultDocumentManagementSDK(
    *,
    metadata_store: MetadataStore,
    object_store: ObjectStore,
    logger: logging.Logger | None = None,
    max_file_size: int | None = None,
    operation_store: UploadOperationStore | None = None,
    recovery_audit_hook: Callable[[RecoveryAuditEvent], object] | None = None,
    access_policy: DocumentAccessPolicy | None = None,
    operation_observer: OperationObserver | None = None,
) -> None
```

`metadata_store`, `object_store`, `operation_store`는 구조적 component 계약이며 package root export가 아니다. host는 기존 adapter 또는 자체 adapter를 전달할 수 있지만 해당 객체의 생성·readiness·종료는 host가 관리한다. `operation_store`를 생략하면 persistent idempotency upload와 operation 조회는 사용할 수 없다. 직접 조립에서 `max_file_size <= 0`은 `ValidationError`다.

고급 native async component 경계는 다음과 같다.

```text
AsyncDocumentManagementSDK.from_async_components(
    *,
    metadata_store: AsyncMetadataStore,
    object_store: AsyncObjectStore,
    operation_store: AsyncUploadOperationStore | None = None,
    logger=None,
    max_file_size: int | None = None,
    recovery_audit_hook=None,
    operation_observer=None,
    access_policy=None,
    initialize: Callable[[], Awaitable[object] | object] | None = None,
) -> AsyncDocumentManagementSDK
```

이 classmethod와 `ready()`는 public class member이므로 facade 표에 포함했지만, 기준 checkout에는 이 두 세부 경계를 직접 실행하는 focused test가 없다. 일반 소비자는 factory 또는 `AsyncDocumentManagementSDK(sync_sdk)` 경계를 우선 사용한다.

compatibility wrapper의 생성 signature는 다음과 같다.

```text
AsyncDocumentManagementSDK(
    sdk: DefaultDocumentManagementSDK | None = None,
    *,
    async_core: AsyncDocumentManagementCore | None = None,
    initialize: Callable[[], Awaitable[object] | object] | None = None,
) -> AsyncDocumentManagementSDK
```

`sdk`와 `async_core` 중 정확히 하나를 전달해야 한다. `AsyncDocumentManagementCore`는 package-root export가 아닌 고급 component 조립 type이다.

### 2.4 facade 생성과 자원 경계

```text
sdk.scoped(context: DmsOperationContext) -> ScopedDocumentManagementSDK
async_sdk.scoped(context: DmsOperationContext) -> AsyncScopedDocumentManagementSDK
```

- scoped facade는 shared SDK와 context를 변경하지 않는 작업 범위 경계다.
- `DefaultDocumentManagementSDK`와 async facade 모두 전역 `close()`/`aclose()`를 제공하지 않는다.
- SDK가 upload 중 직접 연 local file과 SDK가 반환한 content stream은 SDK가 정리한다.
- caller가 제공한 upload input stream과 `copy_document_to()`의 sink는 SDK가 닫지 않는다.

## 3. 공개 facade method 전체 coverage

기준 checkout에서 `DefaultDocumentManagementSDK`는 26개 public member, `AsyncDocumentManagementSDK`는 28개 public member(`from_async_components`, `ready`, `scoped` 포함), 두 scoped facade는 각각 25개 작업 member를 가진다. 아래 표는 union 기준으로 모든 facade operation과 assembly member를 기록한다. `source`는 각 facade의 실제 정의 line이며, `scoped` 열의 `-`는 해당 facade가 그 member를 직접 제공하지 않는다는 뜻이다.

| method | 기본 sync source | 기본 async source | scoped sync source | scoped async source | 결과/형태 | 테스트 근거 | example |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `create` | `dms/sdk/factory.py:89` | `dms/sdk/factory.py:135` | - | - | SDK facade | `test_dms/test_sdk_factory.py::test_factory_assembles_sdk_from_sqlalchemy_engine_and_minio_client` | [E-01](Examples-v0.10.0.md#example-e01), [E-02](Examples-v0.10.0.md#example-e02) |
| `create_async` | - | `dms/sdk/factory.py:169` | - | - | initialized async SDK | `test_dms/test_sdk_factory_integration.py::test_async_factory_round_trips_document_through_postgres_and_minio` (integration) | [E-02](Examples-v0.10.0.md#example-e02) |
| `from_async_components` | - | `dms/sdk/async_sdk.py:130` | - | - | async SDK | source-only: direct component classmethod test gap | [E-02](Examples-v0.10.0.md#example-e02) |
| `ready` | - | `dms/sdk/async_sdk.py:158` | - | - | initialized async SDK | `test_dms/test_sdk_factory_integration.py::test_async_factory_round_trips_document_through_postgres_and_minio` (indirect, integration) | [E-02](Examples-v0.10.0.md#example-e02), [E-11](Examples-v0.10.0.md#example-e11) |
| `scoped` | `dms/sdk/implementation.py:117` | `dms/sdk/async_sdk.py:165` | - | - | scoped facade | `test_dms/test_sdk_consumer_integration_contracts.py::test_scoped_operation_context_supplies_opaque_default_metadata` | [E-10](Examples-v0.10.0.md#example-e10), [E-11](Examples-v0.10.0.md#example-e11) |
| `upload_document` | `dms/sdk/implementation.py:120` | `dms/sdk/async_sdk.py:197` | `dms/sdk/implementation.py:1048` | `dms/sdk/async_sdk.py:611` | `UploadDocumentResult` | `test_dms/test_sdk_behavior.py::test_upload_document_persists_metadata_and_content` | [E-01](Examples-v0.10.0.md#example-e01), [E-03](Examples-v0.10.0.md#example-e03) |
| `upload_file` | `dms/sdk/implementation.py:133` | `dms/sdk/async_sdk.py:209` | `dms/sdk/implementation.py:1088` | `dms/sdk/async_sdk.py:626` | `UploadDocumentResult` | `test_dms/test_sdk_consumer_integration_contracts.py::test_upload_file_and_known_size_stream_own_only_internally_opened_resources` | [E-03](Examples-v0.10.0.md#example-e03), [E-11](Examples-v0.10.0.md#example-e11) |
| `upload_document_stream` | `dms/sdk/implementation.py:171` | `dms/sdk/async_sdk.py:231` | `dms/sdk/implementation.py:1060` | `dms/sdk/async_sdk.py:651` | `UploadDocumentResult` | `test_dms/test_sdk_stream_upload_contract.py::test_stream_upload_enforces_declared_size_and_rolls_back` | [E-03](Examples-v0.10.0.md#example-e03) |
| `get_upload_operation` | `dms/sdk/implementation.py:186` | `dms/sdk/async_sdk.py:243` | `dms/sdk/implementation.py:1073` | `dms/sdk/async_sdk.py:667` | `UploadOperationResult` | `test_dms/test_sdk_factory_integration.py::test_factory_isolates_multiple_users_across_postgres_and_minio` (integration) | [E-08](Examples-v0.10.0.md#example-e08) |
| `get_internal_document_metadata` | `dms/sdk/implementation.py:199` | `dms/sdk/async_sdk.py:257` | `dms/sdk/implementation.py:1111` | `dms/sdk/async_sdk.py:688` | `DocumentMetadata` | `test_dms/test_sdk_public_contract.py::test_privileged_metadata_access_is_explicit` | [E-04](Examples-v0.10.0.md#example-e04), [E-09](Examples-v0.10.0.md#example-e09) |
| `get_document_metadata` | `dms/sdk/implementation.py:219` | `dms/sdk/async_sdk.py:269` | `dms/sdk/implementation.py:1108` | `dms/sdk/async_sdk.py:691` | `PublicDocumentMetadata` | `test_dms/test_sdk_behavior.py::test_get_document_metadata_raises_document_not_found_for_missing_id` | [E-04](Examples-v0.10.0.md#example-e04), [E-07](Examples-v0.10.0.md#example-e07) |
| `list_documents` | `dms/sdk/implementation.py:236` | `dms/sdk/async_sdk.py:281` | `dms/sdk/implementation.py:1114` | `dms/sdk/async_sdk.py:694` | `DocumentPage` | `test_dms/test_sdk_behavior.py::test_list_documents_returns_cursor_paginated_metadata_filtered_by_status` | [E-05](Examples-v0.10.0.md#example-e05), [E-10](Examples-v0.10.0.md#example-e10) |
| `list_documents_page` | `dms/sdk/implementation.py:267` | `dms/sdk/async_sdk.py:297` | `dms/sdk/implementation.py:1128` | `dms/sdk/async_sdk.py:708` | `DocumentPage` | `test_dms/test_sdk_pagination.py::test_cursor_page_is_stable_opaque_and_status_bound` | [E-05](Examples-v0.10.0.md#example-e05) |
| `iter_documents` | `dms/sdk/implementation.py:338` | `dms/sdk/async_sdk.py:313` | `dms/sdk/implementation.py:1142` | `dms/sdk/async_sdk.py:722` | sync/async iterator | `test_dms/test_sdk_consumer_integration_contracts.py::test_document_and_recovery_iterators_preserve_page_conditions` | [E-05](Examples-v0.10.0.md#example-e05), [E-11](Examples-v0.10.0.md#example-e11) |
| `inspect_document` | `dms/sdk/implementation.py:359` | `dms/sdk/async_sdk.py:328` | `dms/sdk/implementation.py:1233` | `dms/sdk/async_sdk.py:817` | `DocumentInspection` | `test_dms/test_sdk_reconciliation_core.py::test_inspect_missing_metadata_is_a_typed_result_not_not_found` | [E-09](Examples-v0.10.0.md#example-e09) |
| `list_recovery_candidates` | `dms/sdk/implementation.py:397` | `dms/sdk/async_sdk.py:340` | `dms/sdk/implementation.py:1236` | `dms/sdk/async_sdk.py:820` | `list[DocumentMetadata]` | `test_dms/test_sdk_reconciliation_core.py::test_batch_is_bounded_status_restricted_dry_run_and_preserves_item_errors` | [E-09](Examples-v0.10.0.md#example-e09) |
| `iter_recovery_candidates` | `dms/sdk/implementation.py:449` | `dms/sdk/async_sdk.py:356` | `dms/sdk/implementation.py:1250` | `dms/sdk/async_sdk.py:834` | sync/async iterator | `test_dms/test_sdk_consumer_integration_contracts.py::test_document_and_recovery_iterators_preserve_page_conditions` | [E-09](Examples-v0.10.0.md#example-e09), [E-11](Examples-v0.10.0.md#example-e11) |
| `reconcile_document` | `dms/sdk/implementation.py:472` | `dms/sdk/async_sdk.py:371` | `dms/sdk/implementation.py:1262` | `dms/sdk/async_sdk.py:847` | `ReconciliationResult` | `test_dms/test_sdk_reconciliation_core.py::test_complete_deletion_requires_deleting_and_absent_object_then_soft_or_hard` | [E-09](Examples-v0.10.0.md#example-e09) |
| `execute_reconciliation_plan` | `dms/sdk/implementation.py:506` | `dms/sdk/async_sdk.py:391` | `dms/sdk/implementation.py:1280` | `dms/sdk/async_sdk.py:885` | `BatchReconciliationResult` | `test_dms/test_sdk_reconciliation.py::test_dry_run_exports_plan_and_execution_revalidates_stale_items_with_best_effort_audit` | [E-09](Examples-v0.10.0.md#example-e09) |
| `reconcile_documents` | `dms/sdk/implementation.py:551` | `dms/sdk/async_sdk.py:405` | `dms/sdk/implementation.py:1292` | `dms/sdk/async_sdk.py:865` | `BatchReconciliationResult` | `test_dms/test_sdk_reconciliation_core.py::test_batch_is_bounded_status_restricted_dry_run_and_preserves_item_errors` | [E-09](Examples-v0.10.0.md#example-e09) |
| `get_document_content` | `dms/sdk/implementation.py:604` | `dms/sdk/async_sdk.py:427` | `dms/sdk/implementation.py:1154` | `dms/sdk/async_sdk.py:735` | `DocumentContent` | `test_dms/test_sdk_behavior.py::test_upload_document_persists_metadata_and_content` | [E-06](Examples-v0.10.0.md#example-e06), [E-11](Examples-v0.10.0.md#example-e11) |
| `get_document_content_stream` | `dms/sdk/implementation.py:621` | `dms/sdk/async_sdk.py:439` | `dms/sdk/implementation.py:1169` | `dms/sdk/async_sdk.py:738` | sync/async stream | `test_dms/test_sdk_behavior.py::test_get_document_content_stream_returns_chunked_stream` | [E-06](Examples-v0.10.0.md#example-e06), [E-11](Examples-v0.10.0.md#example-e11) |
| `get_document_content_async_stream` | `dms/sdk/implementation.py:714` | `dms/sdk/async_sdk.py:461` | `dms/sdk/implementation.py:1157` | `dms/sdk/async_sdk.py:750` | `AsyncDocumentContentStream` | `test_dms/test_sdk_feedback_async_cursor.py::test_async_download_stream_closes_on_context_exit_and_exhaustion` | [E-06](Examples-v0.10.0.md#example-e06), [E-11](Examples-v0.10.0.md#example-e11) |
| `iter_document_chunks` | `dms/sdk/implementation.py:643` | `dms/sdk/async_sdk.py:474` | `dms/sdk/implementation.py:1181` | `dms/sdk/async_sdk.py:761` | sync/async bytes iterator | `test_dms/test_sdk_contract_completion.py::test_sync_closing_iterator_closes_on_exhaustion_and_explicit_early_stop` and `test_dms/test_sdk_contract_completion.py::test_async_closing_iterator_closes_on_exhaustion_and_explicit_early_stop` | [E-06](Examples-v0.10.0.md#example-e06), [E-11](Examples-v0.10.0.md#example-e11) |
| `copy_document_to` | `dms/sdk/implementation.py:660` | `dms/sdk/async_sdk.py:492` | `dms/sdk/implementation.py:1193` | `dms/sdk/async_sdk.py:777` | `DocumentCopyResult` | `test_dms/test_sdk_consumer_integration_contracts.py::test_copy_document_to_closes_source_and_keeps_sink_open` | [E-06](Examples-v0.10.0.md#example-e06) |
| `delete_document` | `dms/sdk/implementation.py:740` | `dms/sdk/async_sdk.py:510` | `dms/sdk/implementation.py:1209` | `dms/sdk/async_sdk.py:793` | `DeleteDocumentResult` | `test_dms/test_sdk_behavior.py::test_delete_document_soft_delete_marks_metadata_and_removes_content` | [E-07](Examples-v0.10.0.md#example-e07) |
| `soft_delete_document` | `dms/sdk/implementation.py:759` | `dms/sdk/async_sdk.py:524` | `dms/sdk/implementation.py:1221` | `dms/sdk/async_sdk.py:805` | `DeleteDocumentResult` | `test_dms/test_sdk_deletion.py::test_explicit_delete_methods_preserve_legacy_dispatch` | [E-07](Examples-v0.10.0.md#example-e07) |
| `hard_delete_document` | `dms/sdk/implementation.py:771` | `dms/sdk/async_sdk.py:536` | `dms/sdk/implementation.py:1224` | `dms/sdk/async_sdk.py:808` | `DeleteDocumentResult` | `test_dms/test_sdk_behavior.py::test_delete_document_hard_delete_removes_metadata` | [E-07](Examples-v0.10.0.md#example-e07) |
| `clear_all_data` | `dms/sdk/implementation.py:783` | `dms/sdk/async_sdk.py:548` | `dms/sdk/implementation.py:1227` | `dms/sdk/async_sdk.py:811` | `DataResetResult` | `test_dms/test_sdk_data_reset.py::test_clear_all_data_removes_documents_objects_and_upload_operations` | [E-07](Examples-v0.10.0.md#example-e07), [E-10](Examples-v0.10.0.md#example-e10) |
| `initialize_for_data_load` | `dms/sdk/implementation.py:793` | `dms/sdk/async_sdk.py:558` | `dms/sdk/implementation.py:1230` | `dms/sdk/async_sdk.py:814` | `DataResetResult` | `test_dms/test_sdk_data_reset.py::test_initialize_for_data_load_is_idempotent_and_leaves_empty_store` | [E-07](Examples-v0.10.0.md#example-e07), [E-11](Examples-v0.10.0.md#example-e11) |

`AsyncDocumentManagementSDK`는 awaitable이다(`dms/sdk/async_sdk.py:162-163`). async method는 `await`, async iterator는 `async for`로 사용한다. `get_document_content_async_stream()`은 sync facade에서도 명시적으로 async content stream 경계를 선택할 수 있다.

### 3.1 기본 sync facade signature

```text
sdk.upload_document(
    request: UploadDocumentRequest,
    *, access_context: AccessContext | None = None,
) -> UploadDocumentResult
sdk.upload_file(
    path: str | Path,
    *, filename: str | None = None, content_type: str | None = None,
    document_id: str | None = None, metadata: object = None,
    created_by: str | None = None,
    access_context: AccessContext | None = None,
) -> UploadDocumentResult
sdk.upload_document_stream(
    request: UploadDocumentStreamRequest,
    *, access_context: AccessContext | None = None,
) -> UploadDocumentResult
sdk.get_upload_operation(
    *, scope: str, idempotency_key: str,
    access_context: AccessContext | None = None,
) -> UploadOperationResult

sdk.get_internal_document_metadata(
    document_id: str, *, access_context: AccessContext | None = None,
) -> DocumentMetadata
sdk.get_document_metadata(
    document_id: str, *, access_context: AccessContext | None = None,
) -> PublicDocumentMetadata
sdk.list_documents(
    *, cursor: str | None = None, limit: int = 100,
    status: DocumentStatus | None = None,
    access_context: AccessContext | None = None,
) -> DocumentPage
sdk.list_documents_page(
    *, cursor: str | None = None, limit: int = 100,
    status: DocumentStatus | None = None,
    access_context: AccessContext | None = None,
) -> DocumentPage
sdk.iter_documents(
    *, status: DocumentStatus | None = None, page_size: int = 100,
    access_context: AccessContext | None = None,
) -> Iterator[PublicDocumentMetadata]

sdk.get_document_content(
    document_id: str, *, access_context: AccessContext | None = None,
) -> DocumentContent
sdk.get_document_content_stream(
    document_id: str, *, chunk_size: int = 65536,
    access_context: AccessContext | None = None,
) -> DocumentContentStream
sdk.get_document_content_async_stream(
    document_id: str, *, chunk_size: int = 65536,
    access_context: AccessContext | None = None,
) -> AsyncDocumentContentStream
sdk.iter_document_chunks(
    document_id: str, *, chunk_size: int = 65536,
    access_context: AccessContext | None = None,
) -> Iterator[bytes]
sdk.copy_document_to(
    document_id: str, sink: BinaryIO, *, chunk_size: int = 65536,
    verify_checksum: bool = True,
    access_context: AccessContext | None = None,
) -> DocumentCopyResult

sdk.delete_document(
    document_id: str, *, hard_delete: bool = False,
    access_context: AccessContext | None = None,
) -> DeleteDocumentResult
sdk.soft_delete_document(
    document_id: str, *, access_context: AccessContext | None = None,
) -> DeleteDocumentResult
sdk.hard_delete_document(
    document_id: str, *, access_context: AccessContext | None = None,
) -> DeleteDocumentResult
sdk.clear_all_data(
    *, access_context: AccessContext | None = None,
) -> DataResetResult
sdk.initialize_for_data_load(
    *, access_context: AccessContext | None = None,
) -> DataResetResult

sdk.inspect_document(
    document_id: str, *, access_context: AccessContext | None = None,
) -> DocumentInspection
sdk.list_recovery_candidates(
    *, status: DocumentStatus, offset: int = 0, limit: int = 100,
    access_context: AccessContext | None = None,
) -> list[DocumentMetadata]
sdk.iter_recovery_candidates(
    *, status: DocumentStatus, page_size: int = 100,
    access_context: AccessContext | None = None,
) -> Iterator[DocumentMetadata]
sdk.reconcile_document(
    document_id: str, action: RecoveryAction, *, storage_key: str | None = None,
    dry_run: bool = False, actor: str | None = None,
    access_context: AccessContext | None = None,
) -> ReconciliationResult
sdk.execute_reconciliation_plan(
    plan: ReconciliationPlan, *, actor: str | None = None,
    access_context: AccessContext | None = None,
) -> BatchReconciliationResult
sdk.reconcile_documents(
    *, status: DocumentStatus, action: RecoveryAction, offset: int = 0,
    limit: int = 100, dry_run: bool = False, actor: str | None = None,
    access_context: AccessContext | None = None,
) -> BatchReconciliationResult
```

### 3.2 async·scoped facade 규칙

- `AsyncDocumentManagementSDK`는 위 sync 이름을 awaitable로 제공하며, `iter_documents()`, `iter_recovery_candidates()`, `iter_document_chunks()`는 async iterator다.
- native async factory에서 얻은 SDK는 async storage component를 사용한다. `AsyncDocumentManagementSDK(sync_sdk)` compatibility 경계는 sync 작업을 event loop 밖에서 실행한다.
- `ScopedDocumentManagementSDK`와 `AsyncScopedDocumentManagementSDK`에는 `access_context` 인자가 없고 context의 `access`를 자동으로 전달한다.
- scoped context의 `user_id`, `created_by`, `idempotency_scope`, `audit_actor`, `default_metadata`는 생략된 작업 인자의 기본값이다. 작업에 명시한 값이 우선하지만 사용자 범위를 바꾸는 값은 `ValidationError`로 거부한다.
- `get_upload_operation(*, idempotency_key, scope=None)`에서 scope를 생략하면 context의 `idempotency_scope`를 사용한다. 둘 다 없으면 `ValidationError`다.
- scoped facade는 shared SDK를 변이시키지 않으며 전역 lifecycle method를 제공하지 않는다.

## 4. 입력·결과 모델

### 4.1 upload 입력과 결과

```text
UploadDocumentRequest(
    *,
    content: bytes,
    filename: str,
    content_type: str,
    document_id: str | None = None,
    metadata: Any = None,
    created_by: str | None = None,
    user_id: str | None = None,
    checksum: str | None = None,
    idempotency_key: str | None = None,
    idempotency_scope: str | None = None,
)

UploadDocumentStreamRequest(
    *,
    stream: BinaryIO,
    size: int,
    filename: str,
    content_type: str,
    document_id: str | None = None,
    metadata: Any = None,
    created_by: str | None = None,
)

UploadDocumentResult(
    document_id: str,
    metadata: PublicDocumentMetadata,
    created: bool = True,
)
```

- bytes 본문은 비어 있지 않아야 한다. filename, content type, 선택 문자열과 선언된 stream size는 공통 검증 대상이다.
- `document_id`를 생략하면 metadata store가 발급한 식별자가 결과에 반환된다. SDK가 별도 ID generator를 주입받는 계약은 없다.
- known-size stream은 양의 `size`와 동기 `read()`를 요구한다. 실제 읽은 크기가 선언값과 다르면 object를 정리한 뒤 `ValidationError`를 발생시킨다.
- `upload_file()`은 SDK가 파일을 열고 닫으며, filename/content type을 생략하면 path에서 결정한다. caller가 제공한 stream은 SDK가 닫지 않는다.
- `max_file_size`를 초과하면 `PayloadTooLargeError`다.
- unknown-size stream, async input stream, request별 max size/chunk size, request별 checksum/idempotency 입력은 현재 공개 upload surface가 아니다.

### 4.2 application-owned metadata와 user scope

`metadata`와 `DmsOperationContext.default_metadata`의 타입은 `object`/`Any`다. DMS는 호출자 부가 정보의 업무 schema, 보안 규칙, 정규화, JSON 직렬화를 정의하거나 검증하지 않는다. 값의 외부 직렬화 가능성 및 secret 포함 여부는 caller 책임이다.

```text
AccessContext(
    subject: str | None = None,
    user_id: str | None = None,
    tenant: str | None = None,
    roles: frozenset[str] = frozenset(),
)

DmsOperationContext(
    access: AccessContext | None = None,
    user_id: str | None = None,
    created_by: str | None = None,
    idempotency_scope: str | None = None,
    audit_actor: str | None = None,
    default_metadata: object = None,
)
```

- `AccessContext.user_id`와 `DmsOperationContext.user_id`는 지정하면 비어 있지 않은 문자열이어야 한다.
- operation context에 `user_id`를 지정하고 access context도 지정하면 두 값이 일치해야 한다. access가 없으면 해당 user ID로 access context가 보강된다.
- user-scoped facade는 문서 정보, object namespace, idempotency operation 및 cursor 조건에 같은 user scope를 적용한다.
- user-scoped upload request의 `user_id`가 context user와 다르면 저장 전에 `ValidationError`다.
- 다른 user scope의 문서 조회·본문·삭제·복구는 `AccessDeniedError`다. user-scoped reset은 해당 user의 DMS 관리 데이터만 삭제한다.

### 4.3 public metadata와 내부 metadata

```text
PublicDocumentMetadata(
    *,
    document_id: str,
    original_filename: str,
    content_type: str,
    file_size: int,
    status: DocumentStatus,
    created_at: datetime,
    updated_at: datetime,
    checksum: str | None = None,
    deleted_at: datetime | None = None,
    created_by: str | None = None,
    user_id: str | None = None,
    extra_metadata: Any = <empty dict>,
)

DocumentMetadata(
    *,
    document_id: str,
    original_filename: str,
    content_type: str,
    file_size: int,
    storage_key: str,
    status: DocumentStatus,
    created_at: datetime,
    updated_at: datetime,
    checksum: str | None = None,
    deleted_at: datetime | None = None,
    created_by: str | None = None,
    user_id: str | None = None,
    extra_metadata: Any = <empty dict>,
)
```

- 일반 upload 결과, `get_document_metadata()`, `list_documents()`/`list_documents_page()`는 `PublicDocumentMetadata`를 반환한다.
- `PublicDocumentMetadata`에는 `storage_key`가 구조적으로 없다. `DocumentMetadata`는 storage locator를 포함하므로 명시적인 관리·복구 경계에서만 사용한다.
- `get_internal_document_metadata()`, `list_recovery_candidates()`, `inspect_document()` 및 복구 result의 inspection은 관리 경계다. 내부 모델을 일반 응답, observer event, tenant callback에 그대로 전달하지 않는다.
- `public_metadata(value)`는 `DocumentMetadata`, `PublicDocumentMetadata`, `UploadDocumentResult`를 public-safe projection으로 깊은 복사한다.
- `PublicDocumentMetadata.to_dict()`는 호환 필드명 `extra_metadata`를 유지하고, `to_public_dict()`는 canonical 외부 필드명 `metadata`를 사용한다. `user_id`가 있으면 두 dump에 포함된다.
- `PublicDocumentMetadata`, `UploadDocumentResult`, `DocumentPage`, `DeleteDocumentResult`, `DataResetResult`는 `json_schema()`와 같은 내용을 반환하는 `model_json_schema()`를 제공한다. caller metadata의 내부 구조는 schema에 고정하지 않는다.

### 4.4 상태·본문·stream·page

```text
DocumentStatus.UPLOADED == "uploaded"
DocumentStatus.AVAILABLE == "available"
DocumentStatus.DELETING == "deleting"
DocumentStatus.DELETED == "deleted"
DocumentStatus.FAILED == "failed"

DocumentContent(
    document_id: str,
    content: bytes,
    content_type: str,
    filename: str,
    size: int,
    checksum: str | None = None,
)

DocumentContentStream(
    document_id: str,
    stream: BinaryIO,
    content_type: str,
    filename: str,
    size: int,
    checksum: str | None = None,
    chunk_size: int = 65536,
)

DocumentPage(
    items: list[PublicDocumentMetadata],
    next_cursor: str | None,
    has_more: bool,
)
```

`DocumentContentStream`의 공개 member:

- `iter_chunks(chunk_size: int | None = None) -> Iterator[bytes]`
- `iter_chunks_closing(chunk_size: int | None = None) -> Iterator[bytes]`
- `close() -> None`
- `with stream: ...`

`iter_chunks_closing()`은 정상 소진·read error·iterator의 명시적 close에서 SDK 소유 stream을 정리한다. `close()`와 context-manager 종료는 반복 호출에 안전하다. `copy_document_to()`는 source를 닫고 caller sink는 닫지 않는다.

`AsyncDocumentContentStream`의 공개 member:

- `content_type`, `filename`, `size`, `checksum`, `closed` property
- `iter_chunks(chunk_size: int | None = None) -> AsyncIterator[bytes]`
- `aiter_chunks_closing(chunk_size: int | None = None) -> AsyncIterator[bytes]`
- `await aclose()`
- `async with stream: ...`

async stream의 읽기와 close는 정상 소진·read error·취소·context 종료에서 source를 정리한다. `aclose()`는 반복 호출에 안전하다.

일반 목록은 `created_at`과 immutable `document_id`의 내림차순 복합 순서를 사용한다. `limit`는 1~1000이며 기본값은 100이다. 다음 조회에는 같은 status, page size 및 user scope 조건과 이전 `next_cursor`를 사용해야 한다. cursor는 opaque 값이며 변조·조건 변경·page size 변경·user scope 변경 시 `ValidationError`다. 일반 목록에는 offset API가 없다.

### 4.5 삭제·reset 결과

```text
DeleteDocumentResult(
    document_id: str,
    deleted: bool,
    hard_deleted: bool,
    status: DocumentStatus,
)

DataResetResult(
    metadata_deleted: int,
    objects_deleted: int,
    upload_operations_deleted: int,
    ready_for_data_load: bool = True,
)
```

- `delete_document(..., hard_delete=False)`와 `soft_delete_document()`는 논리 삭제다. `hard_delete_document()` 또는 `hard_delete=True`는 문서 정보까지 제거한다.
- object 삭제 실패는 metadata를 best-effort로 `FAILED`로 바꾼 뒤 `StorageError`를 발생시킬 수 있다. object 삭제 후 metadata 처리가 실패하면 `ConsistencyError`이며 `DELETING` 상태가 남을 수 있다.
- `clear_all_data()`와 `initialize_for_data_load()`는 DMS가 관리하는 metadata, `documents/` prefix object 및 설정된 upload operation record를 대상으로 한다. user scope가 있으면 해당 user 범위만 대상으로 한다.
- 한 store가 실패해도 가능한 다른 store 정리를 계속한다. 부분 실패 시 `DataResetError.result`, `errors`, `failed_stores`를 확인하고 `result.ready_for_data_load`는 `False`다.
- `DataResetResult.total_deleted`, `to_dict()`, `json_schema()`, `model_json_schema()`가 공개된다.

### 4.6 recovery 모델과 method

```text
RecoveryIssue.NONE                 == "none"
RecoveryIssue.METADATA_MISSING     == "metadata_missing"
RecoveryIssue.OBJECT_MISSING       == "object_missing"
RecoveryIssue.DELETION_INCOMPLETE  == "deletion_incomplete"
RecoveryIssue.FAILED_STATUS        == "failed_status"

RecoveryAction.COMPLETE_DELETION_SOFT == "complete_deletion_soft"
RecoveryAction.COMPLETE_DELETION_HARD == "complete_deletion_hard"
RecoveryAction.MARK_FAILED            == "mark_failed"
RecoveryAction.PURGE_ORPHAN_OBJECT    == "purge_orphan_object"

DocumentInspection(
    document_id: str,
    metadata_exists: bool,
    object_exists: bool | None,
    status: DocumentStatus | None,
    consistent: bool,
    issue: RecoveryIssue,
    storage_key: str | None = None,
)

ReconciliationResult(
    document_id: str,
    action: RecoveryAction,
    applied: bool,
    inspection: DocumentInspection | None,
    error_type: str | None = None,
    error_message: str | None = None,
)

BatchReconciliationResult(
    status: DocumentStatus,
    action: RecoveryAction,
    dry_run: bool,
    offset: int,
    limit: int,
    items: list[ReconciliationResult],
)

ReconciliationPlanItem(
    document_id: str,
    action: RecoveryAction,
    storage_key: str | None = None,
)

ReconciliationPlan(
    status: DocumentStatus,
    action: RecoveryAction,
    items: tuple[ReconciliationPlanItem, ...],
)
```

- `inspect_document()`은 metadata가 없을 때 `DocumentNotFoundError` 대신 `metadata_exists=False`, `issue=METADATA_MISSING`인 typed result를 반환한다.
- `list_recovery_candidates()`와 `reconcile_documents()`는 `FAILED` 또는 `DELETING`만 허용하며 recovery `limit`는 1~1000이다.
- `iter_recovery_candidates()`는 offset을 내부에서 유지한다.
- `reconcile_document()`은 action 조건을 재점검하며 `dry_run=True`에서는 상태를 변경하지 않는다.
- `BatchReconciliationResult`는 `scanned`, `failed`, `eligible`, `applied`, `skipped`, `to_plan()`, `to_dict()`를 제공한다. `to_plan()`은 dry-run result에서만 가능하다.
- `execute_reconciliation_plan()`은 실행 직전에 각 item을 다시 검사한다. `PURGE_ORPHAN_OBJECT`는 metadata가 없고 정확한 `storage_key`가 제공된 경우에만 사용할 수 있다.
- `RecoveryAuditEvent.to_dict()`는 각 복구 시도 결과를 전달한다. `recovery_audit_hook` 실패는 복구 결과를 바꾸지 않는다.

### 4.7 capability protocol과 observer

```text
DocumentWriter
  upload_document(request, *, access_context=None) -> UploadDocumentResult
  upload_file(path, *, filename=None, content_type=None,
              document_id=None, metadata=None, created_by=None,
              access_context=None) -> UploadDocumentResult
  upload_document_stream(request, *, access_context=None) -> UploadDocumentResult

DocumentReader
  get_document_metadata(document_id, *, access_context=None) -> PublicDocumentMetadata
  get_document_content(document_id, *, access_context=None) -> DocumentContent
  get_document_content_stream(document_id, *, chunk_size=65536,
                              access_context=None) -> DocumentContentStream
  copy_document_to(document_id, sink, *, chunk_size=65536,
                  verify_checksum=True, access_context=None) -> DocumentCopyResult

DocumentLister
  list_documents(*, cursor=None, limit=100, status=None,
                 access_context=None) -> DocumentPage
  iter_documents(*, status=None, page_size=100,
                 access_context=None) -> Iterator[PublicDocumentMetadata]

DocumentDeleter
  delete_document(document_id, *, hard_delete=False,
                  access_context=None) -> DeleteDocumentResult

DataResetter
  clear_all_data(*, access_context=None) -> DataResetResult
  initialize_for_data_load(*, access_context=None) -> DataResetResult

DocumentManagementClient
  DocumentWriter + DocumentReader + DocumentLister +
  DocumentDeleter + DataResetter
```

`DefaultDocumentManagementSDK`는 위 다섯 capability protocol과 `DocumentManagementClient`를 만족한다. async facade는 별도 async protocol을 export하지 않으며 같은 작업을 awaitable로 제공한다.

```text
DocumentAccessPolicy.allows(
    *,
    operation: str,
    context: AccessContext | None,
    metadata: PublicDocumentMetadata | None,
) -> bool

OperationEvent(
    operation: str,
    succeeded: bool,
    started_at: datetime,
    completed_at: datetime,
    document_id: str | None = None,
    conditions: Mapping[str, object] = {},
    error_code: str | None = None,
)

OperationObserver(event: OperationEvent) -> object

RecoveryAuditEvent(
    document_id: str,
    action: RecoveryAction,
    dry_run: bool,
    succeeded: bool,
    applied: bool,
    occurred_at: datetime,
    actor: str | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
)
```

policy callback에는 public projection만 전달되며 내부 `storage_key`는 전달되지 않는다. observer와 recovery audit callback의 실패는 원래 작업 결과를 덮지 않는다. event 조건에는 본문, credential, 내부 storage locator를 넣지 않는다.

## 5. 오류 모델

모든 공개 SDK 오류는 `DmsError`에서 파생된다. 공통 field는 `code`, `category`, `retryable`, `document_id`, `diagnosis`다. DMS는 HTTP server가 아니므로 HTTP status, response body, retry header는 host transport가 결정한다.

| 오류 | code | category | retryable | caller action |
| --- | --- | --- | :---: | --- |
| `DmsError` | `dms_error` | `internal` | 아니오 | 공통 오류 boundary로 처리한다. |
| `ConfigurationError` | `configuration_invalid` | `configuration` | 아니오 | factory 입력, bucket, dialect를 확인한다. |
| `ValidationError` | `validation_invalid` | `validation` | 아니오 | request, cursor, policy 조건을 수정한다. |
| `AccessDeniedError` | `access_denied` | `access` | 아니오 | host access context/policy를 확인한다. |
| `PayloadTooLargeError` | `document_too_large` | `validation` | 아니오 | max file size 또는 입력을 조정한다. |
| `DocumentNotFoundError` | `document_not_found` | `not_found` | 아니오 | ID 또는 public 은닉 상태를 확인한다. |
| `DocumentDeletedError` | `document_deleted` | `unavailable` | 아니오 | 관리 metadata/recovery 경계를 사용한다. |
| `DuplicateDocumentError` |

..._This content has been truncated to stay below 50000 characters_...