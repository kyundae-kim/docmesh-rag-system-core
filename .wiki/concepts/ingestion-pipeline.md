---
title: Ingestion Pipeline
created: 2026-06-11
updated: 2026-06-11
type: concept
tags: [ingestion, pipeline, chunking, embeddings, vector-store]
sources: [raw/articles/docmesh-rag-core-api-reference-2026-06-11.md, raw/articles/docmesh-rag-core-prd-2026-06-11.md, raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]
confidence: high
---

# Ingestion Pipeline

DocMesh RAG Core의 ingestion pipeline은 문서를 수집해 검색 가능한 상태로 전환하는 핵심 흐름이다. PRD 기준 순서는 `Load -> Preprocess -> Chunking -> Embedding -> Chunk persistence -> Vector Store 저장`이며, API 문서는 ingestion 결과에 `job_id`가 포함된다고 명시한다.^[raw/articles/docmesh-rag-core-prd-2026-06-11.md]^[raw/articles/docmesh-rag-core-api-reference-2026-06-11.md]

## Supported inputs

현재 SDK는 텍스트 본문, 파일 스트림, 파일 경로 세 가지 입력 방식을 지원한다. 파일 스트림 ingestion은 `source`를 명시적으로 요구하며, 파일 경로 ingestion은 `source` 생략 시 파일명을 기본값으로 사용한다.^[raw/articles/docmesh-rag-core-api-reference-2026-06-11.md]

## Processing requirements

청킹은 MVP에서 고정 길이 청킹과 overlap 설정을 지원한다. 임베딩은 batch 처리 구조를 전제로 하며, 생성된 청크와 임베딩은 persistence와 vector store 양쪽에 반영되어야 한다. 테스트 명세는 이 경로가 실제 persistence와 검색 복원으로 이어지는지를 중점 검증한다.^[raw/articles/docmesh-rag-core-prd-2026-06-11.md]^[raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]

## Progress tracking

각 ingest 실행은 `job_id`로 식별되며 단계 상태는 최소 `running`, `completed`, `failed`를 표현해야 한다. 테스트 명세는 단계 순서를 `load -> preprocess -> chunking -> embedding -> vector_store -> chunk_persistence`로 기대하므로, 구현/문서 간 표현 차이가 없는지 추후 코드와 함께 계속 확인할 필요가 있다.^[raw/articles/docmesh-rag-core-test-spec-2026-06-11.md]

## Related pages

- [[ragcore]]
- [[user-scope-isolation]]
- [[persistence-and-restart-recovery]]
- [[rag-service-architecture]]
