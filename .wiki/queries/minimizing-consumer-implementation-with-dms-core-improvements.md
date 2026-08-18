---
title: Minimizing Consumer Implementation with dms-core Improvements
created: 2026-07-30
updated: 2026-08-18
type: query
tags: [sdk, integration, architecture, config, api, testing, persistence, roadmap]
sources: []
confidence: medium
---

# Minimizing Consumer Implementation with dms-core Improvements

## 질문

소비 프로젝트가 반복해서 작성하는 DMS 설정 변환, 조립, 자원 소유권, 업로드 입력 변환, pagination, 접근제어 및 테스트 코드를 줄이려면 `dms-core` 자체를 어떻게 개선해야 하는가?

## 경계 원칙

`dms-core`는 **원문 문서의 저장·조회·삭제·무결성·복구와 그에 필요한 인프라 lifecycle**을 소유해야 한다. 소비 프로젝트는 문서가 RAG chunk·vector·사용자 workflow와 어떤 관계를 갖는지 같은 제품 정책만 소유한다. 즉 반복 가능한 document-management mechanics는 upstream으로 이동하되, RAG ingestion saga나 tenant 정책을 DMS가 임의로 결정해서는 안 된다. 이 경계는 [[applying-dms-core-as-document-storage]]와 [[rag-service-architecture]]의 책임 분리를 유지한다.

## 현재 문서화된 상태

v0.6.0은 환경, `ServiceConfigs`, caller-owned clients, 직접 components의 네 조립 경로를 제공한다. bytes·동기/비동기 stream 업로드, 공개/internal metadata 분리, cursor pagination, soft/hard delete, idempotency, recovery, health, HTTP 오류 변환과 sync/async context manager까지 갖추고 있어 document lifecycle 자체는 이미 넓게 추상화되어 있다.

소비자 구현이 남는 핵심 원인은 기능 부족보다 **진입점 간 계약 비대칭**이다. `diagnose_environment(env)`는 mapping을 받지만 `create_sdk_from_environment()`는 process environment만 읽는다. 네 factory는 공통 옵션을 각각 나열하고, 주입 자원 소유권은 `close_callbacks`로 표현한다. 다섯 upload 메서드와 수동 cursor loop도 사용처마다 반복된다.

## 반복 구현과 upstream 개선점

| 소비 프로젝트에 남는 코드 | 현재 원인 | 권장 upstream 계약 |
| --- | --- | --- |
| `DMS_` prefixed 값을 canonical config로 수동 변환 | environment factory가 process-global fixed key만 읽음 | 명시적 `env` mapping과 namespace 지원 |
| diagnosis 후 다른 설정 source로 다시 assembly | diagnosis와 environment factory의 입력 경계가 다름 | 동일 mapping을 쓰는 diagnose+assemble 경로 |
| 네 factory마다 validator·health·size 옵션 반복 | 공통 assembly plan 부재 | immutable `DmsAssemblyPlan`/options |
| 주입 client별 close callback wiring | 자원 소유권이 callback 목록으로만 표현 | typed ownership descriptor |
| 소비 프로젝트별 DMS protocol/fake 재작성 | 공개 API가 concrete SDK 중심 | capability 기반 public Protocol |
| 파일 open·size·MIME·checksum·stream request 조립 | low-level upload request만 제공 | `upload_file()`/`upload_source()` convenience API |
| cursor와 filter를 보존하는 반복 loop | page 단위 API만 제공 | `iter_documents()` iterator |
| download stream close/copy loop 반복 | stream lifecycle이 호출자 책임 | SDK-owned copy/iteration helper |
| 모든 호출 전 user/tenant 소유권 검사 반복 | 일반 access policy hook 없음 | generic access-context/policy seam |

## P0 — 설정·조립·소유권의 단일 계약

### 1. 환경 factory에 mapping과 namespace를 지원한다

`create_sdk_from_environment()`가 `diagnose_environment()`와 같은 `Mapping[str, str]`을 받을 수 있어야 한다. process environment는 기본 adapter로 유지하되 `env`가 전달되면 해당 mapping만 사용하고, 진단과 조립이 정확히 같은 snapshot을 소비해야 한다. `prefix="DMS_"` 또는 key-mapper를 함께 지원하면 동일 process의 RAG와 DMS가 서로 다른 PostgreSQL·SQLite·MinIO 구성을 사용해도 consumer가 config model을 수동 조립할 필요가 없다.

권장 최소 계약:

- `diagnose_environment(env, namespace=...)`와 `create_sdk_from_environment(env=..., namespace=...)`가 동일 선택·검증 코드 사용
- 전달 mapping과 process environment를 암묵적으로 병합하지 않음
- namespace 제거 후 중복 key와 부분 설정을 `ConfigurationError.diagnosis`에 기록
- 오류에는 소비자가 제공한 원래 key 이름을 남기되 secret 값은 노출하지 않음
- 기존 인자 없는 environment 경로는 호환성 유지

이 기능이 생기면 [[separating-dms-service-environment-variables-with-prefixes]]에 기록된 consumer-side `load_dms_settings()`와 canonical mapping 변환이 제거 후보가 된다.

### 2. 네 factory가 공유하는 assembly plan을 도입한다

metadata policy, 최대 파일 크기, startup health, logger, audit hook, 자원 소유권 같은 공통 옵션을 immutable `DmsAssemblyPlan` 또는 `DmsSdkOptions`로 묶는다. 환경·config·client·component factory가 같은 plan을 받으면 factory를 바꿔도 정책이 누락되지 않는다.

plan이 소유할 수 있는 항목은 다음으로 제한한다.

- metadata backend 선택과 strict policy
- metadata validator 또는 기본 size/depth 정책
- upload `max_file_size`
- startup healthcheck/timeout/failure policy
- recovery audit 및 operation observer hook
- 주입 자원의 ownership policy

database endpoint나 MinIO credential을 plan에 직접 넣지 않는다. 연결값은 environment/config/client 경계에 남겨 secret과 정책을 분리한다.

### 3. `close_callbacks`를 typed ownership 계약으로 보강한다

`create_sdk_from_clients()`와 `create_sdk_from_components()`는 주입 자원을 기본적으로 caller-owned로 두는 현재 원칙이 안전하다. 그러나 소비자가 종료 책임을 SDK에 넘길 때 callback 순서와 sync/async 차이를 직접 구성해야 한다. `ManagedResource(resource, ownership=SDK, close=..., aclose=...)` 또는 factory별 명시적 ownership descriptor를 제공하면 lifecycle 코드와 테스트를 줄일 수 있다.

필수 검증은 다음과 같다.

- 기본값은 계속 caller-owned
- SDK-owned 자원만 역순으로 정확히 한 번 종료
- 중간 assembly/startup 실패에서도 이미 생성한 SDK-owned 자원 rollback
- sync `close()`와 async `aclose()`의 지원 범위를 명확히 진단
- 여러 종료 실패를 모두 시도한 뒤 구조화해 집계

### 4. capability 기반 public Protocol을 제공한다

소비자가 `DefaultDocumentManagementSDK` 전체를 fake하거나 자체 protocol을 반복 정의하지 않도록 package root에 작은 capability protocol을 제공한다.

- `DocumentWriter`: upload 계열
- `DocumentReader`: metadata/content/stream 조회
- `DocumentLister`: page/iterator 조회
- `DocumentDeleter`: soft/hard delete
- `DocumentHealth`: health check
- `DocumentManagementClient`: 위 capability의 aggregate

이 protocol은 runtime implementation을 추가하는 기능이 아니라 안정적인 typing/test seam이다. RAG adapter는 여전히 자신의 `DocumentStorage` port를 소유하지만, fake가 DMS concrete class 전체를 모방할 필요는 없어진다.

## P1 — 문서 작업 boilerplate 축소

### 5. 고수준 upload source helper를 추가한다

현재 다섯 request와 메서드는 소유권·크기·async 차이를 명시한다는 장점이 있으므로 유지해야 한다. 그 위에 일반 사용을 위한 convenience API를 추가한다.

- `upload_file(path, *, document_id=None, metadata=None, idempotency=None)`
- `upload_bytes(content, *, filename, content_type, ...)`
- `upload_source(source, *, size=None, max_size=None, ...)`

`upload_file()`은 SDK가 파일 open/close, size, 선택적 checksum과 content type 추론을 소유한다. caller가 넘긴 stream은 기존과 같이 caller-owned로 유지한다. 자동 추론값은 결과/진단에서 확인할 수 있어야 하며 low-level request API는 완전한 제어가 필요한 경로로 남긴다.

### 6. pagination과 download lifecycle helper를 제공한다

`iter_documents(*, status=None, page_size=100)`가 내부적으로 cursor, status, limit 일관성을 유지하면 소비자는 cursor loop를 반복하지 않고 cursor 오용도 줄일 수 있다. recovery에도 `iter_recovery_candidates()`를 같은 방식으로 제공할 수 있다.

다운로드에는 `copy_document_to(document_id, sink, *, chunk_size=...)`와 SDK가 stream을 소유하는 `iter_document_chunks(...)`를 제공할 수 있다. helper가 정상·예외·취소 시 stream을 닫고 checksum/size 결과를 반환하면 API·worker마다 context-manager loop를 복제하지 않아도 된다. raw stream API는 zero-copy나 특수 backpressure가 필요한 escape hatch로 유지한다.

### 7. 접근제어를 위한 generic policy seam을 제공한다

현재 문서화된 DMS API는 `created_by`와 metadata를 저장하지만 user/tenant 인가를 자동 보장하지 않는다. 그래서 소비 프로젝트는 조회·다운로드·목록·삭제 전 경로에서 소유권 검사를 반복해야 한다. DMS가 RAG의 `user_id` 정책을 하드코딩하는 대신 `AccessContext`와 `DocumentAccessPolicy` hook을 받을 수 있게 하면 우회 경로 없이 중앙에서 검사할 수 있다.

- context는 opaque subject/tenant/roles만 제공
- policy는 read/list/delete/recovery capability별 allow/filter를 반환
- 기본 policy는 현재와 같은 unrestricted 동작으로 호환성 유지
- internal metadata와 recovery는 별도 administrative capability 요구
- 목록 filtering을 metadata 후처리로 구현해 page 의미를 깨뜨리지 않음

이 기능은 security-sensitive하므로 단순 callback보다 명시적 protocol과 deny/allow 결과 모델이 필요하다. 실제 tenant 모델은 host application이 소유하며 [[user-scope-isolation]] 계약을 대체하지 않는다.

### 8. 공통 operation context를 선택적으로 제공한다

업로드마다 반복되는 `created_by`, `idempotency_scope`, audit actor와 기본 metadata를 `DmsOperationContext`로 묶을 수 있다. SDK에서 `sdk.scoped(context)`처럼 immutable facade를 만들면 worker/request adapter의 필드 전달 코드가 줄어든다.

단, SDK가 idempotency key를 임의 생성하거나 tenant를 process-global 상태로 저장해서는 안 된다. key와 access context는 호출 단위로 명시되어야 하며 concurrent request 사이에 섞이지 않아야 한다.

## P2 — 운영·확장 편의

- upload/read/delete/recovery 결과를 받는 generic operation observer를 추가해 소비자가 모든 메서드를 logging/metric wrapper로 감싸지 않게 한다.
- `HealthStatus`, page, inspection, reconciliation 결과에 일관된 `to_dict()`를 제공한다.
- `SERVICE_CATALOG`와 같은 설정 metadata를 노출해 `.env.example`과 배포 validation을 생성 가능하게 한다.
- framework별 FastAPI/CLI adapter는 별도 integration package 또는 예제로 유지해 core dependency를 늘리지 않는다.
- file upload, pagination iterator, access policy, managed resources에 대한 package-root contract test를 추가한다.

## DMS core에 넣지 말아야 할 것

- chunking, embedding, vector ID, ingestion progress 같은 RAG domain 상태
- RAG와 DMS를 하나의 ACID transaction처럼 보이게 하는 추상화
- `storage_key`를 public path/reference로 노출하는 convenience API
- 특정 제품의 `user_id` 또는 role 이름을 고정한 authorization
- 전달 mapping과 process environment의 암묵적 merge
- injected client를 기본적으로 자동 종료하는 ownership 변경
- sync 사용자를 async runtime으로 강제하는 단일 facade
- 임의 backend SDK 옵션을 `**kwargs`로 전달하는 escape hatch

## 검증 가능한 성공 기준

1. 동일 process의 DMS namespace 조립에 consumer-side config 변환과 `os.environ` mutation이 0건이다.
2. diagnosis와 assembly가 같은 immutable env snapshot과 backend 선택 결과를 사용한다.
3. 네 factory가 동일 assembly plan으로 metadata·health·size 정책을 유지한다.
4. 주입 자원의 caller/SDK ownership이 타입과 테스트에서 명확하며 모든 종료가 정확히 한 번 수행된다.
5. 대표 consumer의 DMS bootstrap 및 lifecycle LOC가 현재 대비 50% 이상 감소한다.
6. 파일 업로드 경로에서 consumer가 직접 file open/size/checksum request wiring을 하지 않는다.
7. 전체 목록 순회에 consumer cursor loop가 없고 기존 cursor 검증은 유지된다.
8. 고수준 download helper가 정상·예외·취소에서 stream을 닫는다.
9. capability protocol 기반 fake가 내부 module import 없이 contract test를 통과한다.
10. access policy 적용 시 get/list/download/delete/internal/recovery 우회 경로가 없다.
11. public metadata와 convenience helper 어느 경로에서도 `storage_key`가 노출되지 않는다.
12. 기존 low-level request, 네 factory, caller-owned lifecycle 계약은 호환성을 유지한다.

## 권장 rollout

- **P0.1:** `env` mapping/namespace를 diagnosis와 environment assembly에 공통 적용
- **P0.2:** 공통 assembly plan과 typed ownership descriptor 도입
- **P0.3:** capability 기반 public Protocol 및 테스트 seam 고정
- **P1.1:** `upload_file()`/`upload_source()` convenience API
- **P1.2:** document/recovery iterator와 managed download helper
- **P1.3:** generic access policy와 operation context
- **P2:** observer, 일관된 serialization, 설정 catalog, integration adapters

각 단계는 추가 API 수가 아니라 실제 삭제되는 consumer 코드, lifecycle 분기 수, env patch 수, cursor loop 수로 효과를 측정해야 한다. 이 페이지는 수집된 dms-core v0.6.0 문서와 RAG 요구에서 도출한 upstream 제안이며 live package나 repository의 최신 구현 상태를 검증하지 않았다. 실제 변경 전에는 [[verifying-dms-core-contract]]으로 설치 버전과 공개 signature를 다시 확인해야 한다.

## Related pages

- [[dms-core]]
- [[dms-configuration-and-assembly]]
- [[dms-document-lifecycle]]
- [[dms-metadata-and-recovery]]
- [[applying-dms-core-as-document-storage]]
- [[separating-dms-service-environment-variables-with-prefixes]]
- [[user-scope-isolation]]
- [[verifying-dms-core-contract]]
