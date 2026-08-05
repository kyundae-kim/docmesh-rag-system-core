---
title: Public API Surface
created: 2026-06-11
updated: 2026-08-04
type: concept
tags: [sdk, api, python, integration]
sources: [raw/articles/docmesh-rag-core-api-reference-2026-06-23.md, raw/articles/docmesh-rag-core-prd-2026-06-23.md, raw/articles/docmesh-rag-core-srs-2026-06-23.md, raw/articles/docmesh-rag-core-test-spec-2026-06-11.md, raw/articles/docmesh-py-core-api-guide-2026-06-19.md, raw/articles/docmesh-py-core-api-reference-v0.2.0-2026-07-16.md, raw/articles/docmesh-py-core-api-reference-v0.5.0-2026-07-27.md, raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md, raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md, raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md, raw/articles/dms-core-examples-v0.7.0-2026-08-04.md, raw/articles/docmesh-py-core-api-reference-v0.6.0-2026-08-04.md]
confidence: high
---

# Public API Surface

이 페이지는 외부 애플리케이션이 `rag_system_core`와 document-management 경계를 어떻게 안정적으로 import하고 호출해야 하는지 정리한다.

## Import boundary

권장 import 경로는 `from rag_system_core import RAGCore` 및 `from rag_system_core.types import ...`이다. RAG Core의 root export, adapter protocol, composition helper는 문서화된 public surface로만 사용하고 domain/storage 내부 모듈 import는 피한다.

`dms-core` v0.7.0의 권장 import 경계도 `dms` package root다. `dms.__all__`은 sync/async factory와 facade, `DmsAssemblyPlan`, resource ownership, access/operation context, 기능별 protocol, public/internal data model, recovery·health·error·HTTP projection을 포함한다. `dms.sdk`는 재-export를 제공할 수 있지만 소비 코드는 root를 기준으로 고정한다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]

## DMS construction and operational methods

현재 문서화된 DMS 조립 경로는 호스트가 만든 client를 받는 `create_sdk_from_clients()`와 저장소 component를 받는 `create_sdk_from_components()` 및 각 async variant다. v0.7.0 configuration은 environment variable을 읽는 public factory, DMS connection 자동 생성, `.env`와 `create_sdk_from_service_configs()`를 현재 DMS public contract에서 제외한다. 따라서 v0.6.0 페이지의 environment/service-config 경로는 버전 이력으로만 취급하고, v0.7.0 integration은 host composition을 명시해야 한다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]

DMS operational surface는 upload bytes/file/known-size stream, operation 조회, public/internal metadata, cursor page/iterator, content·stream·copy, soft/hard delete, 전체 reset, health, inspection·reconciliation으로 구성된다. 기본 sync facade, async facade, immutable scoped facade가 같은 작업 계약을 공유하며, async 작업은 awaitable과 async iterator로 소비한다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]

## Public data and security boundary

DMS의 일반 결과는 `PublicDocumentMetadata`, `UploadDocumentResult`, `DocumentPage`, `DocumentContent` 같은 public-safe 모델을 사용한다. `PublicDocumentMetadata`와 canonical JSON schema에는 `storage_key`가 없으며, 내부 저장 위치가 필요한 recovery/admin 경로는 외부 API 응답으로 그대로 재노출하지 않는다. RAG adapter가 `document_id`, checksum, size, content type을 외부 참조로 제공하되 object-store locator를 `storage_path`처럼 복사하지 않는 이유가 여기에 있다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]

## Policy, protocol, and error surface

`AccessContext`·`DocumentAccessPolicy`는 host-defined 권한 정책 seam이고 `DmsOperationContext`·`sdk.scoped(...)`는 created_by, idempotency scope, audit actor, 기본 metadata를 immutable 작업 범위로 주입한다. `DocumentWriter`·`DocumentReader`·`DocumentLister`·`DocumentDeleter`·`DataResetter`·`DocumentHealth` protocol은 concrete class 전체에 결합하지 않는 typing/test seam이다. `DmsError`의 stable code/category/retryable과 `error_descriptor()`·`recommended_http_error()`는 API/MCP adapter가 전송 계층을 별도로 소유하도록 한다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]

## Existing RAG surface and integration implications

RAG Core의 `EmbeddingClient`, `GenerationClient`, record type, ingestion/query API는 기존 [[rag-service-architecture]]와 [[ingestion-pipeline]]의 책임을 따른다. DMS를 API나 MCP로 감쌀 때는 두 SDK의 root export와 public-safe model을 adapter 경계에서 조합하고, 내부 구현·storage locator·host secret이 새 인터페이스로 새지 않게 유지한다. 제품 전체 계약은 [[product-scope-and-requirements]], [[software-requirements-and-traceability]], [[construction-paths-and-adapter-contracts]]와 함께 읽는다.

## Related pages

- [[ragcore]]
- [[product-scope-and-requirements]]
- [[software-requirements-and-traceability]]
- [[construction-paths-and-adapter-contracts]]
- [[rag-service-architecture]]
- [[ingestion-pipeline]]
- [[service-factory-registry]]
- [[dms-core]]
- [[dms-configuration-and-assembly]]
