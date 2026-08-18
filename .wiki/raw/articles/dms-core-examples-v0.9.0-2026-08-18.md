---
source_url: https://github.com/kyundae-kim/dms-core/wiki/Examples-v0.9.0
ingested: 2026-08-18
sha256: babb5f47d35759d7b7062bea9ee09a75b11cd31b08d8ad972b580cbb98b5c98d
---
# DMS SDK 사용 예제 (v0.9.0)

- API 기준: [API-Reference-v0.9.0](API-Reference-v0.9.0.md)
- 기준 소스: `dms-core` commit `f7a40f1` (`develop-v0.8.0`, package version `0.9.0`)
- 목적: 현재 package root 공개 API를 실제 호출 흐름과 연결하고, 각 예제를 API 추적성 매트릭스의 source/test 근거로 되돌아가게 하는 것

> 아래 예제의 `application`, `engine`, `minio_client`, `metadata_store`, `object_store`, `operation_store`, `consume`, `application.record_*`는 host 애플리케이션이 준비하는 값이다. DMS는 독립 실행형 API 서버가 아니며, 예제가 client/component를 자동으로 만들지 않는다.

> SDK는 host가 제공한 engine, MinIO client, storage component를 생성하거나 종료하지 않는다. SDK가 upload 중 직접 연 file과 SDK가 반환한 content stream은 SDK가 정리하지만, caller가 제공한 input stream과 output sink는 caller가 닫는다.

## 예제와 공개 API 추적

| 예제 ID | 시나리오 | 주요 공개 API | API 문서 추적 |
| --- | --- | --- | --- |
| [E-01](#example-e01) | factory 조립과 기본 upload | `DocumentManagementSDKFactory`, `UploadDocumentRequest` | `TR-ASM`, `TR-UPL` |
| [E-02](#example-e02) | component 직접 조립과 소유권 | `DefaultDocumentManagementSDK` | `TR-ASM`, `TR-POLICY` |
| [E-03](#example-e03) | bytes/file/known-size stream upload | upload request/result, `PayloadTooLargeError` | `TR-UPL`, `TR-ERR` |
| [E-04](#example-e04) | public/internal metadata projection | `PublicDocumentMetadata`, `DocumentMetadata`, `public_metadata` | `TR-DATA` |
| [E-05](#example-e05) | cursor page와 iterator | `DocumentPage`, `DocumentStatus`, `DocumentLister` | `TR-READ`, `TR-DATA`, `TR-CONTRACT` |
| [E-06](#example-e06) | sync/async content stream과 sink copy | content stream, `DocumentCopyResult` | `TR-READ`, `TR-ASYNC` |
| [E-07](#example-e07) | soft/hard delete와 data reset | delete/reset result, `DataResetError` | `TR-DEL`, `TR-RESET` |
| [E-08](#example-e08) | idempotency scope/key와 operation 조회 | `UploadOperationResult`, idempotency errors | `TR-UPL`, `TR-ERR` |
| [E-09](#example-e09) | inspection, dry-run, plan execution | recovery enum/result/plan, `RecoveryAuditEvent` | `TR-REC`, `TR-OBS` |
| [E-10](#example-e10) | access policy, scoped context, observer, protocol | policy/context/observer/capability protocols | `TR-POLICY`, `TR-CONTRACT`, `TR-OBS` |
| [E-11](#example-e11) | async facade와 async scoped facade | async facades, async stream, async iterator | `TR-ASYNC` |
| [E-12](#example-e12) | stable SDK error 처리 | `DmsError` hierarchy | `TR-ERR` |

<a id="example-e01"></a>

## E-01. factory 조립과 기본 upload

host가 만든 SQLAlchemy `Engine`과 MinIO client를 factory에 전달한다. factory는 dialect에 맞는 adapter와 upload operation store를 조립한다.

```python
from dms import DocumentManagementSDKFactory, UploadDocumentRequest

factory = DocumentManagementSDKFactory(
    engine=application.sqlalchemy_engine,
    minio_client=application.minio_client,
    bucket_name="documents",
)
sdk = factory.create()

result = sdk.upload_document(
    UploadDocumentRequest(
        content=b"hello dms",
        filename="hello.txt",
        content_type="text/plain",
        metadata={"source": "quick-start"},
    )
)

metadata = sdk.get_document_metadata(result.document_id)
print(result.document_id)
print(metadata.status.value)
```

`engine.dialect.name`은 `postgresql` 또는 `sqlite`여야 한다. 지원하지 않는 dialect는 `ConfigurationError`다. `bucket_name`은 공백만으로 구성될 수 없다. `engine`과 MinIO client는 host 소유이므로 SDK를 다 쓴 후 SDK에 `close()`를 호출하지 않는다.

<a id="example-e02"></a>

## E-02. component 직접 조립과 소유권

이미 host가 준비한 metadata/object component를 직접 주입할 수 있다. component의 구체 class는 package root 공개 API가 아니며, host adapter가 structural contract를 만족하면 된다.

```python
from dms import DefaultDocumentManagementSDK, UploadDocumentRequest

sdk = DefaultDocumentManagementSDK(
    metadata_store=application.metadata_store,
    object_store=application.object_store,
    max_file_size=25 * 1024 * 1024,
    operation_store=application.upload_operation_store,
)

result = sdk.upload_document(
    UploadDocumentRequest(
        content=b"component payload",
        filename="component.txt",
        content_type="text/plain",
    )
)

# metadata_store/object_store/operation_store의 생성과 종료는 host가 담당한다.
print(result.metadata.file_size)
```

`operation_store`를 생략한 직접 조립에서는 idempotency key upload와 operation 조회를 사용할 수 없다. `max_file_size`는 bytes, file path, known-size stream에 공통 적용된다. SDK facade에는 전역 lifecycle method가 없다.

<a id="example-e03"></a>

## E-03. bytes, file, known-size stream upload

현재 공개 upload 입력은 bytes, file path, 정확한 크기를 선언한 동기 binary stream 세 가지다. application-owned metadata는 DMS가 schema나 보안 규칙으로 해석하지 않는다.

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
        metadata="caller-owned value",
    )
)

file_result = sdk.upload_file(
    Path("payload.pdf"),
    filename="renamed.pdf",
    content_type="application/pdf",
    metadata={"import": "file"},
)

payload = b"stream payload"
source = BytesIO(payload)
stream_result = sdk.upload_document_stream(
    UploadDocumentStreamRequest(
        stream=source,
        size=len(payload),
        filename="stream.txt",
        content_type="text/plain",
        metadata=["stream", "owned"],
    )
)

assert bytes_result.created is True
assert file_result.document_id
assert stream_result.metadata.file_size == len(payload)
assert source.closed is False  # caller가 제공한 input stream

try:
    sdk.upload_document(
        UploadDocumentRequest(
            content=b"too large",
            filename="large.bin",
            content_type="application/octet-stream",
        )
    )
except PayloadTooLargeError as error:
    print(error.code, error.retryable)
```

stream의 선언 크기와 실제 읽은 크기가 다르면 storage에 기록된 object를 정리한 뒤 `ValidationError`를 반환한다. unknown-size stream과 async input stream upload는 현재 공개 API가 아니다. `upload_file()`은 SDK가 파일을 열고 닫는다.

<a id="example-e04"></a>

## E-04. public metadata와 내부 metadata의 분리

일반 consumer 응답은 `storage_key`가 없는 `PublicDocumentMetadata`다. storage locator가 필요한 관리·복구 작업에서만 내부 모델을 명시적으로 요청한다.

```python
from dms import (
    DocumentMetadata,
    PublicDocumentMetadata,
    public_metadata,
)

public = sdk.get_document_metadata(bytes_result.document_id)
assert isinstance(public, PublicDocumentMetadata)
assert not hasattr(public, "storage_key")

internal = sdk.get_internal_document_metadata(bytes_result.document_id)
assert isinstance(internal, DocumentMetadata)
assert internal.storage_key

public_copy = public_metadata(internal)
assert isinstance(public_copy, PublicDocumentMetadata)
assert not hasattr(public_copy, "storage_key")

# 호환 dump는 extra_metadata, canonical external dump는 metadata를 사용한다.
print(public.to_dict())
print(public.to_public_dict())
print(public.model_json_schema())
```

`DocumentMetadata`를 일반 HTTP 응답, operation event, tenant callback에 그대로 전달하지 않는다. `to_public_dict()` 또는 `public_metadata()`를 사용한다. metadata 값이 JSON encoder가 지원하지 않는 opaque 값이면 host가 자신의 직렬화 정책을 적용해야 한다.

<a id="example-e05"></a>

## E-05. cursor page와 metadata iterator

일반 문서 목록은 opaque cursor를 사용한다. 다음 page에는 이전 응답의 cursor를 같은 상태 filter와 page size로 전달한다.

```python
from dms import DocumentStatus

page = sdk.list_documents(
    limit=100,
    status=DocumentStatus.AVAILABLE,
)

while True:
    for item in page.items:
        print(item.document_id, item.original_filename)

    if not page.has_more:
        break

    page = sdk.list_documents_page(
        cursor=page.next_cursor,
        limit=100,
        status=DocumentStatus.AVAILABLE,
    )

# page 자체도 items를 순회할 수 있다.
for item in sdk.list_documents_page(status=DocumentStatus.AVAILABLE):
    print(item.document_id)

# cursor loop를 SDK에 맡기는 iterator
for item in sdk.iter_documents(
    status=DocumentStatus.AVAILABLE,
    page_size=100,
):
    print(item.document_id)
```

`limit`는 1~1000이다. cursor는 status filter와 page size에 결합되어 있으므로 다른 조건에 재사용하거나 직접 해석하지 않는다. 삭제 중인 문서는 일반 목록에서 숨겨진다. 일반 목록에는 offset API가 없다.

<a id="example-e06"></a>

## E-06. sync/async content stream과 sink copy

### Sync content stream

```python
from io import BytesIO

from dms import DocumentCopyResult

content = sdk.get_document_content_stream(
    bytes_result.document_id,
    chunk_size=64 * 1024,
)

with content:
    for chunk in content.iter_chunks():
        consume(chunk)

# iterator 자체에서 정상 소진·오류·명시적 iterator close 시 close하려면 closing variant를 사용한다.
for chunk in sdk.get_document_content_stream(
    bytes_result.document_id,
).iter_chunks_closing():
    consume(chunk)

# sink는 caller 소유이며 SDK가 닫지 않는다.
sink = BytesIO()
copy_result = sdk.copy_document_to(
    bytes_result.document_id,
    sink,
    verify_checksum=True,
)
assert isinstance(copy_result, DocumentCopyResult)
assert copy_result.bytes_copied == len(sink.getvalue())
assert copy_result.checksum_verified is True
assert sink.closed is False
```

### Async content stream

```python
from dms import AsyncDocumentContentStream

async def download_async(async_sdk, document_id: str) -> bytes:
    content = await async_sdk.get_document_content_stream(
        document_id,
        chunk_size=64 * 1024,
    )
    assert isinstance(content, AsyncDocumentContentStream)

    received = bytearray()
    async with content:
        async for chunk in content.iter_chunks():
            received.extend(chunk)
    return bytes(received)


async def copy_async(async_sdk, document_id: str, sink) -> None:
    result = await async_sdk.copy_document_to(
        document_id,
        sink,
        verify_checksum=True,
    )
    print(result.to_dict())
```

`get_document_content_async_stream()`은 sync facade에서도 명시적으로 async stream을 선택할 때 사용한다. async stream은 정상 소진, read error, cancellation, context 종료에서 source를 정리한다. output sink는 caller가 닫는다.

<a id="example-e07"></a>

## E-07. soft delete, hard delete, data reset

기본 `delete_document()`는 soft delete이며, 명시적인 soft/hard convenience method도 제공한다.

```python
from dms import (
    DataResetError,
    DocumentDeletedError,
    DocumentNotFoundError,
)

deleted = sdk.soft_delete_document(bytes_result.document_id)
assert deleted.deleted is True
assert deleted.hard_deleted is False

try:
    sdk.get_document_content(bytes_result.document_id)
except DocumentDeletedError as error:
    print(error.code, error.document_id)

try:
    sdk.get_document_metadata(bytes_result.document_id)
except DocumentNotFoundError as error:
    print(error.code, error.document_id)

hard_deleted = sdk.hard_delete_document(another_document_id)
assert hard_deleted.hard_deleted is True

try:
    reset = sdk.initialize_for_data_load()
except DataResetError as error:
    # 가능한 store의 cleanup 결과를 예외에서 확인한다.
    print(error.failed_stores)
    print(error.result.ready_for_data_load)
    print(error.result.to_dict())
else:
    print(reset.total_deleted, reset.ready_for_data_load)
    print(reset.to_dict())
```

`clear_all_data()`도 같은 reset 계약을 사용한다. metadata, DMS가 관리하는 `documents/` object prefix, upload operation record를 대상으로 하며, 한 store가 실패해도 다른 store의 정리를 계속 시도한다. host의 다른 bucket/object는 DMS가 관리한다고 가정하지 않는다.

<a id="example-e08"></a>

## E-08. idempotency scope/key와 upload operation 조회

idempotency를 사용하려면 persistent `operation_store`가 필요하다. factory는 engine을 이용해 기본 operation store를 조립하고, 직접 조립할 때는 host가 주입한다.

```python
from dms import (
    DefaultDocumentManagementSDK,
    IdempotencyConflictError,
    IdempotencyInProgressError,
    UploadDocumentRequest,
    UploadOperationNotFoundError,
)

sdk_with_operations = DefaultDocumentManagementSDK(
    metadata_store=metadata_store,
    object_store=object_store,
    operation_store=operation_store,
)

request = UploadDocumentRequest(
    content=b"exactly-once candidate",
    filename="once.txt",
    content_type="text/plain",
    idempotency_scope="tenant-a",
    idempotency_key="import-2026-0001",
)

first = sdk_with_operations.upload_document(request)
replay = sdk_with_operations.upload_document(request)
assert first.document_id == replay.document_id
assert replay.created is False

operation = sdk_with_operations.get_upload_operation(
    scope="tenant-a",
    idempotency_key="import-2026-0001",
)
print(operation.state.value)  # pending/succeeded/failed
print(operation.to_dict())

conflicting_request = UploadDocumentRequest(
    content=b"different bytes",
    filename="once.txt",
    content_type="text/plain",
    idempotency_scope="tenant-a",
    idempotency_key="import-2026-0001",
)
try:
    sdk_with_operations.upload_document(conflicting_request)
except IdempotencyConflictError:
    pass
except IdempotencyInProgressError:
    # 다른 worker가 같은 operation을 아직 처리 중일 수 있다.
    pass

try:
    sdk_with_operations.get_upload_operation(
        scope="tenant-a",
        idempotency_key="missing",
    )
except UploadOperationNotFoundError:
    pass
```

같은 scope/key는 동일한 request fingerprint에만 재사용한다. metadata는 fingerprint에 포함하지 않는다. `UploadOperationState` 자체는 root export가 아니므로 소비자는 `operation.state.value`를 사용한다.

<a id="example-e09"></a>

## E-09. consistency inspection, dry-run, plan execution

복구 API는 먼저 상태를 점검하고, dry-run으로 계획을 확인한 다음 plan을 실행하는 흐름을 권장한다.

```python
from dms import (
    BatchReconciliationResult,
    DocumentStatus,
    RecoveryAction,
    RecoveryAuditEvent,
    RecoveryIssue,
    ReconciliationPlan,
    ReconciliationPlanItem,
)

inspection = sdk.inspect_document(candidate_document_id)
print(inspection.issue.value, inspection.consistent)
print(inspection.to_dict())
if inspection.issue is RecoveryIssue.METADATA_MISSING:
    print("metadata is missing")

candidates = sdk.list_recovery_candidates(
    status=DocumentStatus.FAILED,
    limit=100,
)
for candidate in candidates:
    # 이 모델은 storage_key를 포함하므로 관리 경계를 벗어나지 않게 한다.
    print(candidate.document_id, candidate.storage_key)

preview = sdk.reconcile_documents(
    status=DocumentStatus.FAILED,
    action=RecoveryAction.MARK_FAILED,
    limit=100,
    dry_run=True,
    actor="recovery-job",
)
assert isinstance(preview, BatchReconciliationResult)
plan = preview.to_plan()
assert isinstance(plan, ReconciliationPlan)
print(plan.to_dict())

executed = sdk.execute_reconciliation_plan(
    plan,
    actor="recovery-job",
)
for item in executed.items:
    print(item.document_id, item.applied, item.error_type)

for audit_event in application.recovery_audit_events:
    assert isinstance(audit_event, RecoveryAuditEvent)
    print(audit_event.to_dict())

# host가 plan을 직접 만들 때 status/action과 item action을 일치시킨다.
manual_item = ReconciliationPlanItem(
    document_id=candidate_document_id,
    action=RecoveryAction.COMPLETE_DELETION_SOFT,
)
manual_plan = ReconciliationPlan(
    status=DocumentStatus.DELETING,
    action=RecoveryAction.COMPLETE_DELETION_SOFT,
    items=(manual_item,),
)
result = sdk.execute_reconciliation_plan(manual_plan, actor="operator")
print(result.to_dict())
```

`list_recovery_candidates()`와 `reconcile_documents()`는 `FAILED` 또는 `DELETING`만 허용한다. `PURGE_ORPHAN_OBJECT`는 metadata가 없고 정확한 `storage_key`를 caller가 제공한 경우에만 사용한다. plan은 실행 직전에 각 item을 다시 검사하므로 stale plan을 성공으로 간주하지 않는다.

<a id="example-e10"></a>

## E-10. access policy, scoped context, observer, protocol

### Access policy와 scoped context

```python
from dms import (
    AccessContext,
    DataResetter,
    DefaultDocumentManagementSDK,
    DocumentAccessPolicy,
    DocumentDeleter,
    DocumentManagementClient,
    DocumentReader,
    DocumentWriter,
    DmsOperationContext,
    DocumentLister,
    OperationEvent,
    OperationObserver,
    PublicDocumentMetadata,
    UploadDocumentRequest,
)

class TenantPolicy:
    def allows(
        self,
        *,
        operation: str,
        context: AccessContext | None,
        metadata: PublicDocumentMetadata | None,
    ) -> bool:
        if context is None:
            return False
        if metadata is None:
            return "admin" in context.roles
        return metadata.extra_metadata.get("tenant") == context.tenant

policy: DocumentAccessPolicy = TenantPolicy()
events: list[OperationEvent] = []
observer: OperationObserver = events.append

sdk_with_policy = DefaultDocumentManagementSDK(
    metadata_store=metadata_store,
    object_store=object_store,
    access_policy=policy,
    operation_observer=observer,
)

context = DmsOperationContext(
    access=AccessContext(
        subject="user-42",
        tenant="tenant-a",
        roles=frozenset({"writer"}),
    ),
    created_by="user-42",
    idempotency_scope="tenant-a",
    audit_actor="user-42",
    default_metadata={"tenant": "tenant-a"},
)
scoped = sdk_with_policy.scoped(context)
scoped_result = scoped.upload_document(
    UploadDocumentRequest(
        content=b"scoped payload",
        filename="scoped.txt",
        content_type="text/plain",
    )
)

# Default SDK는 기능별 protocol로 받을 수 있다.
writer: DocumentWriter = sdk_with_policy
reader: DocumentReader = sdk_with_policy
lister: DocumentLister = sdk_with_policy
deleter: DocumentDeleter = sdk_with_policy
resetter: DataResetter = sdk_with_policy
client: DocumentManagementClient = sdk_with_policy

print(reader.get_document_metadata(scoped_result.document_id).document_id)
print(lister.list_documents(limit=10).has_more)
print(events[-1].to_dict())
```

policy callback에는 `PublicDocumentMetadata`만 전달된다. 내부 `DocumentMetadata.storage_key`를 tenant 권한 판단에 사용하지 않는다. reset 같은 전역 작업에서는 policy의 `metadata`가 `None`일 수 있다. scoped 작업에 명시한 값은 context 기본값보다 우선한다.

### Observer callback

observer가 예외를 발생시켜도 원래 document 작업은 성공 또는 원래 오류를 유지한다. event의 `conditions`에 document body나 내부 storage locator를 넣지 않는 운영 경계를 host가 지켜야 한다.

<a id="example-e11"></a>

## E-11. async facade와 async scoped facade

async facade는 sync facade의 public 작업을 awaitable로 제공하며, iterator 작업은 async iterator다.

```python
from dms import (
    AsyncDocumentManagementSDK,
    AsyncDocumentContentStream,
    AsyncScopedDocumentManagementSDK,
    DocumentStatus,
    DmsOperationContext,
    UploadDocumentRequest,
)

async def run_async(factory, document_id: str) -> None:
    async_sdk = factory.create_async()
    assert isinstance(async_sdk, AsyncDocumentManagementSDK)

    result = await async_sdk.upload_document(
        UploadDocumentRequest(
            content=b"async payload",
            filename="async.txt",
            content_type="text/plain",
        )
    )

    metadata = await async_sdk.get_document_metadata(result.document_id)
    print(metadata.to_public_dict())

    async for item in async_sdk.iter_documents(page_size=50):
        print(item.document_id)

    async for item in async_sdk.iter_recovery_candidates(
        status=DocumentStatus.FAILED,
        page_size=50,
    ):
        print(item.document_id)

    content = await async_sdk.get_document_content_async_stream(document_id)
    assert isinstance(content, AsyncDocumentContentStream)
    async with content:
        async for chunk in content.aiter_chunks_closing():
            consume(chunk)

    scoped = async_sdk.scoped(
        DmsOperationContext(
            idempotency_scope="tenant-a",
            audit_actor="async-worker",
        )
    )
    assert isinstance(scoped, AsyncScopedDocumentManagementSDK)
    upload = await scoped.upload_file(
        "async-payload.pdf",
        content_type="application/pdf",
    )
    await scoped.soft_delete_document(upload.document_id)
```

async facade도 SDK가 받은 engine/client/component의 lifecycle을 소유하지 않는다. `async_sdk.close()`나 `async_sdk.aclose()`를 추가하지 않는다. `get_document_content_stream()`과 `get_document_content_async_stream()`은 모두 async stream 반환 경계로 사용할 수 있다.

<a id="example-e12"></a>

## E-12. stable SDK error 처리

transport-specific response로 변환하기 전에 SDK 오류의 stable fields를 보존한다.

```python
from dms import (
    AccessDeniedError,
    ConfigurationError,
    ConsistencyError,
    DataResetError,
    DocumentDeletedError,
    DocumentNotFoundError,
    DmsError,
    DuplicateDocumentError,
    IdempotencyConflictError,
    IdempotencyInProgressError,
    MetadataStoreError,
    PayloadTooLargeError,
    StorageError,
    UploadOperationNotFoundError,
    ValidationError,
)


def handle_sdk_call(call):
    try:
        return call()
    except DataResetError as error:
        return {
            "code": error.code,
            "category": error.category,
            "retryable": error.retryable,
            "failed_stores": error.failed_stores,
            "partial_result": error.result.to_dict(),
        }
    except (
        AccessDeniedError,
        ConfigurationError,
        ConsistencyError,
        DocumentDeletedError,
        DocumentNotFoundError,
        DuplicateDocumentError,
        IdempotencyConflictError,
        IdempotencyInProgressError,
        MetadataStoreError,
        PayloadTooLargeError,
        StorageError,
        UploadOperationNotFoundError,
        ValidationError,
    ) as error:
        return {
            "code": error.code,
            "category": error.category,
            "retryable": error.retryable,
            "document_id": error.document_id,
        }
    except DmsError as error:
        return {
            "code": error.code,
            "category": error.category,
            "retryable": error.retryable,
        }
```

`DataResetError`는 partial result와 failed store를 별도로 처리한다. DMS는 HTTP status/response body를 결정하지 않으므로, host transport가 `code`, `category`, `retryable`, `document_id`와 오류별 추가 field를 자체 응답 규칙으로 매핑한다. 예제에 실제 credential, token, password, storage locator를 넣지 않는다.

## 예제 검증

각 `python` fence는 host 객체가 제공된다는 전제에서 구문이 유효해야 한다. 이 문서의 import는 모두 package-root 공개 이름과 표준 library만 사용한다. 실제 storage round-trip은 host가 준비한 PostgreSQL/SQLite·MinIO 환경에서 별도로 실행한다.

```bash
# dms-core checkout에서
.venv/bin/python -m pytest test_dms -q
```

API surface와 예제 anchor의 1:1 관계는 [API-Reference-v0.9.0의 추적성 매트릭스](API-Reference-v0.9.0.md#10-추적성-매트릭스)에서 확인한다.
