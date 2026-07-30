---
title: DMS Configuration and Assembly
created: 2026-07-27
updated: 2026-07-27
type: concept
tags: [config, sdk, integration, persistence, security]
sources: [raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md, raw/articles/dms-core-env-example-v0.6.0-2026-07-27.md, raw/articles/dms-core-examples-v0.6.0-2026-07-27.md]
confidence: medium
---

# DMS Configuration and Assembly

DMS는 환경, 검증된 `ServiceConfigs`, 호출자 소유 SQLAlchemy Engine·MinIO client, 직접 주입 adapter의 네 가지 조립 경로를 제공한다. 환경·설정 기반 factory가 만든 client는 SDK가 소유하고, client/component factory에 주입한 자원은 기본적으로 호출자 소유다. 종료 책임을 넘길 때만 `close_callbacks`를 등록한다.^[raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md]

## Backend selection

`DMS_METADATA_BACKEND=postgresql|sqlite`는 metadata backend를 명시적으로 고정한다. 미설정이면 `POSTGRES_*` 단서가 SQLite보다 우선하고, PostgreSQL/SQLite가 모두 있는 auto mode는 경고와 함께 PostgreSQL을 선택한다. `DMS_CONFIGURATION_STRICT=true`는 이 모호성을 오류로 만든다. 어떤 선택이든 DMS document storage에는 `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`이 필수다.^[raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md]

## Security and startup checks

`DOCMESH_HEALTHCHECK_ENABLED`는 환경 factory의 startup check를 제어하며 typed core의 `HealthcheckPolicy.on_startup`으로 변환된다. production에서는 MinIO transport encryption과 certificate verification을 비활성화할 수 없다. placeholder endpoint를 쓰는 로컬 템플릿은 health check를 꺼 두지만, 실제 배포에는 reachable endpoint와 보안값이 필요하다.^[raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md]^[raw/articles/dms-core-env-example-v0.6.0-2026-07-27.md]

## Related pages

- [[dms-core]]
- [[service-configuration-topology]]
- [[settings-loading-and-validation]]
- [[service-health-orchestration]]
