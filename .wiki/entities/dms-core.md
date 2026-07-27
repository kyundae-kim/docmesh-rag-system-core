---
title: dms-core
created: 2026-07-27
updated: 2026-07-27
type: entity
tags: [sdk, python, integration, persistence]
sources: [raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md, raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md, raw/articles/dms-core-examples-v0.6.0-2026-07-27.md, raw/articles/dms-core-env-example-v0.6.0-2026-07-27.md]
confidence: medium
---

# dms-core

`dms-core`는 PostgreSQL 또는 SQLite의 문서 metadata와 MinIO의 본문 객체를 조합해 문서 업로드·조회·삭제·복구를 제공하는 Python SDK다. 공개 소비 경계는 `dms.__all__`이며, 일반 애플리케이션은 `create_sdk_from_environment()`로 조립하고, 이미 검증한 `docmesh_py_core.ServiceConfigs`가 있으면 `create_sdk_from_service_configs()`를 사용한다.^[raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md]^[raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md]

## Integration role

이 SDK는 RAG 시스템에서 원문 문서와 문서 상태를 책임지는 document-management 경계가 될 수 있다. 일반 조회에는 `storage_key`를 숨기는 `PublicDocumentMetadata`를 반환하고, 저장 위치를 포함하는 `DocumentMetadata`와 복구 API는 관리 경계에만 두므로, API/MCP adapter가 내부 object-store 정보를 노출하지 않도록 설계할 수 있다.^[raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md]

## Operational constraints

환경 조립에는 metadata backend 하나와 MinIO가 모두 필요하다. `DMS_METADATA_BACKEND`로 PostgreSQL/SQLite를 명시 선택할 수 있고, auto mode에서 둘 다 감지되면 PostgreSQL을 선택하며 `DMS_CONFIGURATION_STRICT=true`로 이를 거부할 수 있다. 외부 연결 전에는 `diagnose_environment()`로 선택 결과·누락 키·경고를 secret-safe하게 검사할 수 있다.^[raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md]

## Related pages

- [[dms-document-lifecycle]]
- [[dms-metadata-and-recovery]]
- [[dms-configuration-and-assembly]]
- [[public-api-surface]]
- [[service-configuration-topology]]
