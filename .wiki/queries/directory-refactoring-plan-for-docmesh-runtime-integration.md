---
title: Directory refactoring plan for docmesh runtime integration
created: 2026-06-19
updated: 2026-06-19
type: query
tags: [architecture, integration, roadmap, python, sdk, config]
sources: [raw/articles/docmesh-rag-core-api-reference-2026-06-11.md, raw/articles/docmesh-rag-core-prd-2026-06-11.md, raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]
confidence: medium
---

# Directory refactoring plan for docmesh runtime integration

## Question

앞서 제안한 구조를 기준으로 `docmesh-rag-system-core`의 디렉터리를 어떻게 리팩터링하면 좋은가?

## Recommended target layout

```text
rag_system_core/
  __init__.py
  types.py

  domain/
    __init__.py
    core.py
    ingestion.py
    retrieval.py
    generation.py

  storage/
    __init__.py
    metadata_store.py
    vector_store.py
    document_storage.py

  adapters/
    __init__.py
    ollama.py
    chunking.py

  composition/
    __init__.py
    docmesh_runtime.py
    factories.py
    auth.py
    health.py
    bootstrap.py
```

## Ownership by directory

### `domain/`

`RAGCore`와 ingestion/retrieval/generation orchestration을 둔다. 이 계층은 문서 수명주기, 검색 의미론, delete semantics, progress semantics 같은 RAG 도메인 규칙을 계속 소유해야 하며, `docmesh-py-core`의 설정 로딩이나 Keycloak 세부 구현을 직접 알지 않는 편이 좋다.

### `storage/`

`metadata_store`, `vector_store`, `document_storage`를 모은다. 현재 `DocumentStorage`가 `infrastructure.py`에 섞여 있으므로 이를 먼저 분리하면 runtime/config concern과 persistence concern이 분리된다.

### `adapters/`

외부 의존 concrete adapter를 둔다. 현재 `OllamaEmbeddingClient`, `OllamaGenerationClient`, `FixedWindowChunker`는 adapter 성격이므로 `infrastructure.py`보다는 `adapters/ollama.py`, `adapters/chunking.py`로 옮기는 편이 자연스럽다.

### `composition/`

`docmesh-py-core` 연동 경계를 모은다. 이 디렉터리는 `load_settings`, `ServiceFactoryRegistry`, Milvus/Ollama runtime 설정 브리지, auth mode별 `token -> user_id` 해석, health aggregation, 그리고 앱/API/worker가 재사용할 bootstrap helper를 소유한다. 이 계층이 있어야 `RAGCore`가 runtime 세부사항에 덜 오염된다.

## Transitional guidance

초기 리팩터링에서는 루트 모듈을 완전히 없애기보다 shim으로 두는 편이 좋다. 예를 들어 `rag_system_core/core.py`는 최종적으로 `rag_system_core.domain.core`를 re-export하는 compatibility layer가 될 수 있다. 이렇게 하면 기존 import를 한 번에 깨지 않고 점진적으로 새 구조로 옮길 수 있다.

## Recommended move order

1. 새 package skeleton 생성 (`domain/`, `storage/`, `adapters/`, `composition/`)
2. `RetrievalService`, `GenerationService`, `IngestionService`를 `domain/`으로 이동
3. `DocumentStorage`, `metadata_store`, `vector_store`를 `storage/`로 이동
4. Ollama client와 chunker를 `adapters/`로 이동
5. `resolve_user_id`, runtime settings bridge, health orchestration을 `composition/`으로 이동
6. `bootstrap_rag_core_from_docmesh(...)` 같은 조립 entrypoint 추가
7. 마지막에 루트 모듈을 compatibility shim으로 축소

## Testing alignment

테스트 디렉터리도 책임 기준으로 나누는 것이 좋다.

```text
test_rag_system_core/
  domain/
  storage/
  adapters/
  composition/
```

특히 현재 `test_docmesh_integration.py`, `test_core_configuration.py`는 composition/runtime 계층 테스트로 보는 것이 자연스럽고, query/ingestion/deletion/progress 테스트는 domain 쪽으로 분리하는 편이 구조와 잘 맞는다.

## Recommendation

실제 리팩터링의 핵심은 파일을 예쁘게 나누는 것이 아니라 **`RAGCore`에서 docmesh runtime 지식을 빼내고 composition 계층으로 옮기는 것**이다. 따라서 디렉터리 구조는 `domain / storage / adapters / composition` 네 축을 기준으로 정리하는 것이 가장 적절하다.

## Related pages

- [[structural-integration-of-docmesh-py-core-into-docmesh-rag-system-core]]
- [[docmesh-py-core]]
- [[rag-service-architecture]]
- [[project-roadmap]]
