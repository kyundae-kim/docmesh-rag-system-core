---
title: Separating DMS Service Environment Variables with Prefixes
created: 2026-07-28
updated: 2026-07-28
type: query
tags: [config, integration, architecture, decision]
sources: [raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md, raw/articles/dms-core-env-example-v0.6.0-2026-07-27.md, raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md]
confidence: medium
---

# Separating DMS Service Environment Variables with Prefixes

## 요구사항

같은 host process에서 RAG Core와 DMS가 서로 다른 PostgreSQL·SQLite·MinIO 구성을 사용할 수 있도록, DMS용 환경변수에는 지정한 접두사를 붙여 분리 관리한다. 예시 접두사가 `DMS_`라면 `DMS_POSTGRES_HOST`, `DMS_SQLITE_PATH`, `DMS_MINIO_ENDPOINT`처럼 표현한다.

## 현재 계약

현재 `dms-core` v0.6.0의 환경 factory는 `DMS_*`, `DOCMESH_*`, `POSTGRES_*`, `SQLITE_*`, `MINIO_*`라는 고정된 canonical key를 process environment에서 읽는다. `create_sdk_from_environment()`에는 접두사나 namespace를 지정하는 공개 옵션이 문서화되어 있지 않다. `docmesh-py-core` v0.5.0의 config 모델과 `load_service_configs()`도 process environment에서 고정 key를 직접 읽으며 mapping을 받지 않는다.^[raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md]^[raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md]

따라서 prefixed key를 그대로 둔 채 `create_sdk_from_environment()`를 호출하면 DMS가 이를 인식하지 못한다. 호출 직전에 `os.environ`을 임시 변환하는 방식도 환경 기반 조립 중 관련 key를 변경하지 말라는 동시성 제약과 충돌하므로 애플리케이션 기본 경로로 사용하지 않는다.^[raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md]^[raw/articles/dms-core-env-example-v0.6.0-2026-07-27.md]

## 권장 경계

접두사는 **배포·host application의 configuration namespace**로 소유하고, DMS SDK 내부 계약으로 간주하지 않는다.

| 상황 | 권장 방식 |
| --- | --- |
| DMS가 별도 process/container로 실행됨 | secret/config store에서는 prefixed key를 관리하되, container 주입 시 canonical key로 이름을 변환한 뒤 `create_sdk_from_environment()` 사용 |
| 하나의 process가 RAG와 DMS에 서로 다른 PostgreSQL·MinIO를 사용함 | prefixed key를 application settings로 파싱하고 client를 명시적으로 만든 뒤 `create_sdk_from_clients()` 또는 `create_sdk_from_components()` 사용 |
| 이미 분리된 `ServiceConfigs`를 안전하게 만들 수 있음 | `create_sdk_from_service_configs()` 사용. 단, 현재 공개 config loader 자체에는 prefix/mapping 입력 계약이 없으므로 process environment 변환에 의존하지 않음 |
| SDK 환경 factory에서 prefix를 직접 지원해야 함 | `dms-core` 또는 `docmesh-py-core`에 명시적 environment mapping/namespace API를 추가하는 별도 upstream 계약 변경으로 처리 |

이 경계는 [[dms-configuration-and-assembly]]의 네 조립 경로와 자원 소유권을 유지하면서, [[service-configuration-topology]]의 서비스별 설정 분리를 process-global key 충돌 없이 적용한다.

## 이름 규칙

- 접두사는 배포 단위에서 하나로 고정한다. 예: `DMS_`.
- DMS가 소비하는 공유 서비스 key 전체에 일관되게 적용한다: `DMS_POSTGRES_*`, `DMS_SQLITE_*`, `DMS_MINIO_*`, `DMS_DOCMESH_*`.
- 이미 `DMS_`로 시작하는 DMS 전용 control key는 `DMS_METADATA_BACKEND`, `DMS_CONFIGURATION_STRICT`처럼 기존 canonical 이름을 유지해 `DMS_DMS_*` 중복을 피한다.
- prefix 제거 후 canonical key가 중복되거나 필수값이 누락되면 bootstrap 단계에서 실패시킨다.
- secret-safe 진단에는 원래 prefixed key 이름만 기록하고 password/access key/secret 값은 노출하지 않는다.

## 저장소 적용 상태

2026-07-28 현재 repository의 production composition 경로에 다음과 같이 적용되었다.

- `rag_system_core/composition/docmesh_runtime.py`의 `load_dms_settings()`는 process environment를 변경하지 않고 `DMS_` namespace만 읽는다. `DMS_DOCMESH_*`, `DMS_POSTGRES_*`, `DMS_SQLITE_*`, `DMS_MINIO_*`를 각각 전용 `docmesh-py-core` config model로 검증하고, `DMS_METADATA_BACKEND`와 `DMS_CONFIGURATION_STRICT`는 중복 접두사 없이 DMS 진단에 전달한다.
- 같은 모듈은 진단용 mapping에서 공유 서비스 key의 선행 `DMS_` 한 개만 제거해 `dms.diagnose_environment()`의 canonical 계약을 재사용한다. 실제 `os.environ`에는 쓰지 않는다.
- `rag_system_core/composition/factories.py`의 `DocmeshRAGServiceFactory.from_env()`는 Ollama·Milvus만 RAG `ServiceBundle`로 조립하고, 분리된 DMS `ServiceConfigs`는 `dms.create_sdk_from_service_configs()`에 전달한다. factory가 두 lifecycle을 소유하고 DMS SDK를 먼저 닫은 뒤 RAG bundle을 닫는다.
- `.env.example`과 `README.md`는 `DMS_SQLITE_PATH`, `DMS_POSTGRES_*`, `DMS_MINIO_*`, `DMS_DOCMESH_ENV`를 canonical application 설정으로 사용한다.
- `test_rag_system_core/composition/test_docmesh_integration.py`는 SQLite와 PostgreSQL 양쪽에서 prefixed 값을 읽고 접두사 없는 `SQLITE_PATH`·`MINIO_ENDPOINT`가 DMS 설정에 섞이지 않는지 검증한다. focused composition suite 32개와 전체 suite 79개가 통과했다.

이 구현은 별도 client를 직접 생성하지 않고도 **분리된 `ServiceConfigs`를 안전하게 만드는 경로**를 repository composition 계층에 소유하게 한 것이다. SDK의 process-global environment factory에 namespace 지원이 생겼다고 해석해서는 안 된다.

## 검증 기준

1. **검증됨:** DMS bootstrap은 접두사 없는 RAG `SQLITE_*`·`MINIO_*` 환경변수를 읽지 않는다.
2. **검증됨:** SQLite/PostgreSQL backend와 MinIO 설정이 각각 `DMS_` prefixed config model로 매핑된다.
3. **부분 검증:** PostgreSQL/SQLite 선택과 MinIO bucket 필수값은 DMS 진단 및 config validation을 재사용한다. production TLS 회귀는 upstream DMS 계약 검증 범위로 유지한다.
4. **검증됨:** process environment를 호출 중 변경하지 않는다.
5. **검증됨:** `DocmeshRAGServiceFactory`가 생성한 DMS SDK와 RAG bundle의 종료 순서를 테스트한다.
6. **검증됨:** 접두사 처리는 composition 설정에만 위치하며 domain/storage 인터페이스를 변경하지 않는다.

## 결론

DMS 환경변수의 접두사 분리는 repository composition 계층에 적용되었다. 동일 process에서 RAG와 DMS는 서로 다른 설정 model 및 assembly lifecycle을 사용하며, DMS 공유 서비스 key는 `DMS_` namespace에서만 읽는다. 다만 이는 consumer repository가 분리된 `ServiceConfigs`를 구성하는 구현이지 SDK environment factory 자체의 prefix 지원은 아니다. 별도 process/container에서는 여전히 배포 경계에서 canonical key로 변환해 SDK 환경 factory를 사용할 수 있다. 관련 DMS storage 결합은 [[applying-dms-core-as-document-storage]]의 경계를 따른다.

## Related pages

- [[dms-core]]
- [[dms-configuration-and-assembly]]
- [[service-configuration-topology]]
- [[settings-loading-and-validation]]
- [[applying-dms-core-as-document-storage]]
- [[verifying-dms-core-contract]]
