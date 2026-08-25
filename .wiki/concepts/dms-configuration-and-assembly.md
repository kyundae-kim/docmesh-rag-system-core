---
title: DMS Configuration and Assembly
created: 2026-07-27
updated: 2026-08-25
type: concept
tags: [config, sdk, integration, persistence, security, observability]
sources: [raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md, raw/articles/dms-core-examples-v0.9.0-2026-08-18.md, raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md, raw/articles/dms-core-examples-v0.10.0-2026-08-25.md]
confidence: medium
---

# DMS Configuration and Assembly

## Host-owned configuration boundary

v0.10.0에서 DMS는 환경변수·`.env`를 읽거나 PostgreSQL/SQLite/MinIO connection을 직접 만들지 않는다. 호스트 애플리케이션이 설정 파일·environment·secret manager를 읽고 SQLAlchemy `Engine`과 MinIO client 또는 metadata/object/operation component를 만든 뒤 DMS에 주입한다. DMS의 public package root는 configuration loader가 아니라 document-management SDK 경계다.^[raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md]

따라서 v0.6.0의 environment factory와 v0.7.0의 assembly-plan 서술은 versioned historical context로 분리한다. v0.10.0 문서에는 `DmsServiceConfigs`, environment selector, `DmsAssemblyPlan`, startup health orchestration이 현재 public assembly input으로 제시되지 않는다.^[raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md]

## Factory paths

| 조립 방식 | 공개 API | host 입력 | ownership 기본값 |
| --- | --- | --- | --- |
| client sync | `DocumentManagementSDKFactory` | SQLAlchemy `Engine`, MinIO client, bucket | engine/client caller-owned |
| component sync | `DefaultDocumentManagementSDK` | metadata/object store, optional operation store | component caller-owned |
| client native async | `AsyncDocumentManagementSDKFactory`의 `create()` / `create_async()` | async SQLAlchemy `AsyncEngine`, MinIO client, bucket | engine/client caller-owned |
| compatibility async | `AsyncDocumentManagementSDK(sync_sdk)` | 이미 조립된 sync SDK | sync SDK와 동일 |
| scoped operation | `sdk.scoped(context)` | 기존 sync/async SDK와 `DmsOperationContext` | shared SDK lifecycle 비소유 |

client factory는 dialect가 `postgresql` 또는 `sqlite`인지와 공백이 아닌 `bucket_name`을 검증하고, engine을 이용해 persistent upload operation store를 조립한다. direct component 조립에서 `operation_store`를 생략하면 idempotency key upload와 operation 조회를 사용할 수 없다. factory의 `max_file_size <= 0`은 `ValueError`, direct SDK 조립의 같은 조건은 `ValidationError`다.^[raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md]^[raw/articles/dms-core-examples-v0.10.0-2026-08-25.md]

## v0.10 native async and user-scoped assembly

native async 경계는 `AsyncDocumentManagementSDKFactory(engine=async_engine, ...)`로 조립한다. `factory.create()`는 lazy async SDK를 반환하고 첫 await에서 초기화하며, `await factory.create_async()`는 `ready()`까지 기다린 SDK를 반환한다. 이미 만든 sync SDK를 감쌀 때는 `AsyncDocumentManagementSDK(sync_sdk)` compatibility 경계를 사용하며 두 경로를 같은 native async assembly로 혼동하지 않는다.^[raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md]^[raw/articles/dms-core-examples-v0.10.0-2026-08-25.md]

`DmsOperationContext`에 `user_id`와 `access`를 함께 주입하면 scoped facade가 문서·object namespace·idempotency·cursor에 동일한 사용자 범위를 적용한다. 작업에 명시한 값이 context 기본값보다 우선하지만 다른 user 범위로 바꾸는 값은 `ValidationError`이며, shared SDK와 resource lifecycle은 여전히 host가 소유한다.^[raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md]

## Resource ownership and lifecycle

기본 주입 engine·MinIO client·component는 caller-owned이며 SDK가 닫지 않는다. v0.10.0 facade에는 전역 `close()`·`aclose()`가 없고, async facade도 같은 lifecycle 비소유 계약을 따른다. SDK가 upload 중 직접 연 파일과 반환한 content stream은 SDK가 정리하지만 caller가 제공한 upload input stream과 copy sink는 caller가 닫는다.^[raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md]^[raw/articles/dms-core-examples-v0.10.0-2026-08-25.md]

애플리케이션은 engine/client/component의 생성·readiness·종료를 자신의 composition lifecycle에 연결해야 한다. DMS에 없는 전역 health/cleanup method를 consumer adapter의 필수 계약으로 가정하지 말고, host가 필요한 health check와 종료 순서를 별도로 정의한다.

## Policy and observation options

Factory와 direct facade는 `max_file_size`, `recovery_audit_hook`, `operation_observer`, `access_policy`를 받을 수 있다. `DocumentAccessPolicy` callback에는 public metadata만 전달되고, `OperationObserver`와 recovery audit hook이 예외를 내도 원래 작업 결과는 바뀌지 않는다. 권한·관찰·transport 변환은 DMS 내부 connection configuration과 분리된 host 정책이다.^[raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md]^[raw/articles/dms-core-examples-v0.10.0-2026-08-25.md]

## Security and host integration

DMS가 연결값을 읽지 않는다는 것은 secret 책임이 사라진다는 뜻이 아니다. host configuration layer가 endpoint·credential을 검증하고 log/error에서 masking해야 하며, operation event의 conditions와 recovery audit event에 본문·token·password·내부 storage locator를 넣지 않는 운영 경계를 지켜야 한다. DMS는 HTTP server가 아니므로 host transport가 stable error fields를 외부 응답 규칙으로 매핑한다.^[raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md]^[raw/articles/dms-core-examples-v0.10.0-2026-08-25.md]

## Related pages

- [[dms-core]]
- [[service-configuration-topology]]
- [[settings-loading-and-validation]]
- [[service-health-orchestration]]
- [[construction-paths-and-adapter-contracts]]
- [[applying-dms-core-as-document-storage]]
