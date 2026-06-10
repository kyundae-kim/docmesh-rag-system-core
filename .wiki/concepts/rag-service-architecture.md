---
title: RAG Service Architecture
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [rag, architecture, pipeline, sdk]
sources: [raw/articles/docmesh-rag-core-api-reference-2026-06-11.md, raw/articles/docmesh-rag-core-prd-2026-06-11.md, raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]
confidence: high
---

# RAG Service Architecture

DocMesh RAG Core의 현재 구조는 외부에 `RAGCore` 단일 진입점을 유지하면서 내부를 IngestionService, RetrievalService, GenerationService, MetadataStore로 나누는 형태다. 저장 계층은 Milvus Lite vector store, SQLAlchemy ORM + SQLite metadata store, 그리고 `memory | local` 문서 자산 저장으로 분리된다.^[raw/articles/docmesh-rag-core-prd-2026-06-11.md]

## Design principles

설계 원칙은 외부 인터페이스 단순성, 내부 책임 분리, 문서 자산 저장과 메타데이터 저장 분리, persistence와 검색 계층의 분리 및 재구성 가능성이다. 이 구조는 MVP의 개발 속도와 후속 서비스 분리 가능성 사이의 균형을 목표로 한다.^[raw/articles/docmesh-rag-core-prd-2026-06-11.md]

## Service responsibilities

- IngestionService: 로드, 전처리, 청킹, 임베딩, 메타데이터 기록, 벡터 적재
- RetrievalService: 질의 임베딩, 벡터 검색, 사용자 스코프 필터링
- GenerationService: 프롬프트 구성, 컨텍스트 기반 답변 생성
- MetadataStore: 문서/청크/progress 저장과 조회, 삭제, 복원 지원^[raw/articles/docmesh-rag-core-prd-2026-06-11.md]

## Evolution path

이 아키텍처는 현재 SDK 우선 설계를 취하지만, PRD는 이후 FastAPI 기반 API 서비스, async 처리, 외부 vector DB, 더 나아가 ingestion/retrieval/generation 서비스 분리까지 로드맵에 포함한다. 따라서 현재 위키에서는 [[public-api-surface]]와 [[interface-roadmap]]를 함께 봐야 전체 방향이 드러난다.^[raw/articles/docmesh-rag-core-prd-2026-06-11.md]

## Related pages

- [[ragcore]]
- [[ingestion-pipeline]]
- [[persistence-and-restart-recovery]]
- [[interface-roadmap]]
