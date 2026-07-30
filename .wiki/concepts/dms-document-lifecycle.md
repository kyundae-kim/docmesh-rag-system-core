---
title: DMS Document Lifecycle
created: 2026-07-27
updated: 2026-07-27
type: concept
tags: [sdk, api, persistence, testing]
sources: [raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md, raw/articles/dms-core-examples-v0.6.0-2026-07-27.md]
confidence: medium
---

# DMS Document Lifecycle

`dms-core`의 문서 lifecycle은 bytes, 알려진 크기의 동기·비동기 stream, 크기를 모르는 bounded stream 업로드를 하나의 metadata 정규화·검증 정책으로 처리한다. 입력 stream은 호출자 소유이고 SDK가 반환한 download stream은 호출자가 닫는다. SDK 자체는 동기·비동기 context manager이며 `close()`와 `aclose()`는 반복 호출해도 안전하다.^[raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md]

## Upload and idempotency

알려진 크기 stream은 실제 byte 수가 선언값과 같아야 하며 checksum을 제공하면 SHA-256과 일치해야 한다. `idempotency_key`에는 명시적 scope가 필요하고, 같은 scope/key의 동일 요청은 기존 결과와 `created=False`를 반환한다. 다른 요청은 conflict, 진행 중 요청은 retry 가능한 in-progress 오류로 구분된다.^[raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md]

## Read, paginate, and delete

일반 metadata 조회와 목록은 `DELETING`·`DELETED` 문서를 숨기며, 내부 관리 조회만 저장 위치를 포함한다. 목록 cursor는 정렬·상태 filter·page 크기에 결합된 opaque token이므로 다음 page에서도 동일한 `status`와 `limit`을 유지해야 한다. 기본 삭제는 soft delete이고 hard delete는 복구 불가능한 관리 작업이다.^[raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md]^[raw/articles/dms-core-examples-v0.6.0-2026-07-27.md]

## Related pages

- [[dms-core]]
- [[dms-metadata-and-recovery]]
- [[public-api-surface]]
- [[service-health-orchestration]]
