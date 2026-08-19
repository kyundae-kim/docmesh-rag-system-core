---
title: First Success Configuration
created: 2026-06-23
updated: 2026-08-18
type: concept
tags: [config, sdk, integration, decision, deployment]
sources: []
confidence: medium
---

# First Success Configuration

`docs/config.md`의 현재본은 DocMesh RAG Core를 처음 띄울 때 필요한 설정을 "모든 env를 완성하는 것"이 아니라 **첫 성공 호출을 만드는 최소 조합**으로 설명한다. 위키 관점에서 이 문서의 핵심 가치는 설정 범위를 운영 전체가 아니라 `single-user`, local storage, helper-based assembly, Ollama + Milvus Lite fallback 조합으로 좁혀 준다는 점이다.

## Minimal first-success path

가장 쉬운 첫 성공 전략은 `DOCMESH_AUTH_MODE`를 비워 두고 token도 생략해 `single-user` 경로로 가며, `create_rag_*` helper로 구성요소를 만든 뒤 `RAGCore(...)`를 직접 조립하고, `storage_mode="local"`과 기본 Ollama/Milvus Lite 경로를 사용하는 것이다. 이때 최소 권장 env는 `OLLAMA_HOST`, `OLLAMA_EMBEDDING_MODEL`, `OLLAMA_GENERATION_MODEL` 세 개다.

## Why this matters

이 가이드는 "설정이 많아 보여도 실제 첫 호출엔 대부분 필요 없다"는 해석 기준을 제공한다. 예를 들어 Keycloak, custom collection, custom timeout, 별도 bootstrap helper, registry 주입은 첫 성공 호출의 필수 전제가 아니며, 오히려 너무 일찍 도입하면 디버깅 표면만 넓힌다. 따라서 초기 온보딩 설명은 [[construction-paths-and-adapter-contracts]]와 [[user-scope-isolation]]을 함께 참조하되, 명시적 factory/direct assembly의 최소 경로를 먼저 제시하는 편이 맞다.

## Milvus fallback implications

`create_rag_vector_store(...)`는 Milvus 관련 env가 비어 있어도 `metadata_path.with_suffix('.milvus.db')`, `rag_chunks`, `30.0` fallback으로 동작할 수 있다. 따라서 첫 성공 호출의 진짜 필수 경계는 Milvus env 전체가 아니라 writable `metadata_path`와 실제 embedding/generation 런타임 접근성에 더 가깝다.

## Recommended defaults

문서가 권장하는 단순한 로컬 조합은 `OLLAMA_HOST=http://ollama:11434`, `OLLAMA_EMBEDDING_MODEL=bge-m3`, `OLLAMA_GENERATION_MODEL=gpt-oss:20b`, `storage_mode="local"`, `metadata_path=./data/metadata.db`, `document_storage_dir=./data/documents`, token 생략이다. 이 조합에서는 user scope가 `single-user`, auth mode가 기본 token mode, Milvus URI가 `./data/metadata.milvus.db` 형태 fallback, collection이 `rag_chunks`, chunker 예시가 `512/64`로 수렴한다.

## Related pages

- [[construction-paths-and-adapter-contracts]]
- [[user-scope-isolation]]
- [[service-configuration-topology]]
- [[settings-loading-and-validation]]
- [[public-api-surface]]
