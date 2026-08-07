---
title: DMS Document Lifecycle
created: 2026-07-27
updated: 2026-08-04
type: concept
tags: [sdk, api, persistence, testing, integration]
sources: [raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md, raw/articles/dms-core-examples-v0.6.0-2026-07-27.md, raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md, raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]
confidence: medium
---

# DMS Document Lifecycle

v0.7.0의 lifecycle은 bytes, 파일 경로, 정확한 크기를 선언한 동기 binary stream을 같은 metadata·size·filename 정책으로 처리하며, 기본 SDK와 scoped/async facade가 같은 작업 의미를 공유한다. 입력 stream은 caller-owned이고, 파일 경로 API가 SDK 내부에서 연 파일은 SDK가 닫는다. SDK가 반환한 download stream은 caller가 context manager·`close()`·`aclose()`로 닫아야 한다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]

## Upload and idempotency

`UploadDocumentRequest`는 비어 있지 않은 bytes, 정규화 가능한 filename/content type, optional document id·metadata·checksum·idempotency scope/key를 받는다. `UploadDocumentStreamRequest`는 양수 `size`와 caller stream을 요구하며 실제 읽은 byte 수가 선언값과 다르면 검증 오류다. bytes/file/known-size stream에는 plan의 `max_file_size`가 공통 적용된다. unknown-size input, async input stream, known-size stream별 checksum·idempotency는 현재 v0.7.0 upload request 계약에 포함되지 않는다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]

bytes idempotency는 영속 `operation_store`와 비어 있지 않은 scope/key가 함께 있어야 한다. 동일 scope/key와 같은 요청은 같은 document ID 및 `created=False`로 replay되고, 다른 fingerprint는 conflict, 기존 pending 작업은 retryable in-progress 오류다. `get_upload_operation()`은 정확한 scope/key로 외부 상태를 조회한다.^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]

업로드는 object를 먼저 저장하고 metadata를 기록한다. metadata 저장 실패 시 object rollback을 시도하며 rollback까지 실패하면 `ConsistencyError`가 된다. 동일 `document_id`는 duplicate 오류다. 결과는 public-safe metadata와 `created` 플래그를 포함한다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]

## Read and stream ownership

작은 본문은 `get_document_content()`로 받고, 큰 본문은 `get_document_content_stream()`, `iter_document_chunks()`, `copy_document_to()`로 소비한다. SDK-owned source stream은 전체 소진·읽기 오류·조기 종료에서 닫히지만 caller-owned sink는 닫지 않는다. 크기 또는 checksum 불일치는 `ConsistencyError`다. async facade는 같은 작업을 awaitable로 제공하고 worker thread에서 sync storage 작업을 실행한다. 이미 시작한 변경 작업이 취소되어도 정합성 경계까지 끝난 뒤 취소를 전파할 수 있으므로, 취소를 곧 성공·rollback 완료로 간주하지 않고 operation/metadata 상태를 확인해야 한다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]

## Read, paginate, and delete

일반 metadata와 목록은 `DELETING`·`DELETED` 문서를 숨긴다. 목록은 `created_at`, `document_id` 내림차순이며 `limit`은 1~1000이다. cursor는 opaque token이고 다음 호출에 동일한 `status`와 `limit`을 전달해야 한다. `iter_documents()`와 recovery iterator는 이 cursor/offset 유지 코드를 facade 내부로 숨긴다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]

기본 삭제는 soft delete이며 `soft_delete_document()`와 `hard_delete_document()`로 의도를 명시할 수 있다. 삭제 중 metadata를 `DELETING`으로 만들고 object를 정리한 뒤 `DELETED` 또는 hard-delete 상태로 마무리한다. object 삭제 실패는 `FAILED`와 `StorageError`, 후속 metadata 실패는 `ConsistencyError`를 남길 수 있다. 전역 `clear_all_data()`와 `initialize_for_data_load()`는 metadata·document object·upload operation records를 포함하는 별도 관리 작업이며, 부분 실패 count와 `ready_for_data_load=False`를 결과에 보존한다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]

## Related pages

- [[dms-core]]
- [[dms-metadata-and-recovery]]
- [[dms-configuration-and-assembly]]
- [[public-api-surface]]
- [[service-health-orchestration]]
- [[applying-dms-core-as-document-storage]]
