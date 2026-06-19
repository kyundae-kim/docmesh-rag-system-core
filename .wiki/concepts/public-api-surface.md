---
title: Public API Surface
created: 2026-06-11
updated: 2026-06-19
type: concept
tags: [sdk, api, python, integration]
sources: [raw/articles/docmesh-rag-core-api-reference-2026-06-11.md, raw/articles/docmesh-rag-core-prd-2026-06-11.md, raw/articles/docmesh-rag-core-test-spec-2026-06-11.md, raw/articles/docmesh-py-core-api-guide-2026-06-19.md]
confidence: high
---

# Public API Surface

이 페이지는 외부 애플리케이션이 `rag_system_core`를 어떻게 안정적으로 import하고 호출해야 하는지 정리한다.

## Import boundary

권장 import 경로는 `from rag_system_core import RAGCore` 및 `from rag_system_core.types import ...` 이다. 문서는 `rag_system_core.internal.*` 또는 `rag_system_core.adapters.*` 같은 내부 경로 직접 의존을 public contract로 보지 않는다.^[raw/articles/docmesh-rag-core-api-reference-2026-06-11.md]

## Core methods

공식 public 메서드는 세 가지 ingestion entrypoint(`ingest_text`, `ingest_file_stream`, `ingest_file_path`)와 query/관리 메서드(`query`, `list_documents`, `get_document`, `list_document_chunks`, `list_ingestion_progress`, `delete_document`)로 구성된다. 이 표면은 문서 생명주기 전반을 다루며 테스트 명세도 이 메서드 집합을 중심으로 작성되어 있다.^[raw/articles/docmesh-rag-core-api-reference-2026-06-11.md]^[raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]

## Adapter contracts

`EmbeddingClient`는 `embed(texts: list[str]) -> list[list[float]]`, `GenerationClient`는 `generate(prompt: str) -> str` 계약을 만족해야 한다. 특히 embedding 결과 개수와 입력 텍스트 개수 일치, generation 결과의 문자열성은 호출 안정성의 핵심이다.^[raw/articles/docmesh-rag-core-api-reference-2026-06-11.md]

## Root import discipline

`docmesh-py-core` API 가이드는 패키지 루트에서 직접 import 가능한 심볼 목록을 명시적으로 제공한다. 이 점은 public surface를 단순히 "무엇을 할 수 있는가"가 아니라 "어디서 import해야 안정적인가"의 문제로 확장하며, `Settings`, `ServiceFactoryRegistry`, `ServiceClientWrapper`, `NatsConnectionBuilder`, `KeycloakAuthService`, `check_all_services`, `mask_sensitive_value`, `build_settings_snapshot` 같은 루트 심볼이 안정적인 소비 경계임을 시사한다.^[raw/articles/docmesh-py-core-api-guide-2026-06-19.md]

## Integration implications

외부 인터페이스는 단순하지만 실제 구현은 [[rag-service-architecture]]와 [[ingestion-pipeline]]에 걸친 내부 조합 위에 있다. 따라서 SDK를 API나 MCP로 감쌀 때는 public surface를 그대로 재노출하되 내부 구현 경계는 새 인터페이스 계층 밖으로 새지 않게 유지하는 편이 바람직하다.

## Related pages

- [[ragcore]]
- [[rag-service-architecture]]
- [[interface-roadmap]]
