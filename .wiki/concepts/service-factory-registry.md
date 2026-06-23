---
title: Service Factory Registry
created: 2026-06-19
updated: 2026-06-23
type: concept
tags: [sdk, python, integration, config, decision]
sources: [raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md, raw/articles/docmesh-py-core-api-guide-2026-06-19.md, raw/articles/docmesh-py-core-config-guide-2026-06-19.md, raw/articles/docmesh-rag-core-api-reference-2026-06-23.md]
confidence: medium
---

# Service Factory Registry

`ServiceFactoryRegistry`는 `docmesh-py-core` 소비 프로젝트에서 서비스별 SDK 초기화 책임을 한곳에 모으는 조정 계층이다. 권장 흐름은 `load_settings(environ)`으로 환경변수를 검증한 뒤 registry를 만들고, 실제로 필요한 서비스에 대해서만 `create_client()`를 호출하는 것이다.^[raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md]

## Why this boundary matters

이 패턴은 애플리케이션 코드가 PostgreSQL, SQLite, MinIO, NATS 같은 외부 client 생성 세부사항에 직접 결합되는 것을 줄여 준다. 문서는 명시적 backend selector보다 실제 환경변수 존재 여부로 서비스를 선택하는 방식을 권장하며, 예를 들어 `settings.sqlite`가 있으면 SQLite client를, 아니면 PostgreSQL client를 선택하는 식의 분기가 대표적이다.^[raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md]

## Configuration coupling

설정 가이드는 registry 앞단의 `load_settings()`가 단순 파서가 아니라 서비스별 필수값, 조건부 필수값, 기본값, 보안 규칙을 함께 검증하는 계층임을 분명히 한다. 따라서 registry는 단순 factory라기보다 [[settings-loading-and-validation]]에서 이미 정규화된 설정 객체를 전제로 동작하며, 서비스 선택도 별도 backend selector보다 `POSTGRES_*`, `SQLITE_*` 같은 실제 설정 존재 여부에 결합된다.^[raw/articles/docmesh-py-core-config-guide-2026-06-19.md]

## Usage constraints

registry가 반환하는 값은 서비스마다 성격이 다를 수 있다. 특히 `create_client("nats")`는 즉시 연결된 동기 client가 아니라 `NatsConnectionBuilder`를 돌려주므로 `await builder.connect()` 또는 `await builder.check()` 패턴을 강제한다. 따라서 소비 프로젝트는 서비스별 반환 계약 차이를 흡수하는 래퍼 계층을 둘지 여부를 검토해야 한다.^[raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md]

## RAG bootstrap implications

RAG Core API reference는 `bootstrap_rag_core(...)`가 settings를 직접 로드하지 않고 `service_factory`를 통해 embedding/generation/vector/metadata/storage/chunker를 조립한다고 명시한다. 또한 DocMesh 경로 예시에서 `load_docmesh_settings()`와 `create_service_registry(settings)`를 먼저 호출한 뒤 `DocmeshRAGServiceFactory(settings=settings, registry=registry)`를 구성한다. 따라서 registry는 RAG bootstrap 경로에서 선택적 주변도구가 아니라 [[construction-paths-and-adapter-contracts]]와 [[public-api-surface]]를 잇는 실제 조립 전제조건이다.^[raw/articles/docmesh-rag-core-api-reference-2026-06-23.md]

## Return contract

API 가이드는 registry의 반환 규칙을 서비스별로 더 구체화한다. `keycloak`, `postgres`, `sqlite`, `minio`, `milvus`, `ollama`는 대체로 `ServiceClientWrapper`를 반환하고, `langfuse`는 비활성화 시 `None`일 수 있으며, `nats`만 `NatsConnectionBuilder`를 반환한다. 또한 지원하지 않는 서비스명은 `UnsupportedServiceError`를, 공통 health check 래핑 중 실패는 `ServiceClientWrapperError`를 통해 표준화한다.^[raw/articles/docmesh-py-core-api-guide-2026-06-19.md]

## Operational notes

권장 종료 패턴은 애플리케이션 수명주기 끝에서 `registry.close_all()`을 호출해 engine/client/flush/dispose를 한 번에 정리하는 것이다. 이 수명주기 관리 패턴은 [[service-health-orchestration]]과 결합될 때 startup readiness와 shutdown cleanup을 한 흐름으로 정리할 수 있다.^[raw/articles/docmesh-py-core-sdk-guide-2026-06-19.md]

## Related pages

- [[construction-paths-and-adapter-contracts]]
- [[docmesh-py-core]]
- [[service-health-orchestration]]
- [[public-api-surface]]
