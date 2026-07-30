---
title: DMS Metadata and Recovery
created: 2026-07-27
updated: 2026-07-27
type: concept
tags: [sdk, schema, persistence, security]
sources: [raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md, raw/articles/dms-core-examples-v0.6.0-2026-07-27.md]
confidence: medium
---

# DMS Metadata and Recovery

기본 `DefaultMetadataPolicy`는 JSON 호환 값, 문자열 key, 중첩 depth, UTF-8 직렬화 크기와 금지 key를 검증하며 기본 한도는 16,384 bytes와 depth 8이다. `StructuredMetadataValidator`는 schema-version 검사, parser, 선택 projector, 후속 policy 순으로 처리한다. custom validator를 주입하면 factory의 metadata 크기·depth 옵션은 자동 적용되지 않는다.^[raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md]^[raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md]

## Recovery boundary

`inspect_document()`는 문서 부재도 검사 결과로 표현한다. batch reconciliation은 `FAILED` 또는 `DELETING` 문서만 대상으로 하며, dry-run 결과에서 만든 plan을 실행할 때는 현재 상태를 다시 검사한다. `recovery_audit_hook`은 best-effort이므로 hook 실패가 복구 작업 결과를 뒤집지 않는다.^[raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md]

## HTTP adaptation

`recommended_http_error()`는 DMS 오류를 권장 HTTP status와 `code`, `category`, `retryable`, secret-safe message body로 변환한다. 이는 전송 계층 adapter를 위한 helper이며 예외 모델 자체를 HTTP에 결합하지 않는다.^[raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md]

## Related pages

- [[dms-core]]
- [[dms-document-lifecycle]]
- [[public-api-surface]]
- [[user-scope-isolation]]
