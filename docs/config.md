# Configuration Guide

이 문서는 `docmesh-rag-system-core`를 **문서만 보고 첫 호출까지 성공시키기 위해 필요한 최소 설정**을 설명합니다.

이 문서의 초점:
- 어떤 env가 필수인지
- 어떤 env가 선택인지
- 첫 성공 호출에는 무엇만 있으면 되는지
- bootstrap / Keycloak 경로는 언제 필요한지

---

## 1. 가장 쉬운 첫 성공 설정

첫 성공 호출만 목표라면 다음 전략이 가장 단순합니다.

- `RAGCore(...)` 직접 생성 사용
- `DOCMESH_AUTH_MODE` 미설정
- token 생략 (`single-user` 경로)
- local storage 사용
- Ollama + Milvus Lite 기본 경로 사용

최소 권장 env:

```env
OLLAMA_HOST=http://ollama:11434
OLLAMA_EMBEDDING_MODEL=bge-m3
OLLAMA_GENERATION_MODEL=gpt-oss:20b
```

이 경우:
- auth는 기본 token mode이지만 token을 안 넘기면 `single-user`
- Milvus URI를 비워도 `metadata_path.with_suffix(".milvus.db")` fallback 가능
- collection을 비워도 `rag_chunks` fallback 가능

---

## 2. canonical configuration example

`.env.example` 기준 예시는 아래와 같습니다.

```env
# docmesh-rag-system-core canonical configuration example
# Legacy envs are no longer supported:
# - OLLAMA_EMBED__*
# - OLLAMA_GENERATE__*
# - MILVUS__*

# Shared Ollama runtime
OLLAMA_HOST=http://ollama:11434
OLLAMA_EMBEDDING_MODEL=bge-m3
OLLAMA_GENERATION_MODEL=gpt-oss:20b
OLLAMA_REQUEST_TIMEOUT_SECONDS=30

# Milvus runtime
MILVUS_URI=./data/metadata.milvus.db
MILVUS_COLLECTION=rag_chunks
MILVUS_REQUEST_TIMEOUT_SECONDS=30
MILVUS_CONNECT_TIMEOUT_SECONDS=30

# Optional auth mode
# DOCMESH_AUTH_MODE=keycloak

# If using keycloak mode, configure the required docmesh-py-core auth settings too.
# Example names depend on your shared docmesh config contract.
# KEYCLOAK_URL=
# KEYCLOAK_REALM=
# KEYCLOAK_CLIENT_ID=
```

---

## 3. 필수 / 권장 / 선택 설정

| 변수 | 분류 | 언제 필요한가 | 비고 |
|---|---|---|---|
| `OLLAMA_HOST` | 권장 | 기본 Ollama adapter를 쓸 때 | 예: `http://ollama:11434` |
| `OLLAMA_EMBEDDING_MODEL` | 사실상 필수 | 기본 Ollama embedding adapter를 쓸 때 | 비어 있으면 client 생성 실패 가능 |
| `OLLAMA_GENERATION_MODEL` | 사실상 필수 | 기본 Ollama generation adapter를 쓸 때 | 비어 있으면 client 생성 실패 가능 |
| `OLLAMA_REQUEST_TIMEOUT_SECONDS` | 선택 | Ollama timeout 조정 시 | 없으면 기본/외부 설정 사용 |
| `MILVUS_URI` | 선택 | Milvus Lite 위치를 직접 지정하고 싶을 때 | 없으면 metadata 경로 기반 fallback 가능 |
| `MILVUS_COLLECTION` | 선택 | collection 이름을 바꾸고 싶을 때 | 없으면 `rag_chunks` |
| `MILVUS_REQUEST_TIMEOUT_SECONDS` | 선택 | Milvus 요청 timeout 조정 시 | 우선 timeout 소스 |
| `MILVUS_CONNECT_TIMEOUT_SECONDS` | 선택 | request timeout이 없을 때 | fallback timeout 소스 |
| `DOCMESH_AUTH_MODE` | 선택 | Keycloak 모드를 켤 때만 | 첫 성공 호출에는 불필요 |
| `KEYCLOAK_URL` | 조건부 필수 | `DOCMESH_AUTH_MODE=keycloak`일 때 | shared docmesh config 계약 따름 |
| `KEYCLOAK_REALM` | 조건부 필수 | `DOCMESH_AUTH_MODE=keycloak`일 때 | shared docmesh config 계약 따름 |
| `KEYCLOAK_CLIENT_ID` | 조건부 필수 | `DOCMESH_AUTH_MODE=keycloak`일 때 | shared docmesh config 계약 따름 |

---

## 4. 설정 우선순위

### 4.1 direct construction (`RAGCore(...)`)

직접 `RAGCore(...)`를 만들 때:
- embedding / generation model은 **당신이 adapter에 직접 넘긴 값**이 가장 중요합니다.
- vector store는 내부에서 Milvus 설정을 읽으려 시도하지만, 실패하면 fallback을 사용합니다.

Milvus fallback:
- URI: `metadata_path.with_suffix(".milvus.db")`
- Collection: `rag_chunks`
- Timeout: `30.0`

즉, direct construction은 **DocMesh 설정이 완벽하지 않아도 시작할 수 있는 경로**입니다.

### 4.2 bootstrap helper (`bootstrap_rag_core_from_docmesh(...)`)

bootstrap helper를 쓸 때는 아래가 필요합니다.
- `docmesh_py_core.load_settings()` 성공
- service registry 생성 성공
- registry가 `ollama` client 생성 가능
- settings에서 embedding / generation model 확인 가능

즉, bootstrap helper는 **환경이 이미 DocMesh 규약에 맞춰져 있을 때** 사용하는 경로입니다.

---

## 5. 첫 성공 호출용 추천 조합

## 5.1 가장 단순한 로컬 조합

```env
OLLAMA_HOST=http://ollama:11434
OLLAMA_EMBEDDING_MODEL=bge-m3
OLLAMA_GENERATION_MODEL=gpt-oss:20b
```

그리고 코드에서는:
- `RAGCore(...)` 직접 생성
- `storage_mode="local"`
- `metadata_path=./data/metadata.db`
- `document_storage_dir=./data/documents`
- token 생략

## 5.2 이때 기대되는 기본 동작

- user scope: `single-user`
- auth mode: 기본 token mode
- Milvus URI: `./data/metadata.milvus.db` 비슷한 fallback 사용
- Milvus collection: `rag_chunks`

---

## 6. 첫 성공 호출에는 필요 없는 것

다음은 **첫 성공 호출만 목표라면 당장 필요하지 않습니다.**

- `DOCMESH_AUTH_MODE=keycloak`
- Keycloak 관련 설정
- custom collection 이름
- custom timeout 값
- bootstrap helper
- 내부 composition/factory 사용

---

## 7. legacy env

`.env.example` 기준으로 다음 패턴은 더 이상 지원하지 않습니다.

- `OLLAMA_EMBED__*`
- `OLLAMA_GENERATE__*`
- `MILVUS__*`

---

## 8. 빠른 사용 절차

1. `.env.example`를 참고해 `.env`를 만듭니다.
2. 최소한 아래 3개를 채웁니다.
   - `OLLAMA_HOST`
   - `OLLAMA_EMBEDDING_MODEL`
   - `OLLAMA_GENERATION_MODEL`
3. Ollama 서버와 모델 준비를 확인합니다.
4. `docs/api.md`의 direct construction 예시로 첫 호출을 시도합니다.

예:

```bash
cp .env.example .env
```

---

## 9. 첫 성공 체크리스트

- [ ] `OLLAMA_HOST`가 올바르다
- [ ] `OLLAMA_EMBEDDING_MODEL`이 설정됐다
- [ ] `OLLAMA_GENERATION_MODEL`이 설정됐다
- [ ] Ollama 서버가 실제로 떠 있다
- [ ] 모델이 실제로 준비되어 있다
- [ ] `DOCMESH_AUTH_MODE`는 비워두었다 (첫 시도 기준)
- [ ] Keycloak 설정에 의존하지 않는다

---

## 10. 관련 파일

- `.env.example`
- `README.md`
- `docs/api.md`
- `docs/prd.md`
- `docs/test.md`
