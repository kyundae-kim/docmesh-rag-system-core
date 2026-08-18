---
title: Construction Paths and Adapter Contracts
created: 2026-06-23
updated: 2026-08-18
type: concept
tags: [sdk, api, python, integration, decision]
sources: []
confidence: medium
---

# Construction Paths and Adapter Contracts

`docs/api.md`의 현재본은 DocMesh RAG Core의 public API를 단순 메서드 목록이 아니라 **실제 조립 경로와 adapter 계약**까지 포함한 소비 경계로 설명한다. 위키 관점에서 이 문서의 가장 중요한 보강점은 `RAGCore(...)`가 convenience constructor가 아니라 fully assembled dependency graph를 받는 조립형 생성자라는 사실을 코드 예시와 함께 분명히 고정한다는 점이다.

## Direct construction path

가장 직접적인 생성 경로는 `RAGCore(...)`에 `embedding_client`, `generation_client`, `vector_store`, `metadata_store`, `document_storage`, `chunker`를 모두 주입하는 방식이다. 즉 `metadata_path`나 `chunk_size` 같은 설정값을 `RAGCore` 생성자에 바로 넘기는 예전 서술은 현재 구현과 맞지 않으며, 올바른 첫 성공 경로는 factory helper로 의존성을 만든 뒤 `RAGCore(...)`를 조립하는 것이다.

## Factory assembly path

현재 구현은 `bootstrap_rag_core(...)` 또는 `bootstrap_rag_core_from_env(...)`처럼 환경변수에서 `RAGCore`까지 한 번에 생성하는 public entrypoint를 제공하지 않는다. 권장 경로는 host가 Engine·transport client·RAG collaborator를 명시적으로 준비한 뒤 `DocmeshRAGServiceFactory.from_host_clients(...)` 또는 `DocmeshRAGServiceFactory.from_clients(...)`를 호출하고, 반환된 factory의 `create_rag_core()`로 최종 Core를 조립하는 방식이다.

`load_docmesh_settings()`와 `create_rag_*` helper는 선택된 환경 설정을 읽을 수 있는 하위 composition helper지만, 그 자체로 `RAGCore`를 생성하는 entrypoint는 아니다. 이 경계는 [[public-api-surface]]와 [[service-factory-registry]]를 잇는 현재 composition contract로 이해해야 한다.

## Composition helper behavior

API 문서는 `create_rag_embedding_client`, `create_rag_generation_client`, `create_rag_vector_store`, `create_rag_metadata_store`, `create_rag_document_storage`, `create_rag_chunker`의 시그니처와 fallback 동작을 구체적으로 문서화한다. 특히 vector store factory는 가능하면 DocMesh settings에서 Milvus runtime 설정을 읽고, 실패하면 `metadata_path.with_suffix('.milvus.db')`, `rag_chunks`, `30.0`을 fallback으로 사용한다. config guide는 이 fallback 때문에 첫 성공 호출의 핵심 필수값이 Milvus env 전체가 아니라 writable `metadata_path`와 Ollama model 설정 쪽에 더 가깝다고 설명한다.

## Protocol and record contracts

문서는 `EmbeddingClient.embed(texts: list[str]) -> list[list[float]]`와 `GenerationClient.generate(prompt: str) -> str`를 protocol contract로 다시 고정하고, `DocumentRecord`, `ChunkRecord`, `IngestResult`, `IngestionProgressRecord`, `QueryResult`의 필드 shape도 공개 타입으로 제시한다. 따라서 이 페이지는 [[public-api-surface]]의 high-level boundary 설명과 달리, 외부 통합 코드가 어느 수준까지 데이터 shape에 의존해도 되는지 판단하는 기준선이 된다.

## Ollama adapters

API 문서는 `OllamaEmbeddingClient`와 `OllamaGenerationClient`도 root export로 공개하고, 각각의 transport/malformed response 오류 모델까지 명시한다. 또한 해당 adapter나 factory를 쓰려면 Python 패키지 `ollama`가 필요하다고 적시하므로, 런타임 전제조건은 [[public-api-surface]]와 별개로 실제 소비 환경 구성의 일부다. config guide는 여기서 더 나아가 `OLLAMA_HOST`, `OLLAMA_EMBEDDING_MODEL`, `OLLAMA_GENERATION_MODEL`을 first-success 경로의 핵심 env로 묶는다.

## Related pages

- [[first-success-configuration]]
- [[public-api-surface]]
- [[ragcore]]
- [[service-factory-registry]]
- [[persistence-and-restart-recovery]]
- [[user-scope-isolation]]
- [[software-requirements-and-traceability]]
