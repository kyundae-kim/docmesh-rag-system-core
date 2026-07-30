---
source_url: https://github.com/kyundae-kim/dms-core/wiki/API-Reference-v0.6.0
ingested: 2026-07-27
sha256: e8dfdc821655a3899253d485d86db5e758c5204bde744a63266839e66a89171f
---
# DMS SDK 공개 API 레퍼런스

이 문서는 `dms` 패키지 루트에서 가져올 수 있는 공개 계약을 설명한다. 공개 범위의 기준은 `dms.__all__`이며, 내부 모듈 경로는 호환성 계약이 아니다.

- 조립과 환경변수: [설정 레퍼런스](config.md)
- 실행 흐름: [사용 예제](examples.md)
- 환경 템플릿: [`.env.example`](../.env.example)

## 공통 계약

- 모든 요청 dataclass는 키워드 인자로 생성한다.
- 일반 문서 정보 API는 저장 위치가 없는 `PublicDocumentMetadata`를 반환한다.
- `DocumentMetadata`와 복구 API는 `storage_key`를 포함할 수 있으므로 관리 경계 밖으로 노출하지 않는다.
- 업로드 입력 stream은 호출자 소유이며 SDK가 닫지 않는다. SDK가 반환한 다운로드 stream은 호출자가 닫는다.
- SDK는 동기·비동기 context manager이며 `close()`와 `aclose()`는 반복 호출해도 안전하다.
- 모든 `DmsError`는 안정적인 `code`, `category`, `retryable`, 선택적 `document_id`와 `diagnosis`를 제공한다.

## SDK 조립 API

### `create_sdk_from_environment(...)`

```python
create_sdk_from_environment(
    *, logger=None, metadata_validator=None,
    metadata_max_serialized_bytes=16_384, metadata_max_depth=8,
    recovery_audit_hook=None,
) -> DefaultDocumentManagementSDK
```

호출 시 프로세스 환경을 읽고 PostgreSQL 또는 SQLite와 MinIO를 조립한다. 선택·검증 규칙은 [설정 레퍼런스](config.md#환경-기반-조립)를 따른다. 조립이나 시작 상태 확인이 실패하면 이미 생성한 자원을 정리한다.

### `create_sdk_from_service_configs(configs, ...)`

```python
create_sdk_from_service_configs(
    configs, *, logger=None, metadata_validator=None,
    metadata_max_serialized_bytes=16_384, metadata_max_depth=8,
    recovery_audit_hook=None, check_on_startup=False,
) -> DefaultDocumentManagementSDK
```

`docmesh_py_core.ServiceConfigs`를 사용하며 프로세스 환경을 다시 읽거나 변경하지 않는다. PostgreSQL과 SQLite 중 정확히 하나와 MinIO 및 bucket이 필요하다. 조립한 client는 SDK가 소유한다.

### `create_sdk_from_clients(...)`

```python
create_sdk_from_clients(
    *, engine, minio_client, bucket_name, logger=None, id_generator=None,
    close_callbacks=None, max_file_size=None, metadata_validator=None,
    metadata_max_serialized_bytes=16_384, metadata_max_depth=8,
    recovery_audit_hook=None,
) -> DefaultDocumentManagementSDK
```

호출자가 만든 SQLAlchemy `Engine`과 MinIO client를 사용한다. engine dialect는 `postgresql` 또는 `sqlite`여야 하고 `bucket_name`은 공백이 아니어야 한다. 주입 client는 기본적으로 호출자 소유이며 SDK 종료와 연결할 작업만 `close_callbacks`에 전달한다.

### `create_sdk_from_components(...)`

```python
create_sdk_from_components(
    *, metadata_store, object_store, logger=None, id_generator=None,
    service_checks=None, close_callbacks=None, max_file_size=None,
    operation_store=None, metadata_validator=None,
    metadata_max_serialized_bytes=16_384, metadata_max_depth=8,
    recovery_audit_hook=None,
) -> DefaultDocumentManagementSDK
```

애플리케이션 구현체를 직접 주입한다. `operation_store=None`이면 멱등성 키 기반 operation 추적을 사용할 수 없다. `metadata_validator`를 주입하면 factory의 기본 metadata 크기·깊이 설정 대신 해당 validator가 사용된다.

### `DefaultDocumentManagementSDK`

위 factory 사용을 권장한다. 직접 생성자는 `metadata_store`, `object_store`를 필수로 받고 `logger`, `id_generator`, `service_checks`, `close_callbacks`, `max_file_size`, `operation_store`, `metadata_validator`, `recovery_audit_hook`를 선택적으로 받는다.

## 문서 작업 API

| 메서드 | 반환값 | 계약 |
| --- | --- | --- |
| `upload_document(request)` | `UploadDocumentResult` | bytes 본문 등록 |
| `upload_document_stream(request)` | `UploadDocumentResult` | 선언 크기의 동기 stream 등록 |
| `upload_document_unknown_size_stream(request)` | `UploadDocumentResult` | `max_size`로 제한한 임시 spool 등록 |
| `await upload_document_async_stream(request)` | `UploadDocumentResult` | 선언 크기의 비동기 stream 등록 |
| `await upload_document_async_unknown_size_stream(request)` | `UploadDocumentResult` | 최대 크기로 제한한 비동기 stream 등록 |
| `get_upload_operation(*, scope, idempotency_key)` | `UploadOperationResult` | 정확한 scope/key의 operation 상태 조회 |
| `get_document_metadata(document_id)` | `PublicDocumentMetadata` | 일반 공개 문서 정보 조회 |
| `get_internal_document_metadata(document_id)` | `DocumentMetadata` | 저장 위치를 포함하는 관리 전용 조회 |
| `list_documents(*, cursor=None, limit=100, status=None)` | `DocumentPage` | 기본 커서 목록 API |
| `list_documents_page(*, cursor=None, limit=100, status=None)` | `DocumentPage` | 위와 같은 명시적 page API |
| `get_document_content(document_id)` | `DocumentContent` | 전체 본문을 메모리에 적재 |
| `get_document_content_stream(document_id, *, chunk_size=65536)` | `DocumentContentStream` | 동기 다운로드 stream |
| `await get_document_content_async_stream(document_id, *, chunk_size=65536)` | `AsyncDocumentContentStream` | 비동기 다운로드 stream |
| `delete_document(document_id, *, hard_delete=False)` | `DeleteDocumentResult` | 기본은 논리 삭제 |
| `soft_delete_document(document_id)` | `DeleteDocumentResult` | 논리 삭제 편의 메서드 |
| `hard_delete_document(document_id)` | `DeleteDocumentResult` | 영구 삭제 편의 메서드 |
| `check_health()` | `HealthStatus` | 현재 의존성 상태 확인 |
| `close()` / `await aclose()` | `None` | SDK 소유 자원 정리 |
| `__enter__()` / `__exit__()` | SDK / `None` | `with sdk` 동기 lifecycle |
| `__aenter__()` / `__aexit__()` | SDK / `None` | `async with sdk` 비동기 lifecycle |

### 업로드 검증과 멱등성

- filename과 content type은 비어 있지 않아야 하며 크기와 chunk 크기는 양수여야 한다.
- 알려진 크기 stream은 실제 읽은 byte 수가 선언값과 일치해야 한다.
- checksum을 제공하면 실제 SHA-256과 일치해야 한다.
- `max_file_size` 또는 unknown-size 요청의 `max_size`를 넘으면 `PayloadTooLargeError`다.
- `idempotency_key`를 사용하면 명시적 `idempotency_scope`가 필요하다.
- 동일 scope/key와 같은 요청의 재실행은 기존 결과와 `created=False`를 반환한다. 다른 요청이면 `IdempotencyConflictError`, 진행 중이면 `IdempotencyInProgressError`다.
- bytes, 동기 stream, 비동기 stream은 같은 metadata 정규화·검증 정책을 사용한다.

### 공개 조회와 페이지네이션

일반 단건·목록 조회는 `DELETED`와 `DELETING` 상태를 숨긴다. 삭제된 본문 조회는 `DocumentDeletedError`다. `DocumentPage`는 `items`, `next_cursor`, `has_more`를 가지며 이전 반복 사용을 위해 iterable이다.

커서는 불투명하며 정렬 조건, 상태 필터, page 크기에 결합된다. 다음 page에서도 같은 `status`와 `limit`을 사용해야 한다. 변조되거나 다른 조건에 재사용한 커서는 `ValidationError`다. 일반 목록은 offset을 지원하지 않는다.

### stream lifecycle

`DocumentContentStream`은 `iter_chunks()`, `close()`와 동기 context manager를 제공한다. `AsyncDocumentContentStream`은 `iter_chunks()`, `aclose()`, `closed`와 비동기 context manager를 제공한다. 비동기 반복은 완료·오류·취소 시 다운로드 자원을 정리한다. 비동기 열기는 먼저 await해야 한다.

## 요청·결과 모델

| 공개 모델 | 공개 필드 또는 동작 |
| --- | --- |
| `UploadDocumentRequest` | `content`, `filename`, `content_type`, `document_id`, `metadata`, `created_by`, `checksum`, `idempotency_key`, `idempotency_scope` |
| `UploadDocumentStreamRequest` | `stream`, `size`, `filename`, `content_type`, `document_id`, `metadata`, `created_by`, `checksum`, `chunk_size`, `idempotency_key`, `idempotency_scope` |
| `UploadDocumentUnknownSizeStreamRequest` | `stream`, `max_size`, `filename`, `content_type`, `document_id`, `metadata`, `created_by`, `chunk_size`, `idempotency_key`, `idempotency_scope` |
| `AsyncUploadDocumentStreamRequest` | known-size 요청과 같고 async `read()` stream 사용 |
| `AsyncUploadDocumentUnknownSizeStreamRequest` | unknown-size 요청과 같고 async `read()` stream 사용 |
| `UploadDocumentResult` | `document_id`, `metadata`, `created` |
| `UploadOperationResult` | `scope`, `idempotency_key`, `document_id`, `state`, `created_at`, `updated_at` |
| `PublicDocumentMetadata` | `document_id`, `original_filename`, `content_type`, `file_size`, `status`, `created_at`, `updated_at`, `checksum`, `deleted_at`, `created_by`, `extra_metadata`; `to_dict()` |
| `DocumentMetadata` | 공개 문서 정보 필드와 관리 전용 `storage_key` |
| `DocumentContent` | `document_id`, `content`, `content_type`, `filename`, `size`, `checksum` |
| `DocumentContentStream` | 문서·본문 정보, `iter_chunks()`, `close()` |
| `AsyncDocumentContentStream` | 문서·본문 property, `iter_chunks()`, `aclose()`, `closed` |
| `DocumentPage` | `items`, `next_cursor`, `has_more` |
| `DeleteDocumentResult` | `document_id`, `deleted`, `hard_deleted`, `status`; `to_dict()` |
| `ServiceHealth` | `service`, `ok`, `latency_ms`, `error` |
| `HealthStatus` | `ok`, `services`, `checked_at` |

`PublicDocumentMetadata.to_dict()`는 enum을 문자열 값으로, 날짜·시각을 timezone이 포함된 ISO 8601 문자열로 변환한다. `extra_metadata`는 문자열 key와 JSON 호환 값만 포함해야 한다. `public_metadata(value)`는 `DocumentMetadata`, `PublicDocumentMetadata`, `UploadDocumentResult`를 public-safe 복사본으로 변환한다.

`DocumentStatus` 값은 `uploaded`, `available`, `deleting`, `deleted`, `failed`다. `UploadOperationResult.state` 값은 `pending`, `succeeded`, `failed`지만 해당 enum 타입 자체는 package root export가 아니다.

## Metadata 검증 API

| 공개 이름 | 계약 |
| --- | --- |
| `MetadataValidator` | `Mapping[str, Any]`를 받아 정규화된 새 `dict`를 반환하는 callable protocol |
| `MetadataNormalizer` | 같은 callable의 공개 type alias |
| `DefaultMetadataPolicy` | JSON 호환성, 문자열 key, 깊이, UTF-8 직렬화 크기, 금지 key를 검증 |
| `StructuredMetadataValidator` | schema version 확인 → parser → 선택적 projector → 후속 policy 순서로 처리 |
| `MetadataValidationIssue` | `path`, `code`, `message` 구조의 문제 한 건 |
| `MetadataSchemaValidationError` | `ValidationError` 하위 오류이며 immutable `issues` tuple 제공 |

기본 policy는 `max_serialized_bytes=16_384`, `max_depth=8`이다. 금지 key는 대소문자를 구분하지 않고 중첩 mapping/list에도 적용한다. 입력 mapping은 변경하지 않는다.

## 복구 API

| 메서드 | 반환값 | 계약 |
| --- | --- | --- |
| `inspect_document(document_id)` | `DocumentInspection` | 문서 정보 부재도 예외가 아닌 검사 결과 |
| `list_recovery_candidates(*, status, offset=0, limit=100)` | `list[DocumentMetadata]` | `FAILED` 또는 `DELETING`만 허용, 관리 정보 포함 |
| `reconcile_document(document_id, action, *, storage_key=None, dry_run=False, actor=None)` | `ReconciliationResult` | 단건 복구 또는 dry-run |
| `reconcile_documents(*, status, action, offset=0, limit=100, dry_run=False, actor=None)` | `BatchReconciliationResult` | 항목별 실패를 결과에 보존하고 계속 진행 |
| `execute_reconciliation_plan(plan, *, actor=None)` | `BatchReconciliationResult` | 각 항목을 다시 검사한 뒤 실행 |

복구 목록의 `offset`은 0 이상, `limit`은 1~1000이어야 한다.

| 공개 모델·enum | 계약 |
| --- | --- |
| `RecoveryIssue` | `none`, `metadata_missing`, `object_missing`, `deletion_incomplete`, `failed_status` |
| `RecoveryAction` | `complete_deletion_soft`, `complete_deletion_hard`, `mark_failed`, `purge_orphan_object` |
| `DocumentInspection` | 존재 여부, 상태, 일관성, issue, 선택적 `storage_key` |
| `ReconciliationResult` | action, 적용 여부, 재검사 결과, 항목별 오류 |
| `BatchReconciliationResult` | items와 `scanned`, `failed`, `eligible`, `applied`, `skipped`; dry-run 결과의 `to_plan()` |
| `ReconciliationPlanItem` | document ID, action, orphan용 선택적 storage key |
| `ReconciliationPlan` | status, action, immutable items; 모든 item action이 같아야 함 |
| `RecoveryAuditEvent` | action, dry-run·성공·적용 여부, UTC 시각, actor, 선택적 오류 |

`to_plan()`은 dry-run batch에서만 가능하다. 계획 실행은 오래된 결과를 그대로 신뢰하지 않는다. `recovery_audit_hook`은 best-effort이며 hook 오류가 본 작업 결과를 뒤집지 않는다.

## 환경 진단 API

`diagnose_environment(env=None)`는 연결 없이 환경 mapping을 진단하여 `EnvironmentDiagnosis`를 반환한다. 필드는 `metadata_backend`, `object_backend`, `healthcheck_enabled`, `missing_required_keys`, `warnings`, `unsupported_keys`, `valid`다. `format_environment_diagnosis()`는 같은 결과를 민감정보 없는 운영자용 문자열로 만든다. 자세한 선택 규칙은 [설정 레퍼런스](config.md)에 있다.

## 오류 계층과 권장 HTTP 변환

| 오류 | code | category | 재시도 | 권장 HTTP |
| --- | --- | --- | --- | --- |
| `DmsError` | `dms_error` | `internal` | 아니요 | 500 |
| `ConfigurationError` | `configuration_invalid` | `configuration` | 아니요 | 500 |
| `ValidationError` | `validation_invalid` | `validation` | 아니요 | 400 |
| `MetadataSchemaValidationError` | `metadata_schema_invalid` | `validation` | 아니요 | 400 |
| `PayloadTooLargeError` | `document_too_large` | `validation` | 아니요 | 413 |
| `DocumentNotFoundError` | `document_not_found` | `not_found` | 아니요 | 404 |
| `UploadOperationNotFoundError` | `upload_operation_not_found` | `not_found` | 아니요 | 404 |
| `DocumentDeletedError` | `document_deleted` | `unavailable` | 아니요 | 409 |
| `DuplicateDocumentError` | `document_duplicate` | `conflict` | 아니요 | 409 |
| `IdempotencyConflictError` | `idempotency_conflict` | `conflict` | 아니요 | 409 |
| `IdempotencyInProgressError` | `idempotency_in_progress` | `conflict` | 예 | 425 |
| `StorageError` | `object_storage_failed` | `storage` | 예 | 503 |
| `MetadataStoreError` | `metadata_store_failed` | `storage` | 예 | 503 |
| `HealthCheckFailedError` | `startup_health_failed` | `health` | 예 | 503 |
| `ConsistencyError` | `document_inconsistent` | `consistency` | 아니요 | 500 |

`recommended_http_error(error)`는 `RecommendedHttpError(status, body)`를 반환한다. body는 `code`, `category`, `retryable`, `message`를 포함한다. 이 기능은 호스트 전송 계층을 위한 권고이며 예외 자체에 HTTP 속성을 추가하지 않는다. 설정·저장소·상태 확인·일관성 오류의 외부 메시지는 내부 연결 정보가 없는 고정 문구로 바뀐다.

## 공개 export 추적표

아래 표는 `dms.__all__` 전체를 문서 절과 연결한다.

| 영역 | 공개 export | 상세 절 | 예제 |
| --- | --- | --- | --- |
| SDK·조립 | `DefaultDocumentManagementSDK`, `create_sdk_from_environment`, `create_sdk_from_service_configs`, `create_sdk_from_clients`, `create_sdk_from_components` | [SDK 조립 API](#sdk-조립-api) | [1, 2, 3](examples.md) |
| 환경 진단 | `EnvironmentDiagnosis`, `diagnose_environment`, `format_environment_diagnosis` | [환경 진단 API](#환경-진단-api) | [4](examples.md) |
| 업로드 | `UploadDocumentRequest`, `UploadDocumentStreamRequest`, `UploadDocumentUnknownSizeStreamRequest`, `AsyncUploadDocumentStreamRequest`, `AsyncUploadDocumentUnknownSizeStreamRequest`, `UploadDocumentResult`, `UploadOperationResult` | [문서 작업 API](#문서-작업-api) | [5, 6, 7](examples.md) |
| 조회·삭제 | `PublicDocumentMetadata`, `DocumentMetadata`, `public_metadata`, `DocumentContent`, `DocumentContentStream`, `AsyncDocumentContentStream`, `DocumentPage`, `DeleteDocumentResult`, `DocumentStatus` | [요청·결과 모델](#요청결과-모델) | [8, 9, 10](examples.md) |
| Metadata | `MetadataValidator`, `MetadataNormalizer`, `DefaultMetadataPolicy`, `StructuredMetadataValidator`, `MetadataValidationIssue`, `MetadataSchemaValidationError` | [Metadata 검증 API](#metadata-검증-api) | [11](examples.md) |
| 복구 | `RecoveryIssue`, `RecoveryAction`, `DocumentInspection`, `ReconciliationResult`, `BatchReconciliationResult`, `ReconciliationPlanItem`, `ReconciliationPlan`, `RecoveryAuditEvent` | [복구 API](#복구-api) | [12](examples.md) |
| 상태 확인 | `ServiceHealth`, `HealthStatus` | [요청·결과 모델](#요청결과-모델) | [13](examples.md) |
| HTTP | `RecommendedHttpError`, `recommended_http_error` | [오류 계층과 권장 HTTP 변환](#오류-계층과-권장-http-변환) | [14](examples.md) |
| 오류 | `DmsError`, `ConfigurationError`, `ValidationError`, `MetadataSchemaValidationError`, `PayloadTooLargeError`, `DocumentNotFoundError`, `UploadOperationNotFoundError`, `DocumentDeletedError`, `DuplicateDocumentError`, `IdempotencyConflictError`, `IdempotencyInProgressError`, `StorageError`, `MetadataStoreError`, `HealthCheckFailedError`, `ConsistencyError` | [오류 계층과 권장 HTTP 변환](#오류-계층과-권장-http-변환) | [14](examples.md) |
