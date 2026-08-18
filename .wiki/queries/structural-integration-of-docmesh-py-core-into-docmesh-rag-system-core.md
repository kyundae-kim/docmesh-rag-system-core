---
title: Structural integration of docmesh-py-core into docmesh-rag-system-core
created: 2026-06-19
updated: 2026-08-18
type: query
tags: [sdk, architecture, integration, python, roadmap, config]
sources: []
confidence: medium
---

# Structural integration of docmesh-py-core into docmesh-rag-system-core

## Question

`docmesh-rag-system-core`에 `docmesh-py-core`를 어떻게 연결하면 구조적으로 좋은가?

## Short answer

가장 좋은 방향은 `docmesh-rag-system-core`가 **RAG 도메인 코어**를 계속 소유하고, `docmesh-py-core`는 그 바깥에서 **공통 인프라 bootstrap / config / auth / service wiring 계층**을 맡게 하는 것이다. 즉 `RAGCore` 내부에 `docmesh-py-core`를 깊게 침투시키기보다, `infrastructure` 또는 별도 composition layer에서 두 패키지를 연결하는 방식이 장기적으로 가장 안정적이다.

## Current grounding

현재 코드 기준으로는 이미 약한 결합의 출발점이 있다. `pyproject.toml`이 `docmesh-py-core`를 직접 의존성으로 두고 있고, `rag_system_core.infrastructure`는 `load_settings`, `ServiceFactoryRegistry`, `check_all_services`, `KeycloakAuthService`를 사용해 Ollama / Milvus / auth / health 동작 일부를 `docmesh-py-core`와 연결하고 있다. 반면 `RAGCore` 자체는 ingestion / retrieval / generation / metadata lifecycle을 여전히 직접 소유한다. 이 상태는 [[rag-service-architecture]]와 [[interface-roadmap]]가 제안하는 “core는 도메인, adapter는 채널/운영” 원칙과 대체로 맞는다.

## Recommended target structure

### 1. Keep domain ownership in rag_system_core

다음 책임은 `rag_system_core`가 계속 소유하는 것이 좋다.

- `RAGCore` public methods와 반환 의미
- ingestion / retrieval / generation orchestration
- metadata schema와 document/chunk/progress lifecycle
- user scope 적용 지점
- delete semantics, restart recovery, persistence semantics

즉 `RAGCore`는 계속 [[public-api-surface]], [[rag-service-architecture]], [[user-scope-isolation]]의 canonical contract여야 한다.

### 2. Move integration ownership to a composition boundary

반대로 다음 책임은 `docmesh-py-core`와의 연결 경계로 분리하는 것이 좋다.

- 환경변수 로드와 검증
- 외부 서비스 endpoint/model/timeout 선택
- Keycloak 기반 `token -> user_id` 해석
- 공통 health check aggregation
- 향후 API/worker가 재사용할 bootstrap 함수

이 책임은 지금처럼 `infrastructure.py` 일부에 흩어져 있기보다, 명시적인 composition 계층으로 분리하는 편이 낫다.

## Concrete module proposal

### Option A — Preferred: dedicated composition module

```text
rag_system_core/
  core.py                    # pure domain orchestration
  ingestion.py
  metadata_store.py
  vector_store.py
  infrastructure.py          # low-level adapters only
  composition/
    __init__.py
    docmesh_runtime.py       # docmesh settings + registry bridge
    factories.py             # create_embedding_client/create_generation_client/create_vector_store
    auth.py                  # resolve_user_id via auth mode
    health.py                # aggregate readiness policies
```

이 구조에서:

- `core.py`는 가능한 한 `docmesh-py-core`를 직접 import하지 않는다.
- `composition/docmesh_runtime.py`가 `load_settings()`와 `ServiceFactoryRegistry`를 담당한다.
- `composition/factories.py`가 `OllamaEmbeddingClient`, `OllamaGenerationClient`, Milvus runtime 설정 생성 규칙을 담당한다.
- `composition/auth.py`가 현재 `resolve_user_id()`를 옮겨 auth mode 별 해석을 담당한다.
- `composition/health.py`가 `check_all_services()` 연동과 fallback 정책을 캡슐화한다.

이렇게 하면 `docmesh-py-core` 연동 코드는 한곳에 모이고, `RAGCore`는 테스트하기 쉬운 순수 조합 계층으로 남는다.

### Option B — Minimal change path

큰 구조 변경이 부담되면, 당장은 `infrastructure.py` 안에서만 경계를 선명히 해도 된다.

- `docmesh settings bridge`
- `ollama client bridge`
- `milvus runtime settings bridge`
- `auth bridge`
- `health bridge`

처럼 섹션을 나누고, `core.py`는 `infrastructure`의 안정된 함수만 호출하게 유지한다. 다만 장기적으로는 composition 패키지로 분리하는 편이 더 낫다.

## Recommended integration pattern

### Pattern 1: App/bootstrap owns docmesh wiring

가장 권장하는 패턴은 애플리케이션 또는 API 서버가 먼저 `docmesh-py-core`로 설정을 만들고, 그 결과를 바탕으로 `rag_system_core` 객체를 조립하는 방식이다.

```python
settings = load_settings()
registry = ServiceFactoryRegistry(settings)

embedding_client = create_rag_embedding_client(settings=settings, registry=registry)
generation_client = create_rag_generation_client(settings=settings, registry=registry)
core = RAGCore(
    embedding_client=embedding_client,
    generation_client=generation_client,
    metadata_path=..., 
    document_storage_dir=..., 
    storage_mode="local",
)
```

이 방식의 장점은 `RAGCore` 생성자가 여전히 단순하고, API/worker/CLI가 같은 bootstrap 로직을 재사용할 수 있다는 점이다.

### Pattern 2: Optional convenience constructor

필요하다면 `RAGCore.from_docmesh_settings(...)` 같은 convenience constructor를 추가할 수는 있다. 하지만 이것을 기본 경로로 만들기보다, app-level bootstrap을 우선 경로로 두는 편이 좋다. 그렇지 않으면 core가 점점 service locator처럼 비대해질 수 있다.

## Specific refactoring recommendations

### 1. Separate runtime config from domain constructor

현재 `RAGCore.__init__`는 `resolve_milvus_runtime_settings()`를 직접 호출한다. 이 때문에 core 생성이 docmesh 설정 유효성에 즉시 결합된다. 구조적으로는 다음이 더 낫다.

- app/bootstrap 계층에서 Milvus URI, collection, timeout을 먼저 확정
- `RAGCore` 또는 vector store factory에 명시적으로 주입
- core는 “어떻게 설정을 읽는지”가 아니라 “무슨 의존성을 받는지”만 안다

이렇게 하면 테스트, 대체 저장소, API 서비스화가 쉬워진다.

### 2. Treat auth resolution as pre-core concern

현재 `query`, `ingest_*`, `list_*`, `delete_document`가 모두 `token`을 받아 내부에서 `resolve_user_id(token)`을 호출한다. 초기에는 편하지만, API/MCP 확장 관점에서는 auth 해석을 core 밖으로 빼는 편이 더 좋다.

권장 방향:

- 외부 계층(API/MCP/app bootstrap)이 token 검증/해석 수행
- core에는 `user_id` 또는 이미 해석된 principal/context 전달
- 필요 시 편의용 `token` 경로는 유지하되, 내부 canonical path는 `user_id` 기반으로 이동

이것이 [[user-scope-isolation]]의 의미를 더 명확하게 만든다.

### 3. Standardize service factory APIs for RAG use

`docmesh-py-core` registry가 범용 서비스 생성기라면, `rag_system_core` 쪽에는 얇은 전용 factory를 두는 것이 좋다.

예:

- `create_rag_embedding_client(...)`
- `create_rag_generation_client(...)`
- `create_rag_health_checks(core, ...)`
- `create_rag_runtime_paths(settings, ...)`

이렇게 하면 범용 SDK와 RAG 프로젝트 특화 규칙을 섞지 않을 수 있다.

## Proposed boundary rule

### docmesh-py-core owns

- settings schema loading/validation
- shared external client creation
- Keycloak/JWT handling utilities
- generic health-check aggregation
- secret masking / config snapshotting

### rag-system-core owns

- document/chunk/progress semantics
- chunking/embedding/retrieval/generation orchestration
- vector search domain behavior
- user-scoped document lifecycle
- public RAG methods and result types

이 소유권 구분이 깨지면 API/MCP 단계에서 계층이 혼탁해질 가능성이 높다.

## Rollout order

1. `infrastructure.py` 안의 docmesh 결합 코드를 runtime/composition 책임으로 재정리
2. `RAGCore` 생성자에서 설정 해석 로직을 줄이고 의존성 주입 비중 확대
3. auth 해석과 `user_id` 적용 경로를 분리 설계
4. API/worker가 재사용할 `bootstrap_rag_core_from_docmesh(...)` 헬퍼 추가
5. 이후 API/MCP 프로젝트는 이 bootstrap 모듈을 재사용

이 순서는 [[project-roadmap]]의 Phase 0~2와도 잘 맞는다.

## Recommendation

실무적으로는 **“RAGCore는 순수 도메인 코어, docmesh-py-core는 composition/bootstrap SDK”** 라는 원칙으로 가는 것이 가장 좋다. 지금 코드도 그 방향의 초입에 있으므로, 다음 단계는 `docmesh` 연동을 `core.py` 내부로 더 넣는 것이 아니라 오히려 **명시적 runtime/composition 계층으로 분리**하는 것이다.

## Related pages

- [[docmesh-py-core]]
- [[rag-service-architecture]]
- [[interface-roadmap]]
- [[project-roadmap]]
- [[user-scope-isolation]]
- [[future-considerations-for-sdk-api-mcp-rag-project]]
