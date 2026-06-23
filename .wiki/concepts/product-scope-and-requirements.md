---
title: Product Scope and Requirements
created: 2026-06-23
updated: 2026-06-23
type: concept
tags: [rag, architecture, sdk, decision, api]
sources: [raw/articles/docmesh-rag-core-prd-2026-06-23.md]
confidence: medium
---

# Product Scope and Requirements

`docs/prd.md`의 현재본은 DocMesh RAG Core를 미래 지향적 서비스가 아니라 **현재 코드 기준으로 정렬된 조립형 Python RAG 라이브러리**로 정의한다. 즉 이 제품의 기준선은 `RAGCore` 중심 SDK, user scope 격리, SQLite + Milvus Lite persistence, 세 가지 ingestion 경로, 문서 관리 API, 그리고 선택적 DocMesh integration이다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]

## What is in scope now

현재 PRD가 보장하는 범위는 `RAGCore` 단일 진입점, `bootstrap_rag_core` helper, 텍스트/파일 스트림/파일 경로 ingestion, 고정 길이 chunking + overlap, embedding batch 호출, Milvus Lite 검색, generation client 기반 답변 생성, token 및 선택적 Keycloak 기반 user scope, SQLite metadata persistence, `memory | local` document asset storage, 문서 조회/삭제, health check 집계까지다. 이 목록은 실제 public contract를 해석할 때 [[public-api-surface]], [[ingestion-pipeline]], [[user-scope-isolation]], [[persistence-and-restart-recovery]]를 함께 읽어야 함을 뜻한다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]

## What is explicitly out of scope

PRD는 외부 공개 HTTP API 서버, UI/Frontend, 비동기 job queue, 고급 reranking, 복잡한 조직/역할 기반 권한 모델, 분산 트랜잭션, production-grade 분산 vector DB 운영, 범용 바이너리 파싱을 현재 범위 밖으로 둔다. 따라서 [[interface-roadmap]]와 [[project-roadmap]]에 적힌 후속 확장은 현재 제품 계약이 아니라 미래 확장 가능성으로 읽어야 한다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]

## Product shape implied by the PRD

이 PRD는 제품 경계를 "단일 public 진입점은 단순하게 유지하되 내부는 ingestion / retrieval / generation / storage / composition 책임으로 나눈다"는 원칙으로 묶는다. 그 결과 [[rag-service-architecture]]는 façade 중심 아키텍처로, [[service-factory-registry]]는 직접 조립과 factory 조립을 동시에 허용하는 composition 경계로 해석하는 것이 맞다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]

## Operational contract

운영 측면에서 중요한 계약은 세 가지다. 첫째, query와 조회/삭제는 항상 현재 user scope에 제한되어야 한다. 둘째, restart recovery는 동일한 SQLite metadata와 Milvus 저장소 구성을 다시 열어 retrieval을 복원하는 방식이어야 한다. 셋째, document deletion은 vector store 삭제 성공 시에만 metadata / progress / asset 정리를 이어서 수행해야 하며, 실패 시에는 재시도를 위해 metadata를 보존해야 한다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]

## Acceptance-oriented reading

이 문서를 위키에서 특히 중요하게 봐야 하는 이유는 acceptance criteria가 구조적 기대를 매우 구체적으로 고정하기 때문이다. 예를 들어 ingestion 단계 순서, file stream ingestion의 `source` 필수성, prompt의 `[System Prompt] / [Retrieved Context] / [User Query]` 섹션, `bootstrap_rag_core(...)`의 service factory 조립 가능성은 모두 구현 세부가 아니라 제품 계약에 해당한다. 이 점은 [[public-api-surface]]와 [[ingestion-pipeline]]의 내용을 해석할 때 우선순위를 정해 준다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]

## Related pages

- [[ragcore]]
- [[public-api-surface]]
- [[rag-service-architecture]]
- [[ingestion-pipeline]]
- [[user-scope-isolation]]
- [[persistence-and-restart-recovery]]
- [[service-factory-registry]]
- [[interface-roadmap]]
- [[project-roadmap]]
