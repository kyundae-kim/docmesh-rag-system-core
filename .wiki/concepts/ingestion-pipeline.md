---
title: Ingestion Pipeline
created: 2026-06-11
updated: 2026-08-18
type: concept
tags: [ingestion, pipeline, chunking, embeddings, vector-store]
sources: []
confidence: high
---

# Ingestion Pipeline

DocMesh RAG Core의 ingestion pipeline은 문서를 수집해 검색 가능한 상태로 전환하는 핵심 흐름이다. 현재 PRD와 acceptance criteria 기준 단계 순서는 `load -> preprocess -> chunking -> embedding -> vector_store -> chunk_persistence`이며, API 문서는 ingestion 결과에 `job_id`가 포함된다고 명시한다.

## Supported inputs

현재 SDK는 텍스트 본문, 파일 스트림, 파일 경로 세 가지 입력 방식을 지원한다. 파일 스트림 ingestion은 `source`를 명시적으로 요구하며, 비어 있거나 공백이면 실패해야 한다. 파일 기반 ingestion은 현재 구현상 UTF-8 decode 가능한 텍스트를 전제한다.

## Processing requirements

전처리는 현재 구현 기준 `strip()` 수준이며, 청킹은 고정 길이 window + overlap 방식을 사용한다. 빈 텍스트는 ingest할 수 없어야 하며, ingestion 시 chunk 전체는 하나의 `embed(chunks)` batch 호출로 처리되어야 한다. 생성된 벡터 수는 chunk 수와 일치해야 하고, vector store 적재 뒤 chunk metadata persistence가 이어져야 한다.

## Progress tracking

각 ingest 실행은 `job_id`로 식별되며 단계 상태는 최소 `running`, `completed`, `failed`를 표현해야 한다. progress 조회는 문서와 user scope 기준으로 제한되어야 하므로, 이 페이지는 단순 배치 흐름 설명이 아니라 [[user-scope-isolation]]과 직접 연결되는 운영 계약으로 읽어야 한다.

## Related pages

- [[ragcore]]
- [[product-scope-and-requirements]]
- [[user-scope-isolation]]
- [[persistence-and-restart-recovery]]
- [[rag-service-architecture]]
