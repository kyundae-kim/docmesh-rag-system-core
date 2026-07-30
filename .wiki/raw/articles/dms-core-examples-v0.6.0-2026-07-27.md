---
source_url: https://github.com/kyundae-kim/dms-core/wiki/Examples-v0.6.0
ingested: 2026-07-27
sha256: 1cdd933d1cd11d75fffaf971bf3ca8ac6db7f1a3305bf2cfc9de9b918743925d
---
# DMS SDK 사용 예제

모든 예제는 package root 공개 API만 사용한다. 저장소 adapter를 직접 구현하는 예제만 애플리케이션 소유 객체를 전제로 한다.

- 정확한 계약: [API 레퍼런스](api.md)
- 환경변수와 소유권: [설정 레퍼런스](config.md)
- 환경 템플릿: [`.env.example`](../.env.example)

## 1. 환경 기반 SDK

```python
import logging

from dms import UploadDocumentRequest, create_sdk_from_environment

with create_sdk_from_environment(logger=logging.getLogger("dms.sdk")) as sdk:
    result = sdk.upload_document(
        UploadDocumentRequest(
            document_id="doc-1",
            content=b"hello world",
            filename="hello.txt",
            content_type="text/plain",
        )
    )
    print(result.metadata.to_dict())
```

PostgreSQL 또는 SQLite 하나와 MinIO 환경변수를 먼저 준비한다. placeholder endpoint를 사용할 때는 startup 상태 확인을 끄고, 실제 배포에서는 연결 가능한 값과 보안 정책을 사용한다.

## 2. 검증된 설정 묶음으로 조립

```python
from docmesh_py_core import load_service_configs

from dms import create_sdk_from_service_configs

configs = load_service_configs(services={"sqlite", "minio"})
with create_sdk_from_service_configs(configs, check_on_startup=True) as sdk:
    print(sdk.check_health())
```

이 경로는 호출 시 프로세스 환경을 다시 읽지 않는다.

## 3. 명시적 component 조립

```python
from dms import create_sdk_from_components

sdk = create_sdk_from_components(
    metadata_store=metadata_store,
    object_store=object_store,
    operation_store=operation_store,
    service_checks={"metadata": metadata_store.check, "object": object_store.check},
    close_callbacks=[metadata_store.close, object_store.close],
    max_file_size=20 * 1024 * 1024,
)
try:
    print(sdk.check_health())
finally:
    sdk.close()
```

이미 생성된 SQLAlchemy Engine과 MinIO client를 사용할 때는 `create_sdk_from_clients(engine=..., minio_client=..., bucket_name=...)`를 사용한다. 주입 자원은 기본적으로 호출자가 소유한다.

## 4. 환경 사전 진단

```python
import os

from dms import diagnose_environment, format_environment_diagnosis

diagnosis = diagnose_environment(dict(os.environ))
if not diagnosis.valid:
    raise RuntimeError(format_environment_diagnosis(diagnosis))

print(diagnosis.metadata_backend, diagnosis.object_backend)
```

연결을 만들지 않으므로 배포 전 검사에 사용할 수 있다. 출력에는 secret 원문이 포함되지 않는다.

## 5. Bytes 업로드와 멱등 재실행

```python
from dms import UploadDocumentRequest

request = UploadDocumentRequest(
    content=b"quarterly report",
    filename="report.txt",
    content_type="text/plain",
    idempotency_key="request-2026-q3",
    idempotency_scope="tenant-a",
)
first = sdk.upload_document(request)
replayed = sdk.upload_document(request)

assert first.created is True
assert replayed.created is False
assert replayed.document_id == first.document_id

operation = sdk.get_upload_operation(
    scope="tenant-a",
    idempotency_key="request-2026-q3",
)
print(operation.state)
```

같은 key에 다른 본문이나 속성을 사용하면 `IdempotencyConflictError`다.

## 6. 동기 stream 업로드

```python
from hashlib import sha256
from io import BytesIO

from dms import (
    UploadDocumentStreamRequest,
    UploadDocumentUnknownSizeStreamRequest,
)

payload = b"known-size payload"
known = BytesIO(payload)
result = sdk.upload_document_stream(
    UploadDocumentStreamRequest(
        stream=known,
        size=len(payload),
        filename="known.bin",
        content_type="application/octet-stream",
        checksum=sha256(payload).hexdigest(),
    )
)
assert not known.closed  # 입력 stream은 호출자 소유

unknown = BytesIO(b"bounded payload")
sdk.upload_document_unknown_size_stream(
    UploadDocumentUnknownSizeStreamRequest(
        stream=unknown,
        max_size=1024 * 1024,
        filename="unknown.bin",
        content_type="application/octet-stream",
    )
)
assert not unknown.closed
```

알 수 없는 크기의 요청에는 caller checksum 필드가 없으며 SDK가 bounded spool 뒤 checksum을 계산한다.

## 7. 비동기 stream 업로드

```python
import asyncio

from dms import (
    AsyncUploadDocumentStreamRequest,
    AsyncUploadDocumentUnknownSizeStreamRequest,
)


class AsyncReader:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.offset = 0

    async def read(self, size: int = -1) -> bytes:
        await asyncio.sleep(0)
        if self.offset >= len(self.payload):
            return b""
        end = len(self.payload) if size < 0 else self.offset + size
        chunk = self.payload[self.offset:end]
        self.offset += len(chunk)
        return chunk


async def upload() -> None:
    payload = b"async payload"
    await sdk.upload_document_async_stream(
        AsyncUploadDocumentStreamRequest(
            stream=AsyncReader(payload),
            size=len(payload),
            filename="async.bin",
            content_type="application/octet-stream",
        )
    )
    await sdk.upload_document_async_unknown_size_stream(
        AsyncUploadDocumentUnknownSizeStreamRequest(
            stream=AsyncReader(payload),
            max_size=1024,
            filename="async-unknown.bin",
            content_type="application/octet-stream",
        )
    )
```

비동기 입력 reader도 호출자 소유다.

## 8. 공개 문서 정보와 커서 목록

```python
from dms import DocumentStatus, public_metadata

metadata = sdk.get_document_metadata("doc-1")
print(metadata.to_dict())

page = sdk.list_documents(limit=50, status=DocumentStatus.AVAILABLE)
for item in page:
    assert not hasattr(item, "storage_key")

if page.next_cursor is not None:
    next_page = sdk.list_documents(
        cursor=page.next_cursor,
        limit=50,
        status=DocumentStatus.AVAILABLE,
    )

internal = sdk.get_internal_document_metadata("doc-1")
safe_copy = public_metadata(internal)
assert not hasattr(safe_copy, "storage_key")
```

`DocumentMetadata`와 internal 조회는 관리·복구 경계에서만 사용한다.

## 9. 본문 다운로드와 stream 정리

```python
content = sdk.get_document_content("doc-1")
print(content.filename, content.size, content.content)

with sdk.get_document_content_stream("doc-1") as streamed:
    for chunk in streamed.iter_chunks(128 * 1024):
        consume(chunk)
```

비동기 다운로드는 반환 coroutine을 먼저 await한다.

```python
async def download() -> None:
    stream = await sdk.get_document_content_async_stream("doc-1")
    async with stream:
        async for chunk in stream.iter_chunks():
            await consume_async(chunk)
```

## 10. 삭제

```python
soft = sdk.soft_delete_document("doc-1")
print(soft.to_dict())

hard = sdk.hard_delete_document("temporary-doc")
assert hard.hard_deleted is True

# 같은 계약을 명시적으로 호출할 수도 있다.
result = sdk.delete_document("another-doc", hard_delete=False)
```

논리 삭제 문서는 일반 조회와 목록에서 숨겨지고 본문 조회 시 `DocumentDeletedError`가 발생한다. 영구 삭제는 복구할 수 없는 작업으로 취급한다.

## 11. 구조화 metadata 검증

```python
from dataclasses import dataclass
from typing import Any, Mapping

from dms import (
    create_sdk_from_components,
    DefaultMetadataPolicy,
    StructuredMetadataValidator,
    UploadDocumentRequest,
)


@dataclass
class InvoiceMetadata:
    schema_version: str
    invoice_number: str


def parse_invoice(value: Mapping[str, Any]) -> InvoiceMetadata:
    if not isinstance(value.get("invoice_number"), str):
        raise ValueError("invoice_number is required")
    return InvoiceMetadata(
        schema_version=str(value["schema_version"]),
        invoice_number=str(value["invoice_number"]),
    )


validator = StructuredMetadataValidator(
    parser=parse_invoice,
    schema_version="1",
    projector=lambda value: {
        "schema_version": value.schema_version,
        "invoice_number": value.invoice_number,
    },
    policy=DefaultMetadataPolicy(max_serialized_bytes=4096, max_depth=4),
)

with create_sdk_from_components(
    metadata_store=metadata_store,
    object_store=object_store,
    metadata_validator=validator,
) as validated_sdk:
    validated_sdk.upload_document(
        UploadDocumentRequest(
            content=b"invoice",
            filename="invoice.txt",
            content_type="text/plain",
            metadata={"schema_version": "1", "invoice_number": "INV-100"},
        )
    )
```

parser가 구조화된 `MetadataValidationIssue` 목록을 제공해야 한다면 `MetadataSchemaValidationError(issues)`를 발생시킨다. `MetadataNormalizer`와 `MetadataValidator`는 custom callable type 표기에 사용할 수 있다.

## 12. 검사, dry-run 복구 계획, 실행

```python
from dms import DocumentStatus, RecoveryAction

inspection = sdk.inspect_document("doc-1")
print(inspection.issue, inspection.consistent)

preview = sdk.reconcile_documents(
    status=DocumentStatus.DELETING,
    action=RecoveryAction.COMPLETE_DELETION_SOFT,
    offset=0,
    limit=100,
    dry_run=True,
    actor="maintenance-job",
)
print(preview.scanned, preview.eligible, preview.failed)

plan = preview.to_plan()
executed = sdk.execute_reconciliation_plan(plan, actor="maintenance-job")
print(executed.applied, executed.skipped)
```

단건은 `reconcile_document(document_id, action, dry_run=True)`를 사용한다. orphan object를 제거하는 명시적 계획에는 `ReconciliationPlan`과 `ReconciliationPlanItem`의 관리용 `storage_key`가 필요할 수 있다. 각 실행은 현재 상태를 다시 검사한다. `RecoveryIssue`, `DocumentInspection`, `ReconciliationResult`, `BatchReconciliationResult`, `RecoveryAuditEvent`는 검사·결과·감사 정보를 구조화한다.

## 13. 상태 확인과 종료

```python
from dms import HealthStatus, ServiceHealth

health: HealthStatus = sdk.check_health()
for service in health.services:
    item: ServiceHealth = service
    print(item.service, item.ok, item.latency_ms, item.error)

sdk.close()
sdk.close()  # 반복 호출 안전
```

`with sdk` 또는 `async with sdk`를 우선 사용하면 예외 종료에서도 정리된다.

## 14. 오류와 권장 HTTP 응답

```python
from dms import (
    ConfigurationError,
    DmsError,
    IdempotencyInProgressError,
    MetadataSchemaValidationError,
    PayloadTooLargeError,
    recommended_http_error,
)

try:
    result = sdk.upload_document(request)
except MetadataSchemaValidationError as exc:
    for issue in exc.issues:
        print(issue.path, issue.code, issue.message)
except PayloadTooLargeError as exc:
    response = recommended_http_error(exc)  # 413
except IdempotencyInProgressError as exc:
    if exc.retryable:
        schedule_retry()
except ConfigurationError as exc:
    if exc.diagnosis is not None:
        print(exc.diagnosis.missing_required_keys)
    response = recommended_http_error(exc)
except DmsError as exc:
    response = recommended_http_error(exc)

if "response" in locals():
    print(response.status, response.body)
```

호스트가 HTTP를 사용하지 않으면 `code`, `category`, `retryable`만으로 분기할 수 있다. `recommended_http_error()`는 전송 계층 편의 기능이며 DMS 예외 자체에 HTTP status를 추가하지 않는다.

## 공개 API 예제 추적표

| 예제 | 다루는 공개 영역 |
| --- | --- |
| 1~3 | 네 factory, SDK lifecycle |
| 4 | `EnvironmentDiagnosis`, 진단·format API |
| 5~7 | 다섯 업로드 요청, 업로드·operation 결과 |
| 8 | 공개·내부 문서 정보, 상태, page, projection |
| 9 | bytes·동기·비동기 본문 결과와 lifecycle |
| 10 | 삭제 결과와 세 삭제 메서드 |
| 11 | metadata protocol, policy, structured validator와 schema 오류 |
| 12 | 모든 복구 enum·모델·메서드와 audit hook 결과 영역 |
| 13 | `HealthStatus`, `ServiceHealth`, 종료 API |
| 14 | 전체 `DmsError` 계층의 공통 분기와 HTTP adapter |
