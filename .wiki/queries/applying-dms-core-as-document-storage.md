---
title: Applying dms-core as Document Storage
created: 2026-07-27
updated: 2026-08-04
type: query
tags: [architecture, integration, sdk, persistence, decision, security]
sources: [raw/articles/dms-core-api-reference-v0.6.0-2026-07-27.md, raw/articles/dms-core-configuration-v0.6.0-2026-07-27.md, raw/articles/dms-core-examples-v0.6.0-2026-07-27.md, raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md, raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md, raw/articles/dms-core-examples-v0.7.0-2026-08-04.md, raw/articles/docmesh-rag-core-api-reference-2026-06-23.md, raw/articles/docmesh-rag-core-prd-2026-06-23.md, raw/articles/docmesh-rag-core-srs-2026-06-23.md]
confidence: medium
---

# Applying dms-core as Document Storage

## 질문

`dms-core` v0.7.0을 DocMesh RAG Core의 `DocumentStorage`로 어떻게 적용해야 하는가?

## 결론

`dms-core`를 단순 MinIO client로 축소하지 않고 **원문 자산의 저장·조회·삭제·무결성·복구를 소유하는 document-management 경계**로 적용한다. RAG Core의 `MetadataStore`는 chunk·embedding·ingestion progress·검색·user-scope 관계 같은 RAG 고유 상태를 유지하고, 두 경계는 공개 `document_id`로 연결한다. DMS의 `storage_key`는 public asset reference나 기존 `storage_path` 필드로 복사하지 않는다.

## 책임 분리

| 책임 | 권장 소유자 |
| --- | --- |
| 원문 bytes/stream 저장·다운로드·checksum·size·content type | `dms-core` |
| DMS document 상태, soft/hard delete, object 정합성 복구 | `dms-core` |
| DMS internal `storage_key` | `dms-core` 관리·복구 경계 |
| RAG document와 DMS document 연결 | RAG `MetadataStore`의 동일 `document_id` 또는 `dms_document_id` |
| chunk, embedding/vector ID, ingestion progress | RAG Core |
| user-scope 제품 관계와 검색 필터 | RAG Core 및 host policy |
| HTTP/API/MCP 오류 변환 | transport adapter; 필요하면 `recommended_http_error()` |

이 분리는 [[rag-service-architecture]]의 원문 자산과 RAG metadata 분리를 유지하면서 [[dms-metadata-and-recovery]]의 public/internal 경계를 보존한다. DMS metadata store를 RAG의 `documents`, `chunks`, `ingestion_progress` 전체 저장소로 재사용하면 두 상태 모델과 삭제 의미가 결합된다.

## v0.7.0 조립 위치

v0.7.0 DMS는 환경변수나 `.env`를 읽지 않고, host가 만든 client/component를 받는다. application composition에서 process lifecycle당 한 번 조립하고 adapter에 주입한다.

1. host가 설정·secret manager를 읽어 SQLAlchemy `Engine`과 MinIO client를 만들거나 metadata/object/operation store를 준비한다.
2. client 경로면 `create_sdk_from_clients()` 또는 async variant를, adapter/test fake 경로면 `create_sdk_from_components()` 또는 async variant를 사용한다.
3. `DmsAssemblyPlan`에 max size, startup check, access policy, observer, audit hook과 metadata policy를 묶어 전달한다.
4. 기본 injected resource는 caller-owned로 두고, DMS가 닫을 자원만 `ManagedResource(SDK)` 또는 `close_callbacks`로 등록한다.
5. bootstrap 종료에서 `close()`/`aclose()`를 정확한 ownership에 따라 호출한다.

`DmsServiceConfigs`를 사용하더라도 그것은 host 설정 value object일 뿐이며 v0.7.0 DMS factory가 자동으로 client를 만드는 입력은 아니다. v0.6.0의 `create_sdk_from_service_configs()`·`create_sdk_from_environment()` 전제를 v0.7.0에 그대로 이식하지 말고 설치 package signature를 확인한다.^[raw/articles/dms-core-configuration-v0.7.0-2026-08-04.md]^[raw/articles/dms-core-examples-v0.7.0-2026-08-04.md]

## Adapter 계약

`DmsDocumentStorage`는 package-root API만 사용하며 다음 의미를 제공한다.

- `save`: `UploadDocumentRequest` 또는 known-size stream request로 업로드하고 public `document_id`·checksum·size·content type을 반환한다.
- `read`: 작은 본문은 `get_document_content()`, 큰 본문은 context manager stream·`iter_document_chunks()`·`copy_document_to()`를 사용한다.
- `delete`: 일반 사용자 요청은 `soft_delete_document()`에 매핑하고 `hard_delete_document()`는 관리자/보존 정책 경계에 둔다.
- metadata/exists: `get_document_metadata()`를 사용하고 not-found/deleted를 port 수준 결과로 변환한다.
- `health`: `check_health()`를 전체 service readiness에 합친다.
- `close`: adapter 또는 bootstrap이 SDK ownership에 맞는 단일 lifecycle을 제공한다.

DMS v0.7.0의 generic `AccessContext`·`DocumentAccessPolicy`를 사용할 수 있지만 tenant/user 의미 자체는 host가 소유한다. RAG `MetadataStore`의 소유 관계를 policy와 함께 검사하고, DMS `extra_metadata`를 인가의 유일한 근거로 삼지 않는다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]

## Ingestion 흐름

1. token에서 host/RAG `user_id`와 access context를 해석한다.
2. 애플리케이션 `document_id` 또는 안정적인 요청 ID를 먼저 확정한다.
3. DMS에 원문을 업로드하고 재시도 가능한 bytes 작업이면 persistent operation store와 `idempotency_scope`/`idempotency_key`를 사용한다.
4. DMS public metadata와 동일 document ID를 RAG document record에 연결한다.
5. 원문을 preprocess·chunk·embed하고 vector store와 chunk metadata에 적재한다.
6. 성공 시 ingestion progress를 completed로 기록한다.
7. 중간 실패는 failed progress와 보상 작업을 기록한다. DMS 업로드 후 즉시 hard delete로 숨기기보다 soft delete 또는 명시적 cleanup/recovery job으로 처리한다.

DMS input stream은 닫지 않고 DMS output stream은 caller가 닫으므로, 이 흐름은 SQL/MinIO/vector store를 하나의 ACID transaction으로 가정하지 않는 saga다. 세부 lifecycle은 [[dms-document-lifecycle]]과 [[ingestion-pipeline]]을 함께 따른다.

## User scope, delete, and recovery

DMS policy는 generic allow/deny seam을 제공하지만 RAG의 `document_id`와 현재 user/tenant 소유 관계는 RAG metadata에서 확인한다. 사용자 목록을 DMS 전체 목록에 직접 노출하지 말고 RAG scope query를 기준으로 필요한 public metadata만 결합한다. internal metadata와 recovery는 별도 administrative capability로 보호한다.

삭제는 다음과 같이 재시도 가능한 상태로 만든다.

1. RAG document를 논리적 deleting 상태로 전환한다.
2. vector entry를 먼저 삭제한다. 실패하면 DMS와 RAG metadata를 보존하고 재시도한다.
3. DMS 원문을 soft delete한다.
4. chunk/progress metadata를 정책에 따라 정리하거나 tombstone을 남긴다.
5. retention 만료 또는 관리자 작업에서만 hard delete한다.

DMS의 `inspect_document()`, `list_recovery_candidates()`, dry-run reconciliation plan은 DMS metadata/object 불일치에 사용하고, vector/RAG metadata 불일치는 애플리케이션 reconciliation이 담당한다. 기존 restart 요구는 [[persistence-and-restart-recovery]]를 따른다.^[raw/articles/dms-core-api-reference-v0.7.0-2026-08-04.md]

## Configuration and rollout

로컬 첫 적용은 host가 SQLite engine과 MinIO client를 직접 구성하는 client factory 또는 fake component factory로 시작한다. 운영에서는 host configuration layer에서 PostgreSQL/MinIO 보안 설정을 검증하고 DMS factory에 주입하며, DMS가 env를 읽는다고 가정하지 않는다. startup mandatory health는 `DmsAssemblyPlan(check_on_startup=True)`로, runtime observation은 `check_health()`로 구분한다.

구현 순서는 다음과 같다.

1. 현재 `DocumentStorage` protocol과 `storage_path` 사용처를 조사해 opaque `document_id` 경계를 정한다.
2. DMS client/component를 소유하는 composition provider와 종료 경로를 추가한다.
3. fake component 기반 save/read/delete/health/error contract test를 작성한다.
4. ingestion에 동일 document ID, idempotency scope/key, 실패 보상을 연결한다.
5. access policy와 user-scope 검사를 get/list/download/delete/recovery 전 경로에 적용한다.
6. vector → DMS → metadata 삭제 순서와 reconciliation retry를 검증한다.
7. SQLite+MinIO smoke test, 재시작 복원, 전체 consumer regression을 실행한다.

실제 repository 구현 전에는 설치된 `dms` version/tag/commit과 현재 `DocumentStorage` protocol을 함께 검증해야 한다. 이 페이지의 v0.7.0 내용은 수집된 문서 기반이며 live package 또는 consumer integration을 새로 실행했다는 뜻은 아니다.

## Related pages

- [[dms-core]]
- [[dms-configuration-and-assembly]]
- [[dms-document-lifecycle]]
- [[dms-metadata-and-recovery]]
- [[rag-service-architecture]]
- [[ingestion-pipeline]]
- [[user-scope-isolation]]
- [[persistence-and-restart-recovery]]
- [[verifying-dms-core-contract]]
- [[minimizing-consumer-implementation-with-dms-core-improvements]]
