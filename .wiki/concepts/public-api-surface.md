---
title: Public API Surface
created: 2026-06-11
updated: 2026-08-18
type: concept
tags: [sdk, api, python, integration]
sources: [raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md, raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]
confidence: high
---

# Public API Surface

이 페이지는 외부 애플리케이션이 `rag_system_core`와 document-management 경계를 어떻게 안정적으로 import하고 호출해야 하는지 정리한다. 두 SDK 모두 내부 module보다 문서화된 package root와 adapter protocol을 소비 경계로 삼는다.

## Import boundary

RAG Core의 권장 import 경로는 `from rag_system_core import RAGCore` 및 문서화된 `rag_system_core.types`다. `dms-core` v0.9.0의 안정적인 import 경계는 `from dms import ...`이며, `dms.sdk`는 같은 공개 이름을 재-export할 수 있지만 소비 코드는 package root를 기준으로 고정한다. API reference 기준 `dms.__all__`은 `dms.sdk.__all__`과 `DocumentStatus`를 합성한 54개 이름이다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]

## DMS construction and operational methods

v0.9.0의 client assembly는 host가 만든 SQLAlchemy `Engine`과 MinIO client를 `DocumentManagementSDKFactory`에 전달하고 `create()` 또는 `create_async()`를 호출하는 경로다. 이미 준비된 metadata/object/optional operation component를 사용하는 경우 `DefaultDocumentManagementSDK`를 직접 조립한다. v0.9.0 문서는 환경변수를 읽는 DMS factory, `create_sdk_from_environment()`, `create_sdk_from_service_configs()`, `DmsAssemblyPlan`, `check_health()`를 current root contract에서 제외한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

DMS facade surface는 upload, operation lookup, public/internal metadata, cursor page/iterator, content·stream·copy, delete/reset, inspection·recovery plan을 포함하는 26개 작업이다. sync facade, async facade, sync/async scoped facade가 같은 결과 의미를 공유하며, async 작업은 awaitable과 async iterator로 소비한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]

## Public data and security boundary

DMS의 일반 결과는 `PublicDocumentMetadata`, `UploadDocumentResult`, `DocumentPage`, `DocumentContent` 같은 public-safe 모델을 사용한다. `PublicDocumentMetadata`와 canonical JSON schema에는 `storage_key`가 없으며, 내부 저장 위치가 필요한 `DocumentMetadata`·inspection·recovery 결과는 외부 API 응답에 그대로 재노출하지 않는다. RAG adapter가 `document_id`, checksum, size, content type을 외부 참조로 제공하되 object-store locator를 `storage_path`처럼 복사하지 않는 이유가 여기에 있다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]

## Policy, protocol, and error surface

`AccessContext`·`DocumentAccessPolicy`는 host-defined 권한 정책 seam이고 `DmsOperationContext`·`sdk.scoped(...)`는 created_by, idempotency scope, audit actor, 기본 metadata를 작업 범위로 주입한다. `DocumentWriter`·`DocumentReader`·`DocumentLister`·`DocumentDeleter`·`DataResetter`·`DocumentManagementClient` protocol은 concrete class 전체에 결합하지 않는 typing/test seam이다. `DmsError`의 stable code/category/retryable은 API/MCP adapter가 전송 계층을 별도로 소유하도록 한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]^[raw/articles/dms-core-examples-v0.9.0-2026-08-18.md]

DMS facade는 host가 주입한 resource lifecycle을 소유하지 않으므로, API/MCP adapter는 connection readiness·cleanup과 DMS document 작업을 하나의 DMS `close()` 계약으로 합치지 않는다. HTTP status와 response body도 host transport가 결정한다.^[raw/articles/dms-core-api-reference-v0.9.0-2026-08-18.md]

## Existing RAG surface and integration implications

RAG Core의 `EmbeddingClient`, `GenerationClient`, record type, ingestion/query API는 [[rag-service-architecture]]와 [[ingestion-pipeline]]의 책임을 따른다. DMS를 API나 MCP로 감쌀 때는 두 SDK의 root export와 public-safe model을 adapter 경계에서 조합하고, 내부 구현·storage locator·host secret이 새 인터페이스로 새지 않게 유지한다. 제품 전체 계약은 [[product-scope-and-requirements]], [[software-requirements-and-traceability]], [[construction-paths-and-adapter-contracts]]와 함께 읽는다.

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
