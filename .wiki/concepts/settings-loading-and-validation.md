---
title: Settings Loading and Validation
created: 2026-06-19
updated: 2026-08-25
type: concept
tags: [config, sdk, python, security, decision]
sources: [raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md, raw/articles/dms-core-examples-v0.9.0-2026-08-18.md, raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md, raw/articles/dms-core-examples-v0.10.0-2026-08-25.md]
confidence: medium
---

# Settings Loading and Validation

`docmesh-config` v0.1.0은 canonical 설정 package로서 process environment에서 typed config를 읽고 `ServiceConfigs`와 `RuntimePlan`으로 선택·검증한다. `docmesh-py-core`는 이 결과를 client/assembly/lifecycle로 변환하며, partial 설정·잘못된 bool/int/range·production transport 보안 위반을 구조화된 오류로 다룬다.

## DMS configuration boundary

DMS v0.10.0은 environment를 읽거나 `diagnose_environment()`를 제공하는 설정 SDK가 아니다. host가 environment·config file·secret manager를 읽고 Engine, MinIO client, 또는 storage component를 만든 뒤 SDK에 주입해야 한다. v0.6.0 environment factory와 v0.7.0 configuration/assembly-plan 서술은 versioned historical context로 분리한다.^[raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md]

DMS assembly에서 host 또는 factory boundary가 확인해야 하는 입력 계약은 다음과 같다.

- SQLAlchemy dialect는 `postgresql` 또는 `sqlite`
- `bucket_name`은 공백을 제거한 뒤 비어 있지 않음
- `max_file_size`는 양수인 경우에만 사용
- upload request의 bytes, filename, content type, stream size는 개별 입력 계약을 만족
- credential과 endpoint는 log/error에 secret-safe하게 남김

factory의 `max_file_size <= 0`은 `ValueError`, direct `DefaultDocumentManagementSDK` 조립의 같은 조건은 `ValidationError`다. DMS API 문서에는 host가 제공한 engine/client/component의 readiness를 SDK가 대신 검사하는 public health method가 없다.^[raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md]^[raw/articles/dms-core-examples-v0.10.0-2026-08-25.md]

## v0.10 async and user-scope validation

v0.10.0 native async는 `AsyncDocumentManagementSDKFactory`의 `create()`/`create_async()`를 사용하며 sync `DocumentManagementSDKFactory`에 `create_async()`가 있다고 가정하지 않는다. `AccessContext.user_id`와 `DmsOperationContext.user_id`는 document·object·operation·cursor에 같은 범위를 적용하고, service readiness와 resource cleanup은 여전히 host가 별도 검증한다.^[raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md]^[raw/articles/dms-core-examples-v0.10.0-2026-08-25.md]

## Assembly and runtime policy

`DocumentManagementSDKFactory`는 engine dialect에 맞는 metadata adapter, MinIO object adapter, persistent operation store를 조립하고 `DefaultDocumentManagementSDK`는 host component를 직접 받는다. `operation_store`를 생략한 direct assembly에서는 idempotency upload와 operation lookup이 불가능하다. access policy, operation observer, recovery audit hook은 configuration loader가 아니라 host가 주입하는 document policy seam이다.^[raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md]

DMS facade는 engine·MinIO client·component lifecycle을 소유하지 않으며 전역 `close()`·`aclose()`·`check_health()`도 제공하지 않는다. startup readiness와 cleanup은 [[service-health-orchestration]] 및 host composition에서 별도 관리하고, DMS 오류는 stable `code`, `category`, `retryable`을 transport adapter가 자체 응답 규칙으로 변환한다.^[raw/articles/dms-core-api-reference-v0.10.0-2026-08-25.md]^[raw/articles/dms-core-examples-v0.10.0-2026-08-25.md]

## Related pages

- [[first-success-configuration]]
- [[docmesh-config]]
- [[keycloak-auth-service]]
- [[docmesh-py-core]]
- [[service-factory-registry]]
- [[service-configuration-topology]]
- [[service-health-orchestration]]
- [[dms-configuration-and-assembly]]
- [[dms-core]]
