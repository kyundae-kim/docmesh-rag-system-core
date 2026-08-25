---
source_url: https://github.com/kyundae-kim/dms-core/wiki/Examples-v0.10.0
ingested: 2026-08-25
sha256: dab98842eafee0c0c5677958033f7e401114204d901d93396460f8168a4d8ce3
---
# DMS SDK 사용 예제 (v0.10.0)

- 기준 API: [API-Reference-v0.10.0](API-Reference-v0.10.0.md)
- 기준 소스: `d508b7c2ea82fb79bfcf008c948a364fcaa962d9`
- import 경계: 모든 DMS 이름은 `from dms import ...`에서 가져온다.
- `engine`, `minio_client`, storage component, `async_engine`은 host 애플리케이션이 생성해 전달하는 placeholder다.
- 예제의 각 anchor는 API Reference의 export/facade trace matrix에서 역참조된다.

> **실행 전 확인**
>
> 예제는 SDK가 storage component와 host lifecycle을 소유하지 않는다는 전제에서 작성되었다. 실행 가능한 애플리케이션에서는 host가 database engine, MinIO client, bucket, 권한 정책, callback 및 종료 순서를 관리한다. 예제는 API contract를 보여주며, Wiki 자체에는 credential이나 실제 endpoint를 넣지 않는다.

## 예제 목차

| anchor | 범위 | API trace |
| --- | --- | --- |
| [E-01](#example-e01) | 동기 factory와 기본 upload | `TR-ASM`, `TR-UPL` |
| [E-02](#example-e02) | native async factory와 직접 조립 | `TR-ASM`, `TR-ASYNC` |
| [E-03](#example-e03) | bytes/file/known-size stream upload | `TR-UPL`, `TR-ERR` |
| [E-04](#example-e04) | public/internal metadata와 projection | `TR-DATA` |
| [E-05](#example-e05) | cursor page, iterator, user scope | `TR-READ`, `TR-POLICY` |
| [E-06](#example-e06) | content stream, async stream, sink copy | `TR-READ`, `TR-ASYNC` |
| [E-07](#example-e07) | soft/hard delete와 data reset | `TR-DEL`, `TR-RESET` |
| [E-08](#example-e08) | idempotency operation 조회 | `TR-UPL`, `TR-ERR` |
| [E-09](#example-e09) | inspection과 dry-run recovery | `TR-REC`, `TR-OBS` |
| [E-10](#example-e10) | access policy, scoped facade, protocols, observer | `TR-POLICY`, `TR-CONTRACT`, `TR-OBS` |
| [E-11](#example-e11) | async facade와 async iterator | `TR-ASYNC` |
| [E-12](#example-e12) | 구조화된 error 처리 | `TR-ERR` |

<a id="example-e01"></a>
## E-01. 동기 factory와 기본 upload

`DocumentManagementSDKFactory`는 host의 SQLAlchemy engine과 MinIO client를 SDK adapter에 연결한다. factory가 만든 SDK와 bucket의 종료는 host가 관리한다.

```python
from dms import DocumentManagementSDKFactory, UploadDocumentRequest

factory = DocumentManagementSDKFactory(
    engine=application.engine,
    minio_client=application.minio_client,
    bucket_name=application.bucket_name,
)
sdk = factory.create()

result = sdk.upload_document(
    UploadDocumentRequest(
        content=b"hello DMS",
        filename="hello.txt",
        content_type="text/plain",
        document_id="hello-001",
        metadata={"source": "example"},
        created_by="example-user",
    )
)

assert result.document_id == "hello-001"
assert not hasattr(result.metadata, "storage_key")
```

마지막 assertion은 public metadata가 storage locator를 노출하지 않는다는 contract를 보여준다. 실제 코드에서는 `hasattr`보다 반환 type을 `PublicDocumentMetadata`로 두고 public field만 사용한다.

### 추적성

- API: `DocumentManagementSDKFactory`, `DefaultDocumentManagementSDK`, `UploadDocumentRequest`, `UploadDocumentResult`
- source: `dms/sdk/factory.py:63`, `dms/sdk/implementation.py:71`, `dms/sdk/types.py:15`
- test: `test_dms/test_sdk_factory.py::test_factory_assembles_sdk_from_sqlalchemy_engine_and_minio_client`

<a id="example-e02"></a>
## E-02. native async factory와 직접 component 조립

native async 경계에서는 별도 async factory를 사용한다. `create()`는 lazy SDK를 반환하고, `create_async()`는 ready 상태까지 기다린 SDK를 반환한다.

```python
from dms import (
    AsyncDocumentManagementSDKFactory,
    DefaultDocumentManagementSDK,
)

async def build_native_async_sdk():
    factory = AsyncDocumentManagementSDKFactory(
        engine=application.async_engine,
        minio_client=application.minio_client,
        bucket_name=application.bucket_name,
        access_policy=application.access_policy,
    )

    lazy_sdk = factory.create()
    lazy_ready_sdk = await lazy_sdk
    eager_sdk = await factory.create_async()
    assert lazy_ready_sdk is lazy_sdk
    return eager_sdk


def build_injected_sync_sdk():
    return DefaultDocumentManagementSDK(
        metadata_store=application.metadata_store,
        object_store=application.object_store,
        operation_store=application.operation_store,
    )
```

`DefaultDocumentManagementSDK`를 직접 조립할 때 component는 package root에서 가져오는 DMS class가 아니라 host가 준비한 구조적 port다. `AsyncDocumentManagementSDK.from_async_components()`는 같은 원칙의 고급 경계이며, 일반 소비자는 factory 경계를 우선한다.

### 추적성

- API: `AsyncDocumentManagementSDKFactory`, `DefaultDocumentManagementSDK`
- source: `dms/sdk/factory.py:63-169`, `dms/sdk/async_sdk.py:130-158`
- test: `test_dms/test_sdk_factory_integration.py::test_async_factory_round_trips_document_through_postgres_and_minio` (integration)

<a id="example-e03"></a>
## E-03. bytes, file, known-size stream upload

세 가지 upload 입력은 모두 결과로 `UploadDocumentResult`를 반환한다. caller가 전달한 input stream은 SDK가 닫지 않고, `upload_file()`이 SDK 내부에서 연 파일은 SDK가 닫는다.

```python
from io import BytesIO
from pathlib import Path

from dms import (
    PayloadTooLargeError,
    UploadDocumentRequest,
    UploadDocumentStreamRequest,
)

bytes_result = sdk.upload_document(
    UploadDocumentRequest(
        content=b"bytes payload",
        filename="bytes.txt",
        content_type="text/plain",
        user_id="alice",
    )
)

file_result = sdk.upload_file(
    Path("payload.bin"),
    document_id="file-001",
    content_type="application/octet-stream",
)

source = BytesIO(b"stream payload")
stream_result = sdk.upload_document_stream(
    UploadDocumentStreamRequest(
        stream=source,
        size=len(b"stream payload"),
        filename="stream.txt",
        content_type="text/plain",
        document_id="stream-001",
    )
)
assert source.closed is False

try:
    sdk.upload_file("too-large.bin")
except PayloadTooLargeError as exc:
    # max_file_size는 factory 또는 직접 조립 시 설정한 값이다.
    print(exc.code, exc.category, exc.retryable)
```

`UploadDocumentStreamRequest.size`는 선언된 길이와 실제 읽은 길이가 일치해야 한다. 불일치 시 object rollback 후 `ValidationError`가 발생한다. unknown-size/async input stream은 이 버전의 공개 API가 아니다.

### 추적성

- API: `UploadDocumentRequest`, `UploadDocumentStreamRequest`, `UploadDocumentResult`, `PayloadTooLargeError`
- source: `dms/sdk/types.py:15-64`, `dms/sdk/errors.py:41`
- test: `test_dms/test_sdk_stream_upload_contract.py::test_stream_upload_enforces_declared_size_and_rolls_back`

<a id="example-e04"></a>
## E-04. public metadata와 privileged metadata

일반 application flow에는 public metadata를 사용한다. `DocumentMetadata`는 `storage_key`를 포함하므로 명시적인 internal/recovery 작업에서만 요청한다.

```python
from dms import (
    DocumentMetadata,
    PublicDocumentMetadata,
    UploadDocumentRequest,
    UploadDocumentResult,
    public_metadata,
)

public: PublicDocumentMetadata = sdk.get_document_metadata("hello-001")
internal: DocumentMetadata = sdk.get_internal_document_metadata("hello-001")

assert not hasattr(public, "storage_key")
assert isinstance(internal.storage_key, str)

safe_again = public_metadata(internal)
assert isinstance(safe_again, PublicDocumentMetadata)
assert not hasattr(safe_again, "storage_key")

upload_result: UploadDocumentResult = sdk.upload_document(
    UploadDocumentRequest(
        content=b"metadata payload",
        filename="metadata.txt",
        content_type="text/plain",
        metadata={"owner_label": "example"},
    )
)
assert not hasattr(upload_result.metadata, "storage_key")
```

`metadata`의 업무 schema는 DMS가 정의하지 않는다. caller가 넣은 값은 `extra_metadata`로 보존되며, secret·개인정보·외부 JSON schema의 유효성은 host가 책임진다. `public_metadata()`는 public projection 경계를 명확히 할 때 사용한다.

### 추적성

- API: `DocumentMetadata`, `PublicDocumentMetadata`, `UploadDocumentResult`, `public_metadata`
- source: `dms/domain/models.py:40`, `dms/sdk/types.py:66-112`
- test: `test_dms/test_sdk_public_contract.py::test_default_metadata_and_upload_results_hide_storage_key`

<a id="example-e05"></a>
## E-05. cursor page, iterator, user scope

일반 목록은 cursor page를 반환한다. 다음 조회에는 이전 page의 `next_cursor`와 같은 조건을 사용해야 하며, cursor는 opaque 값으로 취급한다.

```python
from dms import AccessContext, DocumentStatus, ValidationError

alice = AccessContext(user_id="alice", tenant="tenant-a")

first = sdk.list_documents(
    limit=50,
    status=DocumentStatus.AVAILABLE,
    access_context=alice,
)
items = list(first.items)

while first.next_cursor is not None:
    first = sdk.list_documents(
        cursor=first.next_cursor,
        limit=50,
        status=DocumentStatus.AVAILABLE,
        access_context=alice,
    )
    items.extend(first.items)

# Iterator는 같은 page 조건을 내부에서 유지한다.
for metadata in sdk.iter_documents(
    status=DocumentStatus.AVAILABLE,
    page_size=50,
    access_context=alice,
):
    consume(metadata.document_id, metadata.user_id)

try:
    # 다른 status 또는 user scope로 이전 cursor를 재사용하지 않는다.
    sdk.list_documents(
        cursor="opaque-cursor-from-another-query",
        status=DocumentStatus.FAILED,
        access_context=alice,
    )
except ValidationError:
    recover_with_a_fresh_cursor()
```

user scope가 있는 access context는 list filtering 전에 적용된다. 따라서 접근 불가능한 문서를 먼저 page에 포함한 뒤 제거하는 방식이 아니며, `has_more`와 cursor도 같은 scope 결과를 반영한다.

### 추적성

- API: `AccessContext`, `DocumentStatus`, `DocumentPage`, `DocumentLister`, `ValidationError`
- source: `dms/sdk/contracts.py:66-81,204`, `dms/sdk/types.py:367`, `dms/sdk/errors.py:27`
- test: `test_dms/test_sdk_pagination.py::test_cursor_page_is_stable_opaque_and_status_bound`

<a id="example-e06"></a>
## E-06. content stream, async stream, sink copy

content를 한 번에 메모리에 받거나 stream으로 읽을 수 있다. SDK가 연 source stream은 SDK가 닫고, `copy_document_to()`의 caller sink는 닫지 않는다.

```python
from io import BytesIO

from dms import AsyncDocumentContentStream, DocumentContentStream, DocumentCopyResult

content = sdk.get_document_content("hello-001")
assert content.content

sync_stream: DocumentContentStream = sdk.get_document_content_stream(
    "hello-001",
    chunk_size=1024,
)
with sync_stream:
    body = b"".join(sync_stream.iter_chunks())
assert sync_stream.closed is True

sink = BytesIO()
copy_result: DocumentCopyResult = sdk.copy_document_to(
    "hello-001",
    sink,
    chunk_size=1024,
    verify_checksum=True,
)
assert sink.closed is False
assert copy_result.checksum_verified is True


async def read_async_stream(async_sdk):
    stream: AsyncDocumentContentStream = (
        await async_sdk.get_document_content_async_stream("hello-001", chunk_size=1024)
    )
    async with stream:
        body = b"".join(
            [chunk async for chunk in stream.aiter_chunks_closing()]
        )
    return body
```

`iter_document_chunks()`는 sync facade에서 sync iterator를, async facade에서 async iterator를 반환한다. 정상 소진, read error, 명시적인 iterator stop, context 종료 및 cancellation에서 SDK 소유 stream이 정리된다.

### 추적성

- API: `DocumentContent`, `DocumentContentStream`, `AsyncDocumentContentStream`, `DocumentCopyResult`
- source: `dms/sdk/types.py:145-250`, `dms/sdk/contracts.py:144`
- test: `test_dms/test_sdk_contract_completion.py::test_sync_closing_iterator_closes_on_exhaustion_and_explicit_early_stop`, `test_dms/test_sdk_feedback_async_cursor.py::test_async_download_stream_closes_on_context_exit_and_exhaustion`

<a id="example-e07"></a>
## E-07. soft/hard delete와 data reset

삭제는 기본적으로 logical delete이며, hard delete는 metadata까지 제거한다. reset은 DMS가 관리하는 metadata, object, upload operation record를 대상으로 한다.

```python
from dms import DataResetError, DeleteDocumentResult, DocumentStatus

soft: DeleteDocumentResult = sdk.soft_delete_document("hello-001")
assert soft.status is DocumentStatus.DELETED
assert soft.hard_deleted is False

hard: DeleteDocumentResult = sdk.hard_delete_document("another-document")
assert hard.hard_deleted is True

try:
    reset = sdk.clear_all_data()
    assert reset.ready_for_data_load is True
except DataResetError as exc:
    # 다른 store cleanup은 계속되므로 부분 결과를 확인한다.
    print(exc.failed_stores, exc.result.to_dict())

ready = sdk.initialize_for_data_load()
assert ready.ready_for_data_load is True
```

user-scoped facade에서 reset을 호출하면 context의 user scope에 속한 데이터만 대상으로 한다. 전체 tenant/application reset은 명시적인 unscoped SDK와 host authorization boundary에서 수행한다.

### 추적성

- API: `DeleteDocumentResult`, `DataResetResult`, `DataResetError`, `DocumentStatus`, `DataResetter`
- source: `dms/sdk/types.py:309-365`, `dms/sdk/errors.py:92`, `dms/sdk/contracts.py:226`
- test: `test_dms/test_sdk_data_reset.py::test_clear_all_data_removes_documents_objects_and_upload_operations`

<a id="example-e08"></a>
## E-08. idempotency operation 조회

idempotency는 `(scope, idempotency_key)`를 기준으로 한다. 같은 scope/key에는 동일한 fingerprint의 upload만 재사용할 수 있다.

```python
from dms import (
    IdempotencyConflictError,
    IdempotencyInProgressError,
    UploadDocumentRequest,
    UploadOperationNotFoundError,
)

request = UploadDocumentRequest(
    content=b"idempotent payload",
    filename="idempotent.txt",
    content_type="text/plain",
    idempotency_scope="tenant-a",
    idempotency_key="import-0001",
)

try:
    first = sdk.upload_document(request)
except IdempotencyInProgressError:
    # 다른 worker가 같은 operation을 처리 중이다.
    first = None
except IdempotencyConflictError:
    # 같은 key에 다른 request fingerprint를 사용한 경우다.
    reject_duplicate_request()

operation = sdk.get_upload_operation(
    scope="tenant-a",
    idempotency_key="import-0001",
)
assert operation.scope == "tenant-a"

try:
    sdk.get_upload_operation(scope="tenant-a", idempotency_key="missing")
except UploadOperationNotFoundError:
    operation = None
```

scoped facade에서는 `idempotency_scope`를 context에서 기본값으로 공급할 수 있다. user scope가 있는 경우 operation 조회도 같은 user namespace를 사용한다. persistent replay/conflict의 focused test coverage가 없는 점은 API Reference trace matrix에서 source-only gap으로 공개되어 있다.

### 추적성

- API: `UploadOperationResult`, `IdempotencyConflictError`, `IdempotencyInProgressError`, `UploadOperationNotFoundError`
- source: `dms/sdk/types.py:125`, `dms/sdk/errors.py:113-128`
- test: `test_dms/test_sdk_factory_integration.py::test_factory_isolates_multiple_users_across_postgres_and_minio` (integration), error structure contract test

<a id="example-e09"></a>
## E-09. inspection과 dry-run recovery

recovery는 먼저 inspection 또는 bounded dry-run으로 대상을 고정한 뒤 실행한다. `execute_reconciliation_plan()`은 실행 직전에 stale item을 다시 검증한다.

```python
from dms import (
    DocumentInspection,
    DocumentStatus,
    RecoveryAction,
    RecoveryIssue,
    ReconciliationPlan,
    ReconciliationResult,
)

inspection: DocumentInspection = sdk.inspect_document("failed-document")
if inspection.issue is RecoveryIssue.METADATA_MISSING:
    # metadata가 없으므로 일반 content read의 not-found와 구분한다.
    record_orphan(inspection.document_id)

preview = sdk.reconcile_documents(
    status=DocumentStatus.FAILED,
    action=RecoveryAction.MARK_FAILED,
    limit=100,
    dry_run=True,
    actor="recovery-admin",
)
plan: ReconciliationPlan = preview.to_plan()

executed = sdk.execute_reconciliation_plan(
    plan,
    actor="recovery-admin",
)
for item in executed.items:
    item_result: ReconciliationResult = item
    if item_result.error_type is not None:
        report_failure(item_result.document_id, item_result.error_type)
```

`PURGE_ORPHAN_OBJECT`는 metadata가 없고 정확한 `storage_key`가 있는 item에만 사용한다. `COMPLETE_DELETION_SOFT/HARD`는 metadata와 object 상태를 재검증한다. `recovery_audit_hook`을 등록하면 audit event를 받을 수 있지만 hook 실패는 reconciliation result를 바꾸지 않는다.

### 추적성

- API: `DocumentInspection`, `RecoveryIssue`, `RecoveryAction`, `ReconciliationPlan`, `ReconciliationResult`, `BatchReconciliationResult`, `RecoveryAuditEvent`
- source: `dms/sdk/types.py:391-560`
- test: `test_dms/test_sdk_reconciliation.py::test_dry_run_exports_plan_and_execution_revalidates_stale_items_with_best_effort_audit`

<a id="example-e10"></a>
## E-10. access policy, scoped facade, protocols, observer

host는 `DocumentAccessPolicy`로 tenant/user authorization을 주입하고, `DmsOperationContext`로 반복되는 access와 audit 기본값을 묶을 수 있다. policy에는 public metadata만 전달된다.

```python
from dms import (
    AccessContext,
    DataResetter,
    DmsOperationContext,
    DocumentAccessPolicy,
    DocumentDeleter,
    DocumentManagementClient,
    DocumentManagementSDKFactory,
    DocumentWriter,
    OperationEvent,
    OperationObserver,
)

class TenantPolicy:
    def allows(self, *, operation, context, metadata):
        del operation
        if context is None:
            return metadata is None
        return metadata is None or metadata.user_id == context.user_id


events: list[OperationEvent] = []
policy: DocumentAccessPolicy = TenantPolicy()
observer: OperationObserver = events.append

sdk = DocumentManagementSDKFactory(
    engine=application.engine,
    minio_client=application.minio_client,
    bucket_name=application.bucket_name,
    access_policy=policy,
    operation_observer=observer,
).create()
scoped = sdk.scoped(
    DmsOperationContext(
        access=AccessContext(user_id="alice", tenant="tenant-a"),
        user_id="alice",
        created_by="alice",
        idempotency_scope="tenant-a",
        audit_actor="alice",
        default_metadata={"tenant": "tenant-a"},
    )
)

client: DocumentManagementClient = scoped
writer: DocumentWriter = client
deleter: DocumentDeleter = client
resetter: DataResetter = client

writer.upload_file("alice.txt")
for metadata in client.iter_documents():
    assert metadata.user_id == "alice"
```

위 예제의 실제 factory에 `access_policy=policy`, `operation_observer=observer`를 전달한다. scoped facade에서 작업 인자에 `access_context`를 다시 전달하지 않으며, 명시적인 `created_by`/metadata는 context 기본값보다 우선한다. 다른 user의 document ID로 read/delete/recovery를 시도하면 `AccessDeniedError`다.

### 추적성

- API: `AccessContext`, `DmsOperationContext`, `DocumentAccessPolicy`, `DocumentManagementClient`, `DocumentWriter`, `DocumentDeleter`, `DataResetter`, `OperationEvent`, `OperationObserver`, `ScopedDocumentManagementSDK`
- source: `dms/sdk/contracts.py:66-237`, `dms/sdk/implementation.py:1012`
- test: `test_dms/test_sdk_consumer_integration_contracts.py::test_access_policy_filters_before_paging_and_covers_privileged_reads`, `test_dms/test_sdk_consumer_integration_contracts.py::test_operation_observer_receives_safe_success_and_failure_events`

<a id="example-e11"></a>
## E-11. async facade와 async iterator

async facade는 native async factory 또는 기존 sync SDK compatibility wrapper에서 얻는다. async method는 `await`, async iterator는 `async for`를 사용한다.

```python
from dms import (
    AsyncDocumentManagementSDK,
    AsyncDocumentManagementSDKFactory,
    DmsOperationContext,
    UploadDocumentRequest,
)

async def use_native_factory():
    factory = AsyncDocumentManagementSDKFactory(
        engine=application.async_engine,
        minio_client=application.minio_client,
        bucket_name=application.bucket_name,
    )
    sdk = await factory.create_async()

    uploaded = await sdk.upload_document(
        UploadDocumentRequest(
            content=b"async payload",
            filename="async.txt",
            content_type="text/plain",
            document_id="async-001",
        )
    )
    page = await sdk.list_documents(limit=10)
    listed = [item async for item in sdk.iter_documents(page_size=10)]
    content = await sdk.get_document_content(uploaded.document_id)
    copied = await sdk.copy_document_to(uploaded.document_id, application.open_sink())

    scoped = sdk.scoped(DmsOperationContext(user_id="alice"))
    await scoped.get_document_metadata(uploaded.document_id)
    return page, listed, content, copied


async def wrap_existing_sync_sdk(sync_sdk):
    sdk = AsyncDocumentManagementSDK(sync_sdk)
    sdk = await sdk  # awaitable compatibility facade가 ready를 기다린다.
    return await sdk.get_document_metadata("sync-document")
```

native async factory의 `create()`를 직접 await하는 것도 가능하지만, 즉시 ready 상태가 필요하면 `create_async()`가 명확하다. SDK의 async facade와 stream은 host의 event loop를 사용하며 전역 close를 호출하지 않는다.

### 추적성

- API: `AsyncDocumentManagementSDK`, `AsyncScopedDocumentManagementSDK`, `AsyncDocumentManagementSDKFactory`, `AsyncDocumentContentStream`
- source: `dms/sdk/async_sdk.py:103-165,569`, `dms/sdk/factory.py:115-169`
- test: `test_dms/test_sdk_consumer_integration_contracts.py::test_async_high_level_operations_preserve_sync_contracts`, `test_dms/test_sdk_multi_user.py::test_async_scoped_facade_preserves_user_isolation`

<a id="example-e12"></a>
## E-12. 구조화된 error 처리

DMS 오류는 Python exception이지만 공통 field로 transport와 독립적인 분류를 제공한다. `category`와 `retryable`을 사용하고 class name 문자열에 의존하지 않는다.

```python
from dms import (
    AccessDeniedError,
    ConfigurationError,
    ConsistencyError,
    DataResetError,
    DocumentDeletedError,
    DocumentNotFoundError,
    DmsError,
    IdempotencyConflictError,
    IdempotencyInProgressError,
    MetadataStoreError,
    PayloadTooLargeError,
    StorageError,
    UploadOperationNotFoundError,
    ValidationError,
)

try:
    document = sdk.get_document_content("document-001")
except DocumentDeletedError:
    use_management_or_recovery_path()
except DocumentNotFoundError:
    handle_public_not_found()
except AccessDeniedError:
    audit_denied_request()
except PayloadTooLargeError:
    reject_input()
except IdempotencyInProgressError:
    schedule_operation_poll()
except IdempotencyConflictError:
    reject_reused_key()
except UploadOperationNotFoundError:
    handle_unknown_operation()
except (StorageError, MetadataStoreError) as exc:
    if exc.retryable:
        retry_with_host_policy(exc)
    else:
        escalate(exc)
except (ConsistencyError, DataResetError):
    inspect_and_reconcile()
except (ConfigurationError, ValidationError):
    fix_caller_configuration()
except DmsError as exc:
    log_structured_error(
        code=exc.code,
        category=exc.category,
        retryable=exc.retryable,
        document_id=exc.document_id,
    )
```

`DmsError.diagnosis`에는 backend secret이나 object storage locator를 넣지 않는다. 외부 API가 있다면 host가 DMS error를 자신의 HTTP/RPC error descriptor로 변환한다.

### 추적성

- API: `DmsError` 및 공개 subclass 전체
- source: `dms/sdk/errors.py:6-130`
- test: `test_dms/test_sdk_requirement_feedback.py::test_all_public_sdk_errors_expose_structured_contract`

## 예제와 API page를 함께 읽는 순서

1. 조립 경계는 [E-01](#example-e01) 또는 [E-02](#example-e02)에서 선택한다.
2. upload surface는 [E-03](#example-e03), public metadata는 [E-04](#example-e04)에서 확인한다.
3. 목록과 stream은 [E-05](#example-e05), [E-06](#example-e06)에서 확인한다.
4. 삭제·reset·recovery는 [E-07](#example-e07), [E-09](#example-e09)에서 확인한다.
5. 다중 사용자와 callback은 [E-10](#example-e10), async는 [E-11](#example-e11)에서 확인한다.
6. 예외 boundary는 [E-12](#example-e12)와 API Reference의 오류 표를 함께 사용한다.
