---
title: DMS Document Lifecycle
created: 2026-07-27
updated: 2026-08-18
type: concept
tags: [sdk, api, persistence, testing, integration]
sources: [raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md, raw/articles/dms-core-examples-v0.6.0-2026-07-27.md, raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md, raw/articles/dms-core-examples-v0.7.0-2026-08-04.md, raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md, raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]
confidence: medium
---

# DMS Document Lifecycle

v0.9.0 lifecycle은 bytes, 파일 경로, 정확한 크기를 선언한 동기 binary stream을 같은 metadata·size·filename 정책으로 처리하며, 기본·scoped·async facade가 같은 작업 의미를 공유한다. 입력 stream은 caller-owned이고, SDK가 내부에서 연 file과 반환한 content stream은 SDK가 정리한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

## Upload and idempotency

`UploadDocumentRequest`는 비어 있지 않은 bytes, filename, content type, optional document id·metadata·created_by·checksum·idempotency scope/key를 받는다. `UploadDocumentStreamRequest`는 양수 `size`와 caller stream을 요구하며 실제 읽은 byte 수가 선언값과 다르면 object cleanup 뒤 `ValidationError`다. `max_file_size`는 bytes/file/known-size stream에 공통 적용되고, unknown-size stream과 async input stream upload는 현재 공개 API가 아니다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]

metadata의 타입은 `object`이며 DMS가 업무 schema·보안 규칙·정규화·JSON 직렬화를 정의하거나 검증하지 않는다. metadata는 upload idempotency fingerprint에서 제외되므로 외부 응답이나 메시지로 내보낼 때의 serialization과 secret 검사는 host 책임이다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

persistent `operation_store`가 있고 scope/key가 있으면 같은 fingerprint의 upload는 같은 document ID와 `created=False`로 replay된다. 다른 fingerprint는 `IdempotencyConflictError`, pending operation은 `IdempotencyInProgressError`, 없는 기록은 `UploadOperationNotFoundError`다. direct component assembly에서 operation store를 생략하면 idempotency upload와 operation 조회는 `ValidationError`다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]

## Read and stream ownership

작은 본문은 `get_document_content()`로 받고, 큰 본문은 `get_document_content_stream()`, `iter_document_chunks()`, `copy_document_to()`로 소비한다. `iter_chunks()`는 자동 close 계약이 아니며, `iter_chunks_closing()`은 정상 소진·read error·명시적 iterator close에서 SDK-owned source를 정리한다. `copy_document_to()`는 checksum과 저장 크기를 검증하고 caller-owned sink는 닫지 않는다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

async facade는 작업을 awaitable로 제공하고 `iter_documents`·`iter_recovery_candidates`·`iter_document_chunks`는 async iterator다. async content stream은 정상 소진·read error·cancellation·context 종료에서 source를 정리한다. 상태 변경 작업이 취소되어도 이미 시작한 worker가 안전한 완료 경계에 도달한 뒤 `CancelledError`를 전달할 수 있으므로, 취소를 rollback 완료로 간주하지 않고 metadata/operation 상태를 확인한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]

## Read, paginate, and scope

일반 metadata와 목록은 `DELETING`·`DELETED` 문서를 숨긴다. 목록은 `created_at`과 immutable `document_id`의 안정적인 내림차순 cursor 순서이며 `limit`은 1~1000이다. cursor는 opaque이고 status filter와 page size에 결합되므로 다음 호출에 같은 조건을 전달해야 한다. 일반 문서 목록에는 offset API가 없다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

`DmsOperationContext`는 access context, created_by, idempotency scope, audit actor, default metadata를 scoped facade의 기본값으로 제공한다. 작업에 명시한 값이 context 기본값보다 우선하고, scoped facade는 shared SDK lifecycle을 소유하지 않는다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]

## Delete and reset

기본 `delete_document()`는 soft delete이며 `soft_delete_document()`·`hard_delete_document()`로 의도를 명시할 수 있다. object 삭제 실패는 metadata를 best-effort로 `FAILED`로 전환한 뒤 `StorageError`가 될 수 있고, object 삭제 뒤 metadata 처리 실패는 `ConsistencyError`로 남을 수 있다. `clear_all_data()`와 `initialize_for_data_load()`는 metadata, `documents/` prefix object, upload operation record를 대상으로 하며 한 store 실패 뒤에도 가능한 cleanup을 계속한다. 부분 실패는 `DataResetError.result`, `errors`, `failed_stores`, `ready_for_data_load=False`로 확인한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

## Related pages

- [[dms-core]]
- [[dms-metadata-and-recovery]]
- [[dms-configuration-and-assembly]]
- [[public-api-surface]]
- [[user-scope-isolation]]
- [[applying-dms-core-as-document-storage]]
