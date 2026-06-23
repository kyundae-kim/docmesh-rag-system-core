---
title: RAG Service Architecture
created: 2026-06-11
updated: 2026-06-23
type: concept
tags: [rag, architecture, pipeline, sdk]
sources: [raw/articles/docmesh-rag-core-api-reference-2026-06-11.md, raw/articles/docmesh-rag-core-prd-2026-06-23.md, raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]
confidence: high
---

# RAG Service Architecture

DocMesh RAG Core의 현재 구조는 외부에 `RAGCore` 단일 진입점을 유지하면서 내부를 IngestionService, RetrievalService, GenerationService, MetadataStore, DocumentStorage, Milvus Lite vector store로 분리하는 형태다. 현재 PRD는 이 구성을 **조립 가능한 Python RAG 라이브러리**의 기준선으로 정의하며, 외부 공개 HTTP API나 UI는 아직 제품 범위 밖으로 둔다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]

## Design principles

설계 원칙은 외부 인터페이스 단순성, 내부 책임 분리, 문서 자산 저장과 메타데이터 저장 분리, persistence와 검색 계층의 분리 및 재구성 가능성이다. 또한 직접 조립과 service-factory 기반 조립을 모두 허용해야 하므로, composition layer는 구현 세부가 아니라 제품 구조의 일부로 읽어야 한다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]

## Service responsibilities

- IngestionService: 로드, 전처리, 청킹, 임베딩, vector store 적재, chunk metadata persistence
- RetrievalService: 질의 임베딩, 벡터 검색, 사용자 스코프 필터링
- GenerationService: 프롬프트 구성, 컨텍스트 기반 답변 생성
- MetadataStore: 문서/청크/progress 저장과 조회, 삭제, 복원 지원
- DocumentStorage: `memory | local` 자산 저장과 `storage_path` 추적^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]

## Composition layer

현재 아키텍처 설명에는 `bootstrap_rag_core`, `DocmeshRAGServiceFactory`, `create_rag_embedding_client`, `create_rag_generation_client`, `create_rag_vector_store`, `create_rag_metadata_store`, `create_rag_document_storage`, `create_rag_chunker`, `load_docmesh_settings`, `resolve_user_id`가 함께 포함된다. 따라서 이 프로젝트에서 composition은 단순 편의 함수 모음이 아니라 [[public-api-surface]]와 [[service-factory-registry]]를 잇는 조립 경계다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]

## Evolution path

이 아키텍처는 현재 SDK 우선 설계를 취하지만, PRD는 이후 FastAPI 기반 서비스 래핑, async ingestion, 외부 vector DB adapter, richer document parsing 같은 확장 가능성을 별도 후속 범위로 둔다. 따라서 현재 제품 계약과 미래 확장을 구분하려면 [[product-scope-and-requirements]]와 [[interface-roadmap]]를 함께 보는 편이 정확하다.^[raw/articles/docmesh-rag-core-prd-2026-06-23.md]

## Related pages

- [[ragcore]]
- [[product-scope-and-requirements]]
- [[ingestion-pipeline]]
- [[persistence-and-restart-recovery]]
- [[service-factory-registry]]
- [[interface-roadmap]]
