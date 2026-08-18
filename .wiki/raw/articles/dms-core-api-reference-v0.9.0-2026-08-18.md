---
source_url: https://github.com/kyundae-kim/dms-core/wiki/API-Reference-v0.9.0
ingested: 2026-08-18
sha256: 8d6e76d528d5ee595af0532a3cf52cb43a1d248088ff56b1a10a1dcc0c5729e5
---
# DMS SDK 공개 API 레퍼런스 (v0.9.0)

- 기준 버전: `0.9.0`
- 기준 소스: `dms-core` commit `f7a40f1` (`develop-v0.8.0`, `pyproject.toml` 버전 `0.9.0`)
- 대상: 다른 Python 애플리케이션에서 `import`하여 사용하는 SDK
- 권장 import 경계: `dms` package root
- 사용 예제: [Examples-v0.9.0](Examples-v0.9.0.md)
- 추적 규칙: `source path:line`, `test path::test_function`, `E-xx` 예제 anchor

이 문서는 현재 checkout의 `dms.__all__` 54개 이름과 공개 facade의 모든 작업 method를 기준으로 작성했다. 각 공개 이름과 작업은 이 문서의 [추적성 매트릭스](#10-추적성-매트릭스)에서 실제 source, 실행 test, 예제 anchor로 연결한다. 이전 Wiki 페이지는 과거 release 기록으로 보존하며, 현재 코드에는 이 문서의 버전과 signature를 적용한다.

> **중요한 경계**
>
> DMS는 독립 실행형 API 서버가 아니라 host 애플리케이션에 주입되어 사용되는 Python SDK다. SQLAlchemy `Engine`, MinIO client, storage component의 생성·readiness·종료는 host가 담당한다. SDK facade에는 전역 `close()`, `aclose()`, `check_health()`가 없다.

## 1. 공개 import 경계

소비 프로젝트는 기본적으로 다음 경계에서 import한다.

```python
from dms import DocumentManagementSDKFactory, UploadDocumentRequest
```

`dms.sdk`도 같은 공개 이름을 재-export하지만, 안정적인 소비자 계약은 `from dms import ...`다. `dms.__all__`은 `dms.sdk.__all__` 전체와 `DocumentStatus`를 합성한다. 기준 checkout에서 `dms.sdk.__all__`은 53개, `dms.__all__`은 54개다.

### 1.1 package root 공개 이름 전체

아래 이름은 모두 `from dms import ...`로 접근할 수 있다. 종류와 상세 설명은 다음 절 및 추적성 매트릭스와 함께 읽는다.

#### 조립·정책·관찰

| 공개 이름 | 종류 | 설명 | 추적 ID |
| --- | --- | --- | --- |
| `DocumentManagementSDKFactory` | dataclass factory | host client에서 SDK를 조립한다. | `TR-ASM` |
| `DefaultDocumentManagementSDK` | sync facade | 동기 문서 관리 작업을 제공한다. | `TR-ASM` |
| `AsyncDocumentManagementSDK` | async facade | 동기 구현을 event loop 밖에서 실행하는 awaitable facade다. | `TR-ASYNC` |
| `ScopedDocumentManagementSDK` | sync scoped facade | `DmsOperationContext` 기본값을 작업 범위에 적용한다. | `TR-POLICY` |
| `AsyncScopedDocumentManagementSDK` | async scoped facade | scoped facade의 awaitable adapter다. | `TR-ASYNC` |
| `AccessContext` | immutable dataclass | host 권한 판단에 필요한 주체·tenant·role context다. | `TR-POLICY` |
| `DmsOperationContext` | immutable dataclass | access, 작성자, 멱등성 범위, audit actor, 기본 metadata를 묶는다. | `TR-POLICY` |
| `DocumentAccessPolicy` | protocol | host가 작업 허용 여부를 결정하는 callback 계약이다. | `TR-POLICY` |
| `OperationEvent` | immutable dataclass | 작업 성공·실패 observer event다. | `TR-OBS` |
| `OperationObserver` | protocol | `OperationEvent`를 받는 callback 계약이다. | `TR-OBS` |

#### 기능별 protocol과 결과

| 공개 이름 | 종류 | 설명 | 추적 ID |
| --- | --- | --- | --- |
| `DocumentWriter` | runtime-checkable protocol | upload capability 계약이다. | `TR-CONTRACT` |
| `DocumentReader` | runtime-checkable protocol | metadata/content/copy capability 계약이다. | `TR-CONTRACT` |
| `DocumentLister` | runtime-checkable protocol | cursor 목록과 iterator capability 계약이다. | `TR-CONTRACT` |
| `DocumentDeleter` | runtime-checkable protocol | 문서 삭제 capability 계약이다. | `TR-CONTRACT` |
| `DataResetter` | runtime-checkable protocol | DMS 관리 범위 전체 reset capability 계약이다. | `TR-CONTRACT` |
| `DocumentManagementClient` | 조합 protocol | writer, reader, lister, deleter, resetter를 합친 계약이다. | `TR-CONTRACT` |
| `DocumentCopyResult` | immutable dataclass | content를 caller sink로 복사한 결과다. | `TR-READ` |

#### 업로드·본문·문서 정보

| 공개 이름 | 종류 | 설명 | 추적 ID |
| --- | --- | --- | --- |
| `UploadDocumentRequest` | dataclass | bytes upload 입력이다. | `TR-UPL` |
| `UploadDocumentStreamRequest` | dataclass | 정확한 크기를 선언한 동기 binary stream 입력이다. | `TR-UPL` |
| `UploadDocumentResult` | dataclass | upload된 document id와 public metadata다. | `TR-UPL` |
| `UploadOperationResult` | dataclass | 멱등성 operation 상태다. | `TR-UPL` |
| `PublicDocumentMetadata` | immutable dataclass | `storage_key`를 제외한 public-safe 문서 정보다. | `TR-DATA` |
| `DocumentMetadata` | dataclass | 관리·복구에 사용하는 storage-bearing 문서 정보다. | `TR-DATA` |
| `DocumentStatus` | `StrEnum` | 문서 lifecycle 상태다. | `TR-DATA` |
| `DocumentContent` | dataclass | 본문 전체를 bytes로 반환하는 결과다. | `TR-READ` |
| `DocumentContentStream` | dataclass | 동기 본문 stream과 close 계약이다. | `TR-READ` |
| `AsyncDocumentContentStream` | dataclass | 비동기 본문 stream과 close 계약이다. | `TR-ASYNC` |
| `DocumentPage` | dataclass | cursor 기반 목록 page다. | `TR-READ` |
| `public_metadata` | function | 관리 모델을 public-safe metadata로 projection한다. | `TR-DATA` |

#### 삭제·초기화·복구

| 공개 이름 | 종류 | 설명 | 추적 ID |
| --- | --- | --- | --- |
| `DeleteDocumentResult` | dataclass | soft/hard delete 결과다. | `TR-DEL` |
| `DataResetResult` | immutable dataclass | 전체 reset에서 store별 삭제 건수다. | `TR-RESET` |
| `DocumentInspection` | dataclass | metadata/object 정합성 점검 결과다. | `TR-REC` |
| `RecoveryIssue` | `StrEnum` | 정합성 문제 종류다. | `TR-REC` |
| `RecoveryAction` | `StrEnum` | 복구 적용 작업 종류다. | `TR-REC` |
| `ReconciliationResult` | dataclass | 한 document 복구 결과다. | `TR-REC` |
| `BatchReconciliationResult` | dataclass | 범위 복구의 항목별 결과와 요약이다. | `TR-REC` |
| `ReconciliationPlanItem` | immutable dataclass | 복구 계획의 한 항목이다. | `TR-REC` |
| `ReconciliationPlan` | immutable dataclass | dry-run에서 만든 실행 계획이다. | `TR-REC` |
| `RecoveryAuditEvent` | immutable dataclass | 복구 시도별 best-effort audit event다. | `TR-OBS` |

#### 오류

| 공개 이름 | 종류 | 설명 | 추적 ID |
| --- | --- | --- | --- |
| `DmsError` | base exception | 모든 공개 SDK 오류의 base다. | `TR-ERR` |
| `ConfigurationError` | exception | factory 설정·dialect 오류다. | `TR-ERR` |
| `ValidationError` | exception | 입력·cursor·복구 조건 오류다. | `TR-ERR` |
| `AccessDeniedError` | exception | host access policy 거부다. | `TR-ERR` |
| `PayloadTooLargeError` | exception | `max_file_size` 초과다. | `TR-ERR` |
| `DocumentNotFoundError` | exception | 문서가 없거나 public 조회에서 숨겨졌다. | `TR-ERR` |
| `DocumentDeletedError` | exception | 삭제 상태 본문을 조회했다. | `TR-ERR` |
| `DuplicateDocumentError` | exception | document id가 이미 존재한다. | `TR-ERR` |
| `IdempotencyConflictError` | exception | 같은 scope/key를 다른 요청 fingerprint로 재사용했다. | `TR-ERR` |
| `IdempotencyInProgressError` | exception | 같은 멱등성 operation이 아직 처리 중이다. | `TR-ERR` |
| `UploadOperationNotFoundError` | exception | scope/key operation 기록을 찾지 못했다. | `TR-ERR` |
| `StorageError` | exception | object storage 작업이 실패했다. | `TR-ERR` |
| `MetadataStoreError` | exception | metadata store 작업이 실패했다. | `TR-ERR` |
| `ConsistencyError` | exception | metadata와 object 상태가 정합하지 않다. | `TR-ERR` |
| `DataResetError` | exception | 전체 reset이 일부 store에서 실패했다. | `TR-ERR` |

### 1.2 공개하지 않는 이름과 기능

다음 항목은 현재 `dms` package root 공개 API가 아니다.

- 환경변수에서 client를 생성하는 factory 및 environment diagnosis API
- `MetadataStore`, `ObjectStore`, `UploadOperationStore`의 내부 port/adapter 구현
- `UploadOperationState` 및 내부 domain persistence 모델
- DMS가 자체 관리하는 인증·권한 정책 저장소
- `HealthStatus`, `ServiceHealth`, `check_health()` 및 readiness endpoint
- SDK 전역 resource `close()`/`aclose()` lifecycle
- HTTP error response/descriptor 모델
- 검색·일반 metadata filtering, presigned URL, message broker API
- unknown-size 또는 async input stream 직접 upload

기존 release 페이지에 남아 있는 이러한 이름을 현재 코드의 호환 API로 간주하지 않는다.

## 2. 조립 API와 소유권

### 2.1 `DocumentManagementSDKFactory`

`DocumentManagementSDKFactory`는 호출자가 이미 만든 SQLAlchemy `Engine`과 MinIO client를 storage adapter에 연결한다.

```python
from dms import DocumentManagementSDKFactory

factory = DocumentManagementSDKFactory(
    engine=application.sqlalchemy_engine,
    minio_client=application.minio_client,
    bucket_name="documents",
    max_file_size=25 * 1024 * 1024,
    recovery_audit_hook=application.record_recovery_audit,
    operation_observer=application.observe_dms_operation,
    access_policy=application.document_access_policy,
)

sdk = factory.create()
async_sdk = factory.create_async()
```

생성자 공개 signature:

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
```

| 입력 | 기본값 | 계약 |
| --- | --- | --- |
| `engine` | 필수 | SQLAlchemy `Engine`; `postgresql` 또는 `sqlite` dialect를 지원한다. |
| `minio_client` | 필수 | host가 생성한 MinIO client다. SDK가 생성하지 않는다. |
| `bucket_name` | 필수 | 공백을 제거한 값이 비어 있지 않아야 한다. |
| `logger` | `None` | 생략하면 `dms.sdk` logger를 사용한다. |
| `max_file_size` | `None` | bytes/file/known-size stream에 적용되는 양수 bytes 한도다. |
| `recovery_audit_hook` | `None` | `RecoveryAuditEvent`를 받는 callback이다. callback 실패는 복구 작업을 실패시키지 않는다. |
| `operation_observer` | `None` | `OperationEvent`를 받는 callback이다. callback 실패는 원래 작업 결과를 바꾸지 않는다. |
| `access_policy` | `None` | host authorization callback이다. 생략하면 access 제한을 적용하지 않는다. |

공개 method:

```text
factory.create() -> DefaultDocumentManagementSDK
factory.create_async() -> AsyncDocumentManagementSDK
```

- `create()`는 dialect에 따라 PostgreSQL 또는 SQLite metadata adapter를 선택하고 MinIO object adapter와 SQLAlchemy upload operation store를 조립한다.
- 지원하지 않는 dialect는 `ConfigurationError`다.
- 빈 `bucket_name`은 factory 생성 시 `ConfigurationError`다.
- factory의 `max_file_size <= 0`은 `ValueError`다.
- `create_async()`는 새 sync SDK를 만든 후 `AsyncDocumentManagementSDK`로 감싼다.
- factory가 만든 adapter와 주입 client는 SDK가 닫지 않는다.

### 2.2 `DefaultDocumentManagementSDK` 직접 조립

host가 이미 준비한 storage component를 직접 전달할 때 사용한다.

```python
from dms import DefaultDocumentManagementSDK

sdk = DefaultDocumentManagementSDK(
    metadata_store=application.metadata_store,
    object_store=application.object_store,
    max_file_size=25 * 1024 * 1024,
    operation_store=application.upload_operation_store,
    recovery_audit_hook=application.record_recovery_audit,
    operation_observer=application.observe_dms_operation,
    access_policy=application.document_access_policy,
)
```

생성자 공개 signature:

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

`MetadataStore`, `ObjectStore`, `UploadOperationStore`는 현재 package root에서 export하지 않는 구조적 component 계약이다. host는 기존 adapter 또는 자체 adapter를 전달할 수 있지만, 해당 객체의 생성·readiness·종료는 host가 관리해야 한다. `operation_store`를 생략하면 idempotency key upload와 upload operation 조회는 사용할 수 없다. 직접 생성에서 `max_file_size <= 0`은 `ValidationError`다.

### 2.3 facade 생성과 lifecycle

```python
from dms import DmsOperationContext

scoped = sdk.scoped(
    DmsOperationContext(
        created_by="batch-worker",
        idempotency_scope="tenant-a",
        audit_actor="batch-worker",
        default_metadata={"source": "batch"},
    )
)

async_scoped = async_sdk.scoped(
    DmsOperationContext(idempotency_scope="tenant-a")
)
```

- `DefaultDocumentManagementSDK.scoped(context)`는 `ScopedDocumentManagementSDK`를 반환한다.
- `AsyncDocumentManagementSDK.scoped(context)`는 `AsyncScopedDocumentManagementSDK`를 반환한다.
- scoped facade는 shared SDK를 변경하지 않는 immutable operation context 경계다.
- SDK가 전역 client lifecycle을 소유하지 않으므로 `sdk.close()`, `sdk.aclose()`, `async_sdk.close()`를 호출하지 않는다.
- SDK가 upload 중 직접 연 파일과 SDK가 반환한 content stream은 SDK가 닫는다. caller가 제공한 upload input stream과 copy sink는 caller가 닫는다.

## 3. Facade method 전체 coverage

공개 facade는 아래 26개 작업 이름을 제공한다. 기본 sync facade를 기준으로 signature를 설명하며, async facade는 `async def`와 동일한 결과 타입의 awaitable을 제공한다. `iter_*`는 sync iterator/async iterator다.

| 작업 | 기본 sync | 기본 async | scoped sync | scoped async | 결과 |
| --- | --- | --- | --- | --- | --- |
| `scoped` | context → scoped | context → async scoped | - | - | facade |
| `upload_document` | sync | await | sync | await | `UploadDocumentResult` |
| `upload_file` | sync | await | sync | await | `UploadDocumentResult` |
| `upload_document_stream` | sync | await | sync | await | `UploadDocumentResult` |
| `get_upload_operation` | sync | await | sync | await | `UploadOperationResult` |
| `get_internal_document_metadata` | sync | await | sync | await | `DocumentMetadata` |
| `get_document_metadata` | sync | await | sync | await | `PublicDocumentMetadata` |
| `list_documents` | sync | await | sync | await | `DocumentPage` |
| `list_documents_page` | sync | await | sync | await | `DocumentPage` |
| `iter_documents` | iterator | async iterator | iterator | async iterator | metadata items |
| `inspect_document` | sync | await | sync | await | `DocumentInspection` |
| `list_recovery_candidates` | sync | await | sync | await | `list[DocumentMetadata]` |
| `iter_recovery_candidates` | iterator | async iterator | iterator | async iterator | metadata items |
| `reconcile_document` | sync | await | sync | await | `ReconciliationResult` |
| `execute_reconciliation_plan` | sync | await | sync | await | `BatchReconciliationResult` |
| `reconcile_documents` | sync | await | sync | await | `BatchReconciliationResult` |
| `get_document_content` | sync | await | sync | await | `DocumentContent` |
| `get_document_content_stream` | sync stream | await async stream | sync stream | await async stream | content stream |
| `get_document_content_async_stream` | await | await | await | await | `AsyncDocumentContentStream` |
| `iter_document_chunks` | iterator | async iterator | iterator | async iterator | `bytes` |
| `copy_document_to` | sync | await | sync | await | `DocumentCopyResult` |
| `delete_document` | sync | await | sync | await | `DeleteDocumentResult` |
| `soft_delete_document` | sync | await | sync | await | `DeleteDocumentResult` |
| `hard_delete_document` | sync | await | sync | await | `DeleteDocumentResult` |
| `clear_all_data` | sync | await | sync | await | `DataResetResult` |
| `initialize_for_data_load` | sync | await | sync | await | `DataResetResult` |

기본 sync facade의 상세 signature:

```text
sdk.upload_document(request: UploadDocumentRequest) -> UploadDocumentResult
sdk.upload_file(
    path: str | Path,
    *,
    filename: str | None = None,
    content_type: str | None = None,
    document_id: str | None = None,
    metadata: object = None,
    created_by: str | None = None,
) -> UploadDocumentResult
sdk.upload_document_stream(request: UploadDocumentStreamRequest) -> UploadDocumentResult
sdk.get_upload_operation(*, scope: str, idempotency_key: str) -> UploadOperationResult

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
    document_id: str,
    action: RecoveryAction,
    *,
    storage_key: str | None = None,
    dry_run: bool = False,
    actor: str | None = None,
    access_context: AccessContext | None = None,
) -> ReconciliationResult
sdk.execute_reconciliation_plan(
    plan: ReconciliationPlan,
    *, actor: str | None = None,
    access_context: AccessContext | None = None,
) -> BatchReconciliationResult
sdk.reconcile_documents(
    *,
    status: DocumentStatus,
    action: RecoveryAction,
    offset: int = 0,
    limit: int = 100,
    dry_run: bool = False,
    actor: str | None = None,
    access_context: AccessContext | None = None,
) -> BatchReconciliationResult

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
```

### 3.1 async facade 규칙

`AsyncDocumentManagementSDK`는 `get_document_content_async_stream()`을 제외한 sync 작업을 worker thread에서 실행하고 결과를 awaitable로 반환한다. `get_document_content_async_stream()`은 sync facade에도 존재하는 명시적 async stream 경계다.

```python
async def read_one(async_sdk, document_id: str) -> bytes:
    content = await async_sdk.get_document_content_stream(document_id)
    received = bytearray()
    async with content:
        async for chunk in content.iter_chunks():
            received.extend(chunk)
    return bytes(received)
```

- `async for`는 `iter_documents`, `iter_recovery_candidates`, `iter_document_chunks`에 사용한다.
- `await async_sdk.get_document_content_stream(...)`와 `await async_sdk.get_document_content_async_stream(...)`은 `AsyncDocumentContentStream`을 반환한다.
- 취소된 상태 변경 작업은 이미 시작한 worker가 안전한 완료 경계에 도달한 뒤 `CancelledError`를 전달할 수 있다. 취소를 rollback 완료로 간주하지 말고 metadata 또는 operation 상태를 확인한다.
- async facade 자체도 engine, MinIO client, component lifecycle을 소유하지 않는다.

### 3.2 scoped facade 규칙

`ScopedDocumentManagementSDK`와 `AsyncScopedDocumentManagementSDK`는 다음 값을 `DmsOperationContext`에서 기본값으로 사용한다.

- `access`: 모든 access-aware 작업의 `access_context`
- `created_by`: upload request의 `created_by`
- `default_metadata`: upload request의 `metadata`
- `idempotency_scope`: upload request와 operation 조회의 scope
- `audit_actor`: recovery 작업의 `actor`

작업에 명시한 값이 context 기본값보다 우선한다. `get_upload_operation(*, idempotency_key, scope=None)`에서 scope를 생략하면 context의 `idempotency_scope`를 사용하며, 둘 다 없으면 `ValidationError`다. scoped facade에는 lifecycle method가 없다.

## 4. upload 입력·결과

### 4.1 bytes와 known-size stream request

```text
UploadDocumentRequest(
    *,
    content: bytes,
    filename: str,
    content_type: str,
    document_id: str | None = None,
    metadata: object = None,
    created_by: str | None = None,
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
    metadata: object = None,
    created_by: str | None = None,
)
```

- bytes upload의 content는 비어 있지 않아야 한다.
- filename과 content type은 비어 있지 않아야 하며 선택 문자열도 지정하면 비어 있지 않아야 한다.
- `document_id`를 생략하면 metadata store가 식별자를 할당하고 결과에 반환한다.
- stream upload는 정확한 양의 `size`와 `read()`를 가진 동기 binary stream이 필요하다. 실제 읽은 크기가 선언값과 다르면 object를 정리한 뒤 `ValidationError`를 발생시킨다.
- SDK가 직접 연 file path는 SDK가 열고 닫는다. caller가 제공한 input stream은 SDK가 닫지 않는다.
- `max_file_size`를 초과하면 `PayloadTooLargeError`다.
- unknown-size stream, async input stream, request별 max size, request별 chunk size는 현재 공개 API가 아니다.

### 4.2 application-owned metadata

`UploadDocumentRequest.metadata`, `UploadDocumentStreamRequest.metadata`, `upload_file(..., metadata=...)`, `DmsOperationContext.default_metadata`의 타입은 `object`다.

- DMS는 metadata의 업무 schema, 보안 규칙, 정규화, JSON 직렬화를 정의하거나 검증하지 않는다.
- 문자열·list·mapping·사용자 객체 등 application-owned 값을 문서 정보와 연결해 보존할 수 있다.
- metadata를 외부 응답이나 메시지로 직렬화할 때의 안전성·형식·secret 포함 여부는 caller 책임이다.
- metadata는 upload idempotency fingerprint에 포함하지 않는다.
- `PublicDocumentMetadata.to_dict()`는 값을 그대로 반환한다. JSON encoder가 지원하지 않는 값은 host가 별도로 변환해야 한다.

### 4.3 결과와 operation 상태

```text
UploadDocumentResult(
    document_id: str,
    metadata: PublicDocumentMetadata,
    created: bool = True,
)

UploadOperationResult(
    scope: str,
    idempotency_key: str,
    document_id: str,
    state: UploadOperationState,
    created_at: datetime,
    updated_at: datetime,
)
```

`UploadOperationState` 자체는 package root 공개 이름이 아니다. operation 결과의 `state.value`는 `pending`, `succeeded`, `failed` 문자열이다.

- 동일한 scope/key와 동일한 request fingerprint를 replay하면 `created=False` 결과를 반환한다.
- 다른 fingerprint로 같은 scope/key를 사용하면 `IdempotencyConflictError`다.
- 기존 operation이 pending이면 `IdempotencyInProgressError`다.
- operation 조회에는 정확한 `scope`와 `idempotency_key`가 필요하며 기록이 없으면 `UploadOperationNotFoundError`다.
- persistent `operation_store`가 없으면 idempotency upload와 operation 조회는 `ValidationError`다.

## 5. 문서 정보·본문·목록 모델

### 5.1 public metadata와 내부 metadata

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
    extra_metadata: object = <empty dict>,
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
    extra_metadata: object = <empty dict>,
)
```

- 일반 upload 결과, `get_document_metadata()`, `list_documents()`/`list_documents_page()`는 `PublicDocumentMetadata`를 반환한다.
- `PublicDocumentMetadata`에는 `storage_key`가 구조적으로 없다.
- `DocumentMetadata`는 `storage_key`를 포함하므로 관리·복구 경계에서만 사용한다. 일반 API 응답, observer event, tenant callback에 그대로 전달하지 않는다.
- `get_internal_document_metadata()`, `list_recovery_candidates()`, `inspect_document()`와 복구 결과의 inspection은 명시적인 관리 경계다.
- 일반 단건·목록 조회는 `DELETING`과 `DELETED` 문서를 숨긴다. 해당 상태를 일반 filter로 요청하면 `ValidationError`다.
- 삭제 문서의 public metadata 조회는 `DocumentNotFoundError`, 삭제 문서의 본문/본문 stream 조회는 `DocumentDeletedError`다.

`public_metadata(value)`는 `DocumentMetadata`, `PublicDocumentMetadata`, `UploadDocumentResult`를 받아 `PublicDocumentMetadata`로 깊은 복사 projection한다.

`PublicDocumentMetadata.to_dict()`는 기존 `extra_metadata` field명을 유지한다. `to_public_dict()`는 외부 canonical field명인 `metadata`를 사용한다. public 결과 schema와 canonical dump에는 `storage_key`가 없다. `PublicDocumentMetadata`, `UploadDocumentResult`, `DocumentPage`, `DeleteDocumentResult`, `DataResetResult`는 `json_schema()`와 같은 내용을 반환하는 `model_json_schema()`를 제공한다.

### 5.2 `DocumentStatus`

```text
DocumentStatus.UPLOADED  == "uploaded"
DocumentStatus.AVAILABLE == "available"
DocumentStatus.DELETING  == "deleting"
DocumentStatus.DELETED   == "deleted"
DocumentStatus.FAILED    == "failed"
```

일반 public 목록에서는 `DELETING`과 `DELETED`가 제외된다. `FAILED`와 `DELETING`은 recovery candidate API의 허용 status다.

### 5.3 본문과 stream

```text
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
```

`DocumentContentStream` public method:

```text
stream.iter_chunks(chunk_size: int | None = None) -> Iterator[bytes]
stream.iter_chunks_closing(chunk_size: int | None = None) -> Iterator[bytes]
stream.close() -> None
with stream: ...
```

- `chunk_size`는 양수여야 한다.
- `iter_chunks()`는 읽기만 하며 stream을 자동으로 닫는 계약이 아니다.
- `iter_chunks_closing()`은 정상 소진, read error, iterator의 명시적 close에서 SDK가 연 stream을 닫는다.
- `close()`와 context-manager 종료는 반복 호출에 안전하다.
- `copy_document_to()`는 source stream을 닫고 caller가 준 sink는 닫지 않는다. SHA-256과 저장 크기를 검증하며, 검증 결과는 `DocumentCopyResult`다.

`AsyncDocumentContentStream` public member:

```text
async_stream.content_type -> str
async_stream.filename -> str
async_stream.size -> int
async_stream.checksum -> str | None
async_stream.closed -> bool
async_stream.iter_chunks(chunk_size: int | None = None) -> AsyncIterator[bytes]
async_stream.aiter_chunks_closing(chunk_size: int | None = None) -> AsyncIterator[bytes]
await async_stream.aclose()
async with async_stream: ...
```

async stream의 읽기와 close는 event loop를 직접 차단하지 않는다. 정상 소진, read error, cancellation, context 종료 및 반복 호출 가능한 `aclose()`에서 source를 정리한다.

### 5.4 cursor page

```text
DocumentPage(
    items: list[PublicDocumentMetadata],
    next_cursor: str | None,
    has_more: bool,
)
```

- `list_documents()`는 `DocumentPage`를 반환하며 `list_documents_page()`와 같은 cursor 계약을 사용한다.
- `limit`는 1 이상 1000 이하이며 기본값은 100이다.
- 정렬은 `created_at`과 immutable `document_id`의 안정적인 내림차순 복합 순서다.
- 다음 page에는 직전 응답의 `next_cursor`를 같은 `status`와 같은 `limit`로 전달한다.
- cursor는 opaque 값이며 status filter와 page size에 결합된다. 변조했거나 다른 조건·page size로 재사용하면 `ValidationError`다.
- 현재 public 목록은 cursor 방식만 제공한다. 일반 문서 목록에는 offset parameter/API가 없다.
- `DocumentPage`는 `items`를 순회할 수 있어 `for item in page`도 가능하다.

## 6. 삭제·reset 결과

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

`DataResetResult` public member:

```text
result.total_deleted -> int
result.to_dict() -> dict[str, object]
result.json_schema() -> dict[str, object]
result.model_json_schema() -> dict[str, object]
```

- `delete_document(..., hard_delete=False)`는 object를 삭제하고 metadata를 deleted 상태로 표시하는 soft delete다.
- `soft_delete_document()`와 `hard_delete_document()`는 의도를 드러내는 convenience method다.
- object 삭제 실패는 metadata를 best-effort로 `FAILED`로 전환한 후 `StorageError`를 발생시킬 수 있다.
- object 삭제 후 metadata 처리 실패는 `ConsistencyError`며 metadata가 `DELETING`으로 남을 수 있다.
- `clear_all_data()`와 `initialize_for_data_load()`는 DMS가 관리하는 metadata, `documents/` prefix object, 설정된 upload operation record를 모두 대상으로 한다. orphan object도 정리한다.
- 한 store가 실패해도 가능한 다른 store 정리를 계속 시도한다. 실패 시 `DataResetError.result`, `errors`, `failed_stores`를 확인하고 `result.ready_for_data_load`는 `False`다.
- `initialize_for_data_load()`는 빈 상태에서도 성공하는 멱등 작업이다.

## 7. consistency recovery API

### 7.1 enum과 inspection

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
```

```text
DocumentInspection(
    document_id: str,
    metadata_exists: bool,
    object_exists: bool | None,
    status: DocumentStatus | None,
    consistent: bool,
    issue: RecoveryIssue,
    storage_key: str | None = None,
)
```

`inspect_document()`은 metadata가 없을 때 `DocumentNotFoundError` 대신 `metadata_exists=False`, `issue=METADATA_MISSING`인 typed result를 반환한다. `storage_key`가 포함될 수 있으므로 이 결과를 외부 응답에 그대로 노출하지 않는다.

### 7.2 결과와 plan

```text
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

`BatchReconciliationResult` public member:

```text
result.scanned -> int
result.failed -> int
result.eligible -> int
result.applied -> int
result.skipped -> int
result.to_plan() -> ReconciliationPlan
result.to_dict() -> dict[str, object]
```

`to_plan()`은 `dry_run=True` 결과에서만 사용할 수 있다. plan 생성 시 모든 item의 action이 plan action과 일치해야 한다.

### 7.3 recovery method 규칙

- `list_recovery_candidates(status=..., offset=0, limit=100)`은 `FAILED` 또는 `DELETING`만 허용하며 내부 `DocumentMetadata`를 반환한다. `limit`는 1~1000이다.
- `iter_recovery_candidates()`는 offset을 내부에서 유지하는 sync/async iterator다.
- `reconcile_document()`은 실행 전에 상태를 다시 점검하고 action 조건이 맞을 때만 적용한다. `dry_run=True`에서는 상태를 변경하지 않는다.
- `reconcile_documents()`는 제한된 범위의 일괄 복구이며 항목별 실패를 `ReconciliationResult.error_type/error_message`에 보존한다.
- `execute_reconciliation_plan()`은 실행 직전에 각 item을 재점검하므로 stale plan은 성공으로 간주하지 않는다.
- `PURGE_ORPHAN_OBJECT`는 metadata가 없고 caller가 정확한 `storage_key`를 제공한 경우에만 사용할 수 있다.

## 8. access context·observer·capability protocol

### 8.1 access policy와 scoped context

```text
AccessContext(
    subject: str | None = None,
    tenant: str | None = None,
    roles: frozenset[str] = frozenset(),
)

DmsOperationContext(
    access: AccessContext | None = None,
    created_by: str | None = None,
    idempotency_scope: str | None = None,
    audit_actor: str | None = None,
    default_metadata: object = None,
)
```

```text
DocumentAccessPolicy.allows(
    *,
    operation: str,
    context: AccessContext | None,
    metadata: PublicDocumentMetadata | None,
) -> bool
```

- policy callback에는 public projection만 전달되며 내부 `storage_key`는 전달되지 않는다.
- `clear_all_data()`와 `initialize_for_data_load()` 같은 전역 작업에서는 `metadata=None`일 수 있다.
- policy가 `False`를 반환하거나 policy 실행 자체가 실패하면 `AccessDeniedError`다.
- 목록에서는 policy 허용 항목을 모으면서 cursor/page size semantics를 유지한다.

### 8.2 operation observer와 recovery audit

```text
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
```

`OperationEvent.to_dict()`는 event field를 mapping으로 변환한다. observer callback이 실패해도 원래 작업 성공·실패는 바뀌지 않는다.

```text
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

`recovery_audit_hook`은 각 복구 시도에 대해 `RecoveryAuditEvent`를 받는다. hook 실패는 복구 결과를 덮지 않는다.

### 8.3 기능별 protocol

기능별 protocol은 host 함수가 전체 구현체에 결합되지 않도록 하는 runtime-checkable sync 계약이다.

```text
DocumentWriter
  upload_document(request) -> UploadDocumentResult
  upload_file(path, *, filename=None, content_type=None,
              document_id=None, metadata=None, created_by=None)
              -> UploadDocumentResult
  upload_document_stream(request) -> UploadDocumentResult

DocumentReader
  get_document_metadata(document_id, *, access_context=None)
      -> PublicDocumentMetadata
  get_document_content(document_id, *, access_context=None)
      -> DocumentContent
  get_document_content_stream(document_id, *, chunk_size=65536,
                              access_context=None) -> DocumentContentStream
  copy_document_to(document_id, sink, *, chunk_size=65536,
                  verify_checksum=True, access_context=None)
      -> DocumentCopyResult

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
```

`DocumentManagementClient`는 위 다섯 capability protocol을 합친 protocol이다. `DefaultDocumentManagementSDK`는 이 protocol들과 runtime-checkable compatibility를 가진다. async facade는 별도 async protocol을 export하지 않으며, 같은 작업을 awaitable로 제공한다.

## 9. 오류 모델

모든 공개 SDK 오류는 `DmsError`에서 파생되며 안정적인 class attribute를 제공한다.

```text
DmsError(
    message: str,
    *,
    document_id: str | None = None,
    diagnosis: object | None = None,
)

error.code -> str
error.category -> str
error.retryable -> bool
error.document_id -> str | None
error.diagnosis -> object | None
```

| 오류 | `code` | `category` | retryable | caller action |
| --- | --- | --- | :---: | --- |
| `DmsError` | `dms_error` | `internal` | 아니오 | 공통 오류 boundary로 처리한다. |
| `ConfigurationError` | `configuration_invalid` | `configuration` | 아니오 | factory 입력, bucket, dialect를 확인한다. |
| `ValidationError` | `validation_invalid` | `validation` | 아니오 | request, cursor, recovery 조건을 수정한다. |
| `AccessDeniedError` | `access_denied` | `access` | 아니오 | host access policy/context를 확인한다. |
| `PayloadTooLargeError` | `document_too_large` | `validation` | 아니오 | 파일 크기 또는 `max_file_size`를 조정한다. |
| `DocumentNotFoundError` | `document_not_found` | `not_found` | 아니오 | id 또는 public 은닉 상태를 확인한다. |
| `DocumentDeletedError` | `document_deleted` | `unavailable` | 아니오 | internal metadata/recovery 경로를 사용한다. |
| `DuplicateDocumentError` | `document_duplicate` | `conflict` | 아니오 | 다른 document id를 사용하거나 기존 id를 조회한다. |
| `IdempotencyConflictError` | `idempotency_conflict` | `conflict` | 아니오 | 같은 key에는 같은 요청만 재사용한다. |
| `IdempotencyInProgressError` | `idempotency_in_progress` | `conflict` | 예 | operation 상태를 확인하고 재시도 정책을 적용한다. |
| `UploadOperationNotFoundError` | `upload_operation_not_found` | `not_found` | 아니오 | 정확한 scope/key를 사용한다. |
| `StorageError` | `object_storage_failed` | `storage` | 예 | object storage 상태를 확인한 후 재시도한다. |
| `MetadataStoreError` | `metadata_store_failed` | `storage` | 예 | metadata store 상태를 확인한 후 재시도한다. |
| `ConsistencyError` | `document_inconsistent` | `consistency` | 아니오 | `inspect_document()`와 recovery를 수행한다. |
| `DataResetError` | `data_reset_failed` | `consistency` | 예 | `result`, `errors`, `failed_stores`를 확인한다. |

`DataResetError`는 추가로 다음 instance attribute를 제공한다.

```text
error.result: DataResetResult
error.errors: tuple[Exception, ...]
error.failed_stores: tuple[str, ...]
```

DMS는 HTTP server가 아니므로 HTTP status, response body, retry header를 결정하지 않는다. host transport는 위 stable field를 자체 응답 규칙으로 변환해야 한다.

## 10. 추적성 매트릭스

각 row는 **package-root 공개 이름 또는 공개 facade operation → 실제 source → 실행 test → Examples-v0.9.0 anchor**를 연결한다. `source-only`는 source와 예제는 있지만 현재 checkout에 해당 동작을 직접 실행하는 focused test가 없다는 뜻이며, facade membership test를 behavior test로 과장하지 않았다.

### 10.1 공개 이름 추적

| 공개 이름 | source | test 근거 | example | trace |
| --- | --- | --- | --- | --- |
| `AccessContext` | `dms/sdk/contracts.py:26` | `test_dms/test_sdk_consumer_integration_contracts.py::test_access_policy_filters_before_paging_and_covers_privileged_reads` | [E-10](Examples-v0.9.0.md#example-e10) | `TR-POLICY` |
| `AccessDeniedError` | `dms/sdk/errors.py:34` | `test_dms/test_sdk_consumer_integration_contracts.py::test_access_policy_cannot_be_bypassed_by_content_delete_or_recovery` | [E-10](Examples-v0.9.0.md#example-e10), [E-12](Examples-v0.9.0.md#example-e12) | `TR-ERR` |
| `AsyncDocumentContentStream` | `dms/sdk/types.py:203` | `test_dms/test_sdk_contract_completion.py::test_async_closing_iterator_closes_on_exhaustion_and_explicit_early_stop` | [E-06](Examples-v0.9.0.md#example-e06), [E-11](Examples-v0.9.0.md#example-e11) | `TR-ASYNC` |
| `AsyncDocumentManagementSDK` | `dms/sdk/async_sdk.py:37` | `test_dms/test_sdk_contract_completion.py::test_async_facade_runs_metadata_list_delete_without_global_lifecycle` | [E-11](Examples-v0.9.0.md#example-e11) | `TR-ASYNC` |
| `AsyncScopedDocumentManagementSDK` | `dms/sdk/async_scoped.py:34` | `test_dms/test_refactor_followup_regressions.py::test_async_scoped_facade_preserves_streaming_and_recovery_surface` | [E-11](Examples-v0.9.0.md#example-e11) | `TR-ASYNC` |
| `DmsOperationContext` | `dms/sdk/contracts.py:46` | `test_dms/test_sdk_consumer_integration_contracts.py::test_scoped_operation_context_supplies_opaque_default_metadata` | [E-10](Examples-v0.9.0.md#example-e10), [E-11](Examples-v0.9.0.md#example-e11) | `TR-POLICY` |
| `ConfigurationError` | `dms/sdk/errors.py:20` | `test_dms/test_sdk_factory.py::test_factory_rejects_blank_bucket_before_adapter_assembly`, `test_dms/test_sdk_factory.py::test_factory_rejects_unsupported_sqlalchemy_dialect` | [E-01](Examples-v0.9.0.md#example-e01), [E-12](Examples-v0.9.0.md#example-e12) | `TR-ERR` |
| `DataResetError` | `dms/sdk/errors.py:92` | `test_dms/test_sdk_data_reset.py::test_clear_all_data_reports_partial_cleanup_and_continues_other_stores` | [E-07](Examples-v0.9.0.md#example-e07), [E-12](Examples-v0.9.0.md#example-e12) | `TR-RESET` |
| `DataResetResult` | `dms/sdk/types.py:295` | `test_dms/test_sdk_data_reset.py::test_data_reset_result_exposes_json_schema` | [E-07](Examples-v0.9.0.md#example-e07) | `TR-RESET` |
| `DataResetter` | `dms/sdk/contracts.py:159` | `test_dms/test_sdk_data_reset.py::test_default_sdk_satisfies_data_resetter_contract` | [E-07](Examples-v0.9.0.md#example-e07), [E-10](Examples-v0.9.0.md#example-e10) | `TR-CONTRACT` |
| `BatchReconciliationResult` | `dms/sdk/types.py:414` | `test_dms/test_sdk_reconciliation.py::test_batch_summary_properties_are_stable` | [E-09](Examples-v0.9.0.md#example-e09) | `TR-REC` |
| `DocumentInspection` | `dms/sdk/types.py:372` | `test_dms/test_sdk_reconciliation_core.py::test_inspect_missing_metadata_is_a_typed_result_not_not_found` | [E-09](Examples-v0.9.0.md#example-e09) | `TR-REC` |
| `DocumentPage` | `dms/sdk/types.py:333` | `test_dms/test_sdk_pagination.py::test_cursor_page_is_stable_opaque_and_status_bound` | [E-05](Examples-v0.9.0.md#example-e05) | `TR-READ` |
| `PublicDocumentMetadata` | `dms/sdk/types.py:64` | `test_dms/test_sdk_public_contract.py::test_default_metadata_and_upload_results_hide_storage_key` | [E-04](Examples-v0.9.0.md#example-e04) | `TR-DATA` |
| `ReconciliationPlan` | `dms/sdk/types.py:483` | `test_dms/test_sdk_reconciliation.py::test_dry_run_exports_plan_and_execution_revalidates_stale_items_with_best_effort_audit` | [E-09](Examples-v0.9.0.md#example-e09) | `TR-REC` |
| `ReconciliationPlanItem` | `dms/sdk/types.py:469` | `test_dms/test_independent_review_regressions.py::test_plan_is_immutable_action_bound_and_preserves_empty_batch_origin` | [E-09](Examples-v0.9.0.md#example-e09) | `TR-REC` |
| `RecoveryAuditEvent` | `dms/sdk/types.py:502` | `test_dms/test_sdk_reconciliation.py::test_recovery_audit_records_actor_and_time_and_plan_requires_dry_run` | [E-09](Examples-v0.9.0.md#example-e09) | `TR-OBS` |
| `ReconciliationResult` | `dms/sdk/types.py:394` | `test_dms/test_sdk_reconciliation_core.py::test_batch_is_bounded_status_restricted_dry_run_and_preserves_item_errors` | [E-09](Examples-v0.9.0.md#example-e09) | `TR-REC` |
| `RecoveryAction` | `dms/sdk/types.py:364` | `test_dms/test_sdk_reconciliation_core.py::test_complete_deletion_requires_deleting_and_absent_object_then_soft_or_hard` | [E-09](Examples-v0.9.0.md#example-e09) | `TR-REC` |
| `RecoveryIssue` | `dms/sdk/types.py:356` | `test_dms/test_sdk_reconciliation_core.py::test_inspect_missing_metadata_is_a_typed_result_not_not_found` | [E-09](Examples-v0.9.0.md#example-e09) | `TR-REC` |
| `ConsistencyError` | `dms/sdk/errors.py:85` | `test_dms/test_sdk_behavior.py::test_get_document_content_raises_consistency_error_when_object_is_missing` | [E-09](Examples-v0.9.0.md#example-e09), [E-12](Examples-v0.9.0.md#example-e12) | `TR-ERR` |
| `DefaultDocumentManagementSDK` | `dms/sdk/implementation.py:69` | `test_dms/test_sdk_factory.py::test_sdk_accepts_injected_storage_ports` | [E-01](Examples-v0.9.0.md#example-e01), [E-02](Examples-v0.9.0.md#example-e02) | `TR-ASM` |
| `DeleteDocumentResult` | `dms/sdk/types.py:275` | `test_dms/test_sdk_behavior.py::test_delete_document_soft_delete_marks_metadata_and_removes_content` | [E-07](Examples-v0.9.0.md#example-e07) | `TR-DEL` |
| `DocumentContent` | `dms/sdk/types.py:138` | `test_dms/test_sdk_consumer_integration_contracts.py::test_async_high_level_operations_preserve_sync_contracts` | [E-06](Examples-v0.9.0.md#example-e06) | `TR-READ` |
| `DocumentContentStream` | `dms/sdk/types.py:148` | `test_dms/test_sdk_lifecycle_and_conflicts.py::test_document_content_stream_context_manager_closes_idempotently` | [E-06](Examples-v0.9.0.md#example-e06) | `TR-READ` |
| `DocumentAccessPolicy` | `dms/sdk/contracts.py:35` | `test_dms/test_sdk_consumer_integration_contracts.py::test_access_policy_filters_before_paging_and_covers_privileged_reads` | [E-10](Examples-v0.9.0.md#example-e10) | `TR-POLICY` |
| `DocumentCopyResult` | `dms/sdk/contracts.py:84` | `test_dms/test_sdk_consumer_integration_contracts.py::test_copy_document_to_closes_source_and_keeps_sink_open` | [E-06](Examples-v0.9.0.md#example-e06) | `TR-READ` |
| `DocumentDeleter` | `dms/sdk/contracts.py:151` | `test_dms/test_sdk_consumer_integration_contracts.py::test_default_sdk_satisfies_public_capability_protocols` | [E-07](Examples-v0.9.0.md#example-e07), [E-10](Examples-v0.9.0.md#example-e10) | `TR-CONTRACT` |
| `DocumentManagementSDKFactory` | `dms/sdk/factory.py:58` | `test_dms/test_sdk_factory.py::test_factory_assembles_sdk_from_sqlalchemy_engine_and_minio_client` | [E-01](Examples-v0.9.0.md#example-e01) | `TR-ASM` |
| `DocumentLister` | `dms/sdk/contracts.py:137` | `test_dms/test_sdk_consumer_integration_contracts.py::test_default_sdk_satisfies_public_capability_protocols` | [E-05](Examples-v0.9.0.md#example-e05), [E-10](Examples-v0.9.0.md#example-e10) | `TR-CONTRACT` |
| `DocumentManagementClient` | `dms/sdk/contracts.py:170` | `test_dms/test_sdk_consumer_integration_contracts.py::test_default_sdk_satisfies_public_capability_protocols` | [E-10](Examples-v0.9.0.md#example-e10) | `TR-CONTRACT` |
| `DocumentReader` | `dms/sdk/contracts.py:116` | `test_dms/test_sdk_consumer_integration_contracts.py::test_default_sdk_satisfies_public_capability_protocols` | [E-06](Examples-v0.9.0.md#example-e06), [E-10](Examples-v0.9.0.md#example-e10) | `TR-CONTRACT` |
| `DocumentWriter` | `dms/sdk/contracts.py:100` | `test_dms/test_sdk_consumer_integration_contracts.py::test_default_sdk_satisfies_public_capability_protocols` | [E-03](Examples-v0.9.0.md#example-e03), [E-10](Examples-v0.9.0.md#example-e10) | `TR-CONTRACT` |
| `DocumentMetadata` | `dms/domain/models.py:41` | `test_dms/test_sdk_public_contract.py::test_privileged_metadata_access_is_explicit` | [E-04](Examples-v0.9.0.md#example-e04), [E-09](Examples-v0.9.0.md#example-e09) | `TR-DATA` |
| `DocumentDeletedError` | `dms/sdk/errors.py:55` | `test_dms/test_sdk_public_contract.py::test_deleted_document_content_and_stream_raise_deleted_error` | [E-07](Examples-v0.9.0.md#example-e07), [E-12](Examples-v0.9.0.md#example-e12) | `TR-ERR` |
| `DocumentNotFoundError` | `dms/sdk/errors.py:48` | `test_dms/test_sdk_requirement_feedback.py::test_public_metadata_get_and_lists_hide_deleted_documents` | [E-07](Examples-v0.9.0.md#example-e07), [E-12](Examples-v0.9.0.md#example-e12) | `TR-ERR` |
| `DuplicateDocumentError` | `dms/sdk/errors.py:62` | `test_dms/test_sdk_lifecycle_and_conflicts.py::test_upload_document_maps_database_conflict_to_duplicate_and_rolls_back_object` | [E-03](Examples-v0.9.0.md#example-e03), [E-12](Examples-v0.9.0.md#example-e12) | `TR-ERR` |
| `DmsError` | `dms/sdk/errors.py:6` | source-only: base class field contract is covered through subclass matrix, direct base handling is documented in E-12 | [E-12](Examples-v0.9.0.md#example-e12) | `TR-ERR` |
| `IdempotencyConflictError` | `dms/sdk/errors.py:113` | source-only: current checkout has no focused persistent replay/conflict test | [E-08](Examples-v0.9.0.md#example-e08), [E-12](Examples-v0.9.0.md#example-e12) | `TR-ERR` |
| `IdempotencyInProgressError` | `dms/sdk/errors.py:120` | `test_dms/test_sdk_requirement_feedback.py::test_all_public_sdk_errors_expose_structured_contract` | [E-08](Examples-v0.9.0.md#example-e08), [E-12](Examples-v0.9.0.md#example-e12) | `TR-ERR` |
| `UploadOperationNotFoundError` | `dms/sdk/errors.py:128` | source-only: current checkout has no focused operation lookup test | [E-08](Examples-v0.9.0.md#example-e08), [E-12](Examples-v0.9.0.md#example-e12) | `TR-ERR` |
| `MetadataStoreError` | `dms/sdk/errors.py:77` | `test_dms/test_sdk_behavior.py::test_get_document_metadata_raises_metadata_store_error_for_backend_failure` | [E-12](Examples-v0.9.0.md#example-e12) | `TR-ERR` |
| `PayloadTooLargeError` | `dms/sdk/errors.py:41` | `test_dms/test_sdk_feedback_async_cursor.py::test_configured_file_size_limit_has_distinct_public_error` | [E-03](Examples-v0.9.0.md#example-e03), [E-12](Examples-v0.9.0.md#example-e12) | `TR-ERR` |
| `OperationEvent` | `dms/sdk/contracts.py:55` | `test_dms/test_sdk_consumer_integration_contracts.py::test_operation_observer_receives_safe_success_and_failure_events` | [E-10](Examples-v0.9.0.md#example-e10) | `TR-OBS` |
| `OperationObserver` | `dms/sdk/contracts.py:79` | `test_dms/test_sdk_consumer_integration_contracts.py::test_observer_failure_does_not_change_document_result` | [E-10](Examples-v0.9.0.md#example-e10) | `TR-OBS` |
| `ScopedDocumentManagementSDK` | `dms/sdk/scoped.py:33` | `test_dms/test_sdk_consumer_integration_contracts.py::test_scoped_operation_context_supplies_opaque_default_metadata` | [E-10](Examples-v0.9.0.md#example-e10), [E-11](Examples-v0.9.0.md#example-e11) | `TR-POLICY` |
| `StorageError` | `dms/sdk/errors.py:69` | `test_dms/test_sdk_reconciliation_core.py::test_inspection_and_purge_backend_errors_map_to_existing_sdk_errors` | [E-09](Examples-v0.9.0.md#example-e09), [E-12](Examples-v0.9.0.md#example-e12) | `TR-ERR` |
| `UploadDocumentRequest` | `dms/sdk/types.py:14` | `test_dms/test_sdk_behavior.py::test_upload_document_persists_metadata_and_content` | [E-03](Examples-v0.9.0.md#example-e03) | `TR-UPL` |
| `UploadDocumentStreamRequest` | `dms/sdk/types.py:27` | `test_dms/test_sdk_stream_upload_contract.py::test_stream_request_is_public_and_uploads_without_buffering_as_bytes` | [E-03](Examples-v0.9.0.md#example-e03) | `TR-UPL` |
| `UploadDocumentResult` | `dms/sdk/types.py:46` | `test_dms/test_sdk_public_contract.py::test_default_metadata_and_upload_results_hide_storage_key` | [E-03](Examples-v0.9.0.md#example-e03), [E-04](Examples-v0.9.0.md#example-e04) | `TR-UPL` |
| `UploadOperationResult` | `dms/sdk/types.py:118` | source-only: current checkout has no focused operation result serialization/lookup test | [E-08](Examples-v0.9.0.md#example-e08) | `TR-UPL` |
| `ValidationError` | `dms/sdk/errors.py:27` | `test_dms/test_sdk_stream_upload_contract.py::test_stream_upload_enforces_declared_size_and_rolls_back`, `test_dms/test_sdk_reconciliation_core.py::test_batch_is_bounded_status_restricted_dry_run_and_preserves_item_errors` | [E-03](Examples-v0.9.0.md#example-e03), [E-09](Examples-v0.9.0.md#example-e09), [E-12](Examples-v0.9.0.md#example-e12) | `TR-ERR` |
| `public_metadata` | `dms/sdk/types.py:105` | `test_dms/test_sdk_metadata.py::test_public_metadata_projection_accepts_metadata_and_upload_result_without_storage_key` | [E-04](Examples-v0.9.0.md#example-e04) | `TR-DATA` |
| `DocumentStatus` | `dms/domain/models.py:9` | `test_dms/test_sdk_pagination.py::test_cursor_page_is_stable_opaque_and_status_bound`, `test_dms/test_sdk_reconciliation_core.py::test_batch_is_bounded_status_restricted_dry_run_and_preserves_item_errors` | [E-05](Examples-v0.9.0.md#example-e05), [E-09](Examples-v0.9.0.md#example-e09) | `TR-DATA` |

package-root export assembly itself is defined by `dms/__init__.py:1-5` and `dms/sdk/__init__.py:1-127`. The export-membership test intentionally covers the consumer integration subset rather than pretending that `hasattr()` is behavioral coverage; the complete literal runtime list is recorded in section 1.1 and this table.

### 10.2 공개 facade operation 추적

Source ranges identify the implementation of the same operation on the four facade classes:

- base sync: `dms/sdk/implementation.py:115-744`
- base async: `dms/sdk/async_sdk.py:43-394`
- scoped sync: `dms/sdk/scoped.py:61-318`
- scoped async: `dms/sdk/async_scoped.py:54-300`

| operation | 대표 source line | 직접 실행 test 근거 | example |
| --- | --- | --- | --- |
| `scoped` | `dms/sdk/implementation.py:115`, `dms/sdk/async_sdk.py:43` | `test_dms/test_sdk_consumer_integration_contracts.py::test_scoped_operation_context_supplies_opaque_default_metadata` | [E-10](Examples-v0.9.0.md#example-e10), [E-11](Examples-v0.9.0.md#example-e11) |
| `upload_document` | `dms/sdk/implementation.py:118`, `dms/sdk/async_sdk.py:55`, `dms/sdk/scoped.py:61`, `dms/sdk/async_scoped.py:54` | `test_dms/test_sdk_behavior.py::test_upload_document_persists_metadata_and_content` | [E-03](Examples-v0.9.0.md#example-e03) |
| `upload_file` | `dms/sdk/implementation.py:125`, `dms/sdk/async_sdk.py:58`, `dms/sdk/scoped.py:97`, `dms/sdk/async_scoped.py:59` | `test_dms/test_sdk_consumer_integration_contracts.py::test_upload_file_and_known_size_stream_own_only_internally_opened_resources` | [E-02](Examples-v0.9.0.md#example-e02), [E-03](Examples-v0.9.0.md#example-e03), [E-11](Examples-v0.9.0.md#example-e11) |
| `upload_document_stream` | `dms/sdk/implementation.py:159`, `dms/sdk/async_sdk.py:78`, `dms/sdk/scoped.py:71`, `dms/sdk/async_scoped.py:79` | `test_dms/test_sdk_stream_upload_contract.py::test_stream_upload_enforces_declared_size_and_rolls_back` | [E-03](Examples-v0.9.0.md#example-e03) |
| `get_upload_operation` | `dms/sdk/implementation.py:168`, `dms/sdk/async_sdk.py:83`, `dms/sdk/scoped.py:83`, `dms/sdk/async_scoped.py:84` | source-only: async facade membership is checked by `test_dms/test_sdk_contract_completion.py::test_async_facade_exposes_awaitable_counterparts_for_all_public_sdk_operations` | [E-08](Examples-v0.9.0.md#example-e08) |
| `get_internal_document_metadata` | `dms/sdk/implementation.py:171`, `dms/sdk/async_sdk.py:92`, `dms/sdk/scoped.py:119`, `dms/sdk/async_scoped.py:96` | `test_dms/test_sdk_public_contract.py::test_privileged_metadata_access_is_explicit` | [E-04](Examples-v0.9.0.md#example-e04) |
| `get_document_metadata` | `dms/sdk/implementation.py:191`, `dms/sdk/async_sdk.py:104`, `dms/sdk/scoped.py:116`, `dms/sdk/async_scoped.py:99` | `test_dms/test_sdk_behavior.py::test_get_document_metadata_raises_document_not_found_for_missing_id` | [E-04](Examples-v0.9.0.md#example-e04), [E-07](Examples-v0.9.0.md#example-e07) |
| `list_documents` | `dms/sdk/implementation.py:208`, `dms/sdk/async_sdk.py:116`, `dms/sdk/scoped.py:122`, `dms/sdk/async_scoped.py:102` | `test_dms/test_sdk_behavior.py::test_list_documents_returns_cursor_paginated_metadata_filtered_by_status` | [E-05](Examples-v0.9.0.md#example-e05) |
| `list_documents_page` | `dms/sdk/implementation.py:235`, `dms/sdk/async_sdk.py:132`, `dms/sdk/scoped.py:136`, `dms/sdk/async_scoped.py:116` | `test_dms/test_sdk_public_contract.py::test_default_metadata_and_upload_results_hide_storage_key` | [E-05](Examples-v0.9.0.md#example-e05) |
| `iter_documents` | `dms/sdk/implementation.py:295`, `dms/sdk/async_sdk.py:148`, `dms/sdk/scoped.py:150`, `dms/sdk/async_scoped.py:130` | `test_dms/test_sdk_consumer_integration_contracts.py::test_document_and_recovery_iterators_preserve_page_conditions` | [E-05](Examples-v0.9.0.md#example-e05), [E-11](Examples-v0.9.0.md#example-e11) |
| `inspect_document` | `dms/sdk/implementation.py:316`, `dms/sdk/async_sdk.py:163`, `dms/sdk/scoped.py:241`, `dms/sdk/async_scoped.py:222` | `test_dms/test_sdk_reconciliation_core.py::test_inspect_missing_metadata_is_a_typed_result_not_not_found` | [E-09](Examples-v0.9.0.md#example-e09) |
| `list_recovery_candidates` | `dms/sdk/implementation.py:346`, `dms/sdk/async_sdk.py:175`, `dms/sdk/scoped.py:244`, `dms/sdk/async_scoped.py:225` | `test_dms/test_sdk_reconciliation_core.py::test_batch_is_bounded_status_restricted_dry_run_and_preserves_item_errors` | [E-09](Examples-v0.9.0.md#example-e09) |
| `iter_recovery_candidates` | `dms/sdk/implementation.py:391`, `dms/sdk/async_sdk.py:191`, `dms/sdk/scoped.py:258`, `dms/sdk/async_scoped.py:239` | `test_dms/test_sdk_consumer_integration_contracts.py::test_document_and_recovery_iterators_preserve_page_conditions` | [E-09](Examples-v0.9.0.md#example-e09), [E-11](Examples-v0.9.0.md#example-e11) |
| `reconcile_document` | `dms/sdk/implementation.py:414`, `dms/sdk/async_sdk.py:206`, `dms/sdk/scoped.py:270`, `dms/sdk/async_scoped.py:252` | `test_dms/test_sdk_reconciliation_core.py::test_complete_deletion_requires_deleting_and_absent_object_then_soft_or_hard` | [E-09](Examples-v0.9.0.md#example-e09) |
| `execute_reconciliation_plan` | `dms/sdk/implementation.py:448`, `dms/sdk/async_sdk.py:226`, `dms/sdk/scoped.py:288`, `dms/sdk/async_scoped.py:290` | `test_dms/test_sdk_reconciliation.py::test_dry_run_exports_plan_and_execution_revalidates_stale_items_with_best_effort_audit` | [E-09](Examples-v0.9.0.md#example-e09) |
| `reconcile_documents` | `dms/sdk/implementation.py:493`, `dms/sdk/async_sdk.py:240`, `dms/sdk/scoped.py:300`, `dms/sdk/async_scoped.py:270` | `test_dms/test_sdk_reconciliation_core.py::test_batch_is_bounded_status_restricted_dry_run_and_preserves_item_errors` | [E-09](Examples-v0.9.0.md#example-e09) |
| `get_document_content` | `dms/sdk/implementation.py:546`, `dms/sdk/async_sdk.py:262`, `dms/sdk/scoped.py:162`, `dms/sdk/async_scoped.py:143` | `test_dms/test_sdk_behavior.py::test_get_document_content_stream_returns_chunked_stream`, `test_dms/test_sdk_consumer_integration_contracts.py::test_async_high_level_operations_preserve_sync_contracts` | [E-06](Examples-v0.9.0.md#example-e06) |
| `get_document_content_stream` | `dms/sdk/implementation.py:563`, `dms/sdk/async_sdk.py:274`, `dms/sdk/scoped.py:177`, `dms/sdk/async_scoped.py:146` | `test_dms/test_sdk_behavior.py::test_get_document_content_stream_returns_chunked_stream` | [E-06](Examples-v0.9.0.md#example-e06) |
| `get_document_content_async_stream` | `dms/sdk/implementation.py:656`, `dms/sdk/async_sdk.py:287`, `dms/sdk/scoped.py:165`, `dms/sdk/async_scoped.py:158` | `test_dms/test_sdk_feedback_async_cursor.py::test_async_download_stream_closes_on_context_exit_and_exhaustion` | [E-06](Examples-v0.9.0.md#example-e06), [E-11](Examples-v0.9.0.md#example-e11) |
| `iter_document_chunks` | `dms/sdk/implementation.py:585`, `dms/sdk/async_sdk.py:300`, `dms/sdk/scoped.py:189`, `dms/sdk/async_scoped.py:169` | `test_dms/test_sdk_contract_completion.py::test_sync_closing_iterator_closes_on_exhaustion_and_explicit_early_stop`, `test_dms/test_sdk_contract_completion.py::test_async_closing_iterator_closes_on_exhaustion_and_explicit_early_stop` | [E-06](Examples-v0.9.0.md#example-e06), [E-11](Examples-v0.9.0.md#example-e11) |
| `copy_document_to` | `dms/sdk/implementation.py:602`, `dms/sdk/async_sdk.py:318`, `dms/sdk/scoped.py:201`, `dms/sdk/async_scoped.py:182` | `test_dms/test_sdk_consumer_integration_contracts.py::test_copy_document_to_closes_source_and_keeps_sink_open` | [E-06](Examples-v0.9.0.md#example-e06) |
| `delete_document` | `dms/sdk/implementation.py:682`, `dms/sdk/async_sdk.py:336`, `dms/sdk/scoped.py:217`, `dms/sdk/async_scoped.py:198` | `test_dms/test_sdk_behavior.py::test_delete_document_soft_delete_marks_metadata_and_removes_content` | [E-07](Examples-v0.9.0.md#example-e07) |
| `soft_delete_document` | `dms/sdk/implementation.py:701`, `dms/sdk/async_sdk.py:350`, `dms/sdk/scoped.py:229`, `dms/sdk/async_scoped.py:210` | `test_dms/test_sdk_deletion.py::test_explicit_delete_methods_preserve_legacy_dispatch` | [E-07](Examples-v0.9.0.md#example-e07) |
| `hard_delete_document` | `dms/sdk/implementation.py:713`, `dms/sdk/async_sdk.py:362`, `dms/sdk/scoped.py:232`, `dms/sdk/async_scoped.py:213` | `test_dms/test_sdk_behavior.py::test_delete_document_hard_delete_removes_metadata` | [E-07](Examples-v0.9.0.md#example-e07) |
| `clear_all_data` | `dms/sdk/implementation.py:725`, `dms/sdk/async_sdk.py:374`, `dms/sdk/scoped.py:235`, `dms/sdk/async_scoped.py:216` | `test_dms/test_sdk_data_reset.py::test_clear_all_data_removes_documents_objects_and_upload_operations` | [E-07](Examples-v0.9.0.md#example-e07) |
| `initialize_for_data_load` | `dms/sdk/implementation.py:735`, `dms/sdk/async_sdk.py:384`, `dms/sdk/scoped.py:238`, `dms/sdk/async_scoped.py:219` | `test_dms/test_sdk_data_reset.py::test_initialize_for_data_load_is_idempotent_and_leaves_empty_store` | [E-07](Examples-v0.9.0.md#example-e07), [E-11](Examples-v0.9.0.md#example-e11) |

### 10.3 문서 검증 범위

- source baseline은 `f7a40f1`이며, source paths는 이 commit의 line 기준이다.
- 현재 test suite는 facade method 존재 여부와 핵심 behavior를 분리한다. `get_upload_operation()`과 persistent idempotency replay/conflict/lookup는 이 checkout에서 source-only gap으로 표시했다.
- API page와 Examples page의 모든 `python` fence는 AST 구문 검증 대상이다. host가 제공하는 객체를 참조하는 예제도 package-root 공개 import만 사용해야 한다.

검증 명령:

```bash
# dms-core checkout에서 provisioned project interpreter 사용
.venv/bin/python -m pytest test_dms -q

# Wiki clone에서 Python fence 구문 검사
python - <<'PY'
import ast
from pathlib import Path

for path in (Path("API-Reference-v0.9.0.md"), Path("Examples-v0.9.0.md")):
    in_python = False
    block = []
    for line in path.read_text().splitlines():
        if line.strip() == "```python":
            in_python = True
            block = []
        elif in_python and line.strip() == "```":
            ast.parse("\n".join(block), filename=str(path))
            in_python = False
        elif in_python:
            block.append(line)
    assert not in_python, path
PY
```
