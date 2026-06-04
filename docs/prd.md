# DocMesh RAG Core Service PRD

## 1. 문서 개요

- **문서명:** Product Requirements Document (PRD)
- **대상 제품:** DocMesh RAG Core Service
- **문서 목적:** 문서 기반 질의응답을 수행하는 RAG 코어 서비스의 제품 요구사항을 정의하고, MVP 범위와 향후 확장 방향을 명확히 한다.
- **문서 상태:** Draft

---

## 2. 제품 배경

DocMesh 프로젝트는 문서를 적재하고, 문서에서 관련 정보를 검색한 뒤, LLM을 통해 답변을 생성하는 RAG(Retrieval-Augmented Generation) 시스템을 필요로 한다. 초기 단계에서는 빠른 검증과 구현 속도를 위해 **단일 클래스 기반의 코어 서비스**로 시작하되, 이후 API 서버 및 MSA 구조로 확장 가능한 설계를 목표로 한다.

또한 본 서비스는 단일 사용자 환경을 넘어 **멀티 유저 환경**을 고려해야 하며, 각 사용자의 문서와 검색 결과가 서로 섞이지 않도록 **명확한 데이터 격리**를 보장해야 한다.

---

## 3. 제품 목표

### 3.1 핵심 목표

1. 개인 및 멀티 유저를 지원하는 RAG 코어를 구축한다.
2. 문서 기반 질의응답 기능을 제공한다.
3. 로컬 환경의 Ollama를 활용해 임베딩 및 생성 기능을 제공한다.
4. MVP는 단순하게 시작하되, 이후 API/비동기/MSA 구조로 확장 가능한 기반을 마련한다.

### 3.2 성공 기준

- 사용자는 자신의 문서를 업로드하거나 텍스트로 입력할 수 있다.
- 사용자는 자신의 문서만 대상으로 질의응답을 수행할 수 있다.
- 시스템은 문서 적재, 벡터 검색, 답변 생성을 하나의 일관된 흐름으로 수행할 수 있다.
- 초기 구현이 단일 프로세스 구조이더라도, 기능별 서비스 분리가 가능한 구조를 유지한다.

---

## 4. 범위 정의

### 4.1 포함 범위 (In Scope)

- Knowledge Ingestion (문서 적재)
- 문서 전처리 및 청킹
- Ollama 기반 임베딩 생성
- Vector DB 기반 검색
- LLM 기반 답변 생성
- token 기반 사용자 식별
- user_id 기반 멀티 유저 데이터 격리
- 메타데이터 저장 및 최소 수준의 persistence 보장

### 4.2 제외 범위 (Out of Scope)

초기 MVP에서는 아래 항목을 제외한다.

- 외부 공개용 API 서버
- UI / Frontend
- 대규모 분산 아키텍처(MSA) 운영 환경
- 고급 캐싱
- 고급 reranking
- 복잡한 권한 체계 및 조직 단위 멀티테넌시

---

## 5. 주요 사용자 및 사용 시나리오

### 5.1 주요 사용자

1. **개인 사용자**
   - 자신의 문서를 적재하고 질의응답을 수행하려는 사용자
2. **멀티 유저 환경의 애플리케이션/서비스**
   - 여러 사용자의 문서를 분리 저장하고, 사용자별 RAG 응답을 제공하려는 상위 시스템

### 5.2 핵심 사용 시나리오

#### 시나리오 1: 문서 적재
- 사용자는 파일 또는 문자열 형태로 문서를 입력한다.
- 시스템은 문서를 로드, 전처리, 청킹, 임베딩한 뒤 벡터 저장소와 메타데이터 저장소에 기록한다.

#### 시나리오 2: 사용자별 질의응답
- 사용자는 token을 통해 식별된다.
- 시스템은 token을 user_id로 매핑한다.
- 시스템은 user_id에 해당하는 문서만 검색 대상으로 삼아 관련 컨텍스트를 수집한다.
- 시스템은 수집한 컨텍스트를 기반으로 답변을 생성한다.

#### 시나리오 3: 재시작 이후 메타데이터 유지
- 프로세스가 재시작되더라도 최소한 문서 메타데이터는 유지되어야 한다.
- 이를 통해 이후 저장소 재구성 또는 운영 추적이 가능해야 한다.

---

## 6. 제품 요구사항

### 6.1 사용자 관리 요구사항

#### PRD-FR-1. 사용자 식별
- 시스템은 token 기반으로 사용자를 식별해야 한다.
- 시스템은 token과 user_id 간 매핑을 관리할 수 있어야 한다.

#### PRD-FR-2. 멀티 유저 지원
- 시스템은 사용자별 데이터 격리를 지원해야 한다.
- 모든 문서 메타데이터에는 user_id가 필수로 포함되어야 한다.
- 검색 시 user_id 기반 필터링이 반드시 적용되어야 한다.

### 6.2 문서 관리 요구사항

#### PRD-FR-3. 문서 입력
- 시스템은 텍스트 기반 문서 입력을 지원해야 한다.
- 입력 방식은 최소 다음 두 가지를 지원해야 한다.
  - 파일 입력
  - 문자열 입력

#### PRD-FR-4. 문서 저장
- 시스템은 문서를 처리 과정에서 사용할 저장 방식을 선택 가능해야 한다.
- MVP 기준 지원 옵션:
  - In-memory 저장
  - Local file storage

#### PRD-FR-5. 문서 메타데이터 관리
- 시스템은 문서별 메타데이터를 저장해야 한다.
- 최소 메타데이터 스키마는 아래 정보를 포함해야 한다.

```json
{
  "doc_id": "uuid",
  "user_id": "string",
  "source": "file_name",
  "created_at": "timestamp"
}
```

### 6.3 Knowledge Ingestion 요구사항

#### PRD-FR-6. 문서 처리 파이프라인
시스템은 아래 순서의 문서 처리 파이프라인을 제공해야 한다.

1. Load
2. Preprocess
3. Chunking
4. Embedding
5. Vector Store 저장

#### PRD-FR-7. Chunking
- 시스템은 문서를 청크 단위로 분할할 수 있어야 한다.
- 최소 지원 방식:
  - 고정 길이 청킹
  - semantic chunking 확장 가능 구조
- 청크 간 overlap 설정을 지원해야 한다.

### 6.4 Embedding 요구사항

#### PRD-FR-8. 임베딩 생성
- 시스템은 Ollama 기반 embedding 모델을 사용해야 한다.
- 성능 최적화를 위해 batch 처리를 지원해야 한다.

#### PRD-FR-9. 임베딩 서비스 분리
- 시스템은 embedding 처리와 LLM inference를 논리적으로 분리해야 한다.
- embedding client/instance는 generation용 client/instance와 분리 가능해야 한다.

### 6.5 Vector Storage 요구사항

#### PRD-FR-10. 벡터 저장소
- 시스템은 Milvus 또는 lightweight vector DB를 사용할 수 있어야 한다.
- MVP에서는 구현 단순성과 확장성을 함께 고려한 저장소 선택이 가능해야 한다.

#### PRD-FR-11. 멀티테넌트 구조
- 사용자 데이터 분리를 위한 벡터 저장 전략이 필요하다.
- 고려 가능한 전략:
  - collection per user (**MVP 권장**)
  - partition per user
  - metadata filter

### 6.6 Retrieval 요구사항

#### PRD-FR-12. 유사도 검색
- 시스템은 질의에 대한 embedding을 생성해야 한다.
- 시스템은 top-k 기반 유사도 검색을 수행해야 한다.

#### PRD-FR-13. 사용자 필터링
- 검색 결과는 반드시 user_id 기준으로 필터링되어야 한다.
- 다른 사용자 데이터가 검색 결과에 포함되어서는 안 된다.

### 6.7 Generation 요구사항

#### PRD-FR-14. 프롬프트 생성
시스템은 아래 요소를 조합해 프롬프트를 구성해야 한다.

```text
[System Prompt]
[User Query]
[Retrieved Context]
```

#### PRD-FR-15. 답변 생성
- 시스템은 Ollama 기반 LLM inference를 통해 응답을 생성해야 한다.
- 응답은 검색된 컨텍스트를 기반으로 생성되어야 한다.

---

## 7. 비기능 요구사항

### 7.1 성능

- embedding은 batch 처리로 최적화되어야 한다.
- retrieval latency는 가능한 낮게 유지되어야 한다.
- LLM 응답 지연 시간은 운영 가능한 수준으로 관리되어야 한다.

### 7.2 확장성

- 초기 구현은 단일 클래스 구조로 시작하되, 서비스 단위 분리가 가능해야 한다.
- 향후 FastAPI 기반 API 서버 또는 MSA로 확장 가능한 구조여야 한다.

### 7.3 데이터 격리

- 사용자 데이터는 절대 혼합되어서는 안 된다.
- 저장, 검색, 응답 생성 전 과정에서 user_id 스코프가 일관되게 유지되어야 한다.

### 7.4 안정성

- 최소한의 persistence를 보장해야 한다.
- 프로세스 재시작 이후에도 메타데이터는 유지되어야 한다.

### 7.5 유지보수성

- ingestion, retrieval, generation 책임은 구조적으로 분리되어야 한다.
- 향후 독립 서비스로 분리 가능한 수준의 모듈화가 필요하다.

---

## 8. 시스템 아키텍처 개요

```text
[RAG Core Class]
 ├ Ingestion
 ├ Retrieval
 └ Generation

[Storage]
 ├ Vector DB (Milvus or lightweight)
 ├ Metadata DB (MySQL)
 └ Document Storage (Memory or Local)

[Model]
 ├ Embedding (Ollama)
 └ LLM (Ollama)
```

### 8.1 설계 원칙

- 외부 인터페이스는 단순하게 유지한다.
- 내부 구현은 ingestion / retrieval / generation 책임별로 분리한다.
- MVP에서는 단일 클래스 진입점을 제공하되, 실제 내부는 서비스 객체 단위로 나눈다.

### 8.2 코어 인터페이스 예시

```python
class RAGCore:
    def __init__(self):
        self.ingestor = IngestionService()
        self.retriever = RetrievalService()
        self.generator = GenerationService()

    def ingest(self, user_id, document):
        return self.ingestor.process(user_id, document)

    def query(self, user_id, question):
        context = self.retriever.search(user_id, question)
        return self.generator.generate(question, context)
```

---

## 9. 세부 서비스 책임

### 9.1 IngestionService
책임:
- 문서 로드
- 전처리
- 청킹
- 임베딩 생성 요청
- 벡터 저장소 적재
- 문서/청크 메타데이터 기록

예시 메서드:

```python
load()
preprocess()
chunk()
embed()
store()
```

### 9.2 RetrievalService
책임:
- 질의 임베딩 생성
- 벡터 검색 수행
- 사용자 범위 필터 적용
- 상위 k개 컨텍스트 반환

예시 메서드:

```python
embed_query()
vector_search()
filter_by_user()
```

### 9.3 GenerationService
책임:
- 프롬프트 구성
- 컨텍스트 기반 답변 생성

예시 메서드:

```python
build_prompt()
call_llm()
```

---

## 10. 데이터 모델 요구사항

### 10.1 documents

필수 필드:

```text
doc_id (PK)
user_id
source
created_at
```

### 10.2 chunks

필수 필드:

```text
chunk_id
doc_id
content
metadata
```

### 10.3 pipelines

필수 필드:

```text
pipeline_id
status
created_at
```

---

## 11. 제약사항 및 리스크

### R1. Ollama 리소스 경쟁
- embedding과 generation이 동일 리소스를 과도하게 점유할 수 있다.
- 대응 방향: embedding/LLM 실행 경로 분리, 클라이언트 분리, 배치 전략 적용

### R2. 멀티 유저 데이터 혼합
- 사용자 필터링이 누락되면 심각한 데이터 혼합 문제가 발생할 수 있다.
- 대응 방향: user_id 필터를 저장 및 검색 계층 모두에서 강제

### R3. In-memory 데이터 손실
- 메모리 기반 저장만 사용할 경우 재시작 시 데이터 유실 위험이 있다.
- 대응 방향: 최소 metadata는 RDB에 저장

### R4. 단일 클래스 구조의 확장 한계
- 초기 구현이 지나치게 결합되면 이후 분리가 어려워질 수 있다.
- 대응 방향: 초기부터 서비스 책임 분리 및 인터페이스 명확화

---

## 12. 릴리스 범위 정의

### 12.1 MVP 릴리스 범위
- 단일 클래스 기반 RAGCore 제공
- 파일/문자열 문서 입력
- 기본 전처리 및 청킹
- Ollama embedding
- Milvus 또는 lightweight vector DB 저장/검색
- 사용자별 질의응답
- MySQL 기반 메타데이터 저장

### 12.2 이후 확장 로드맵

#### Phase 1
- 단일 클래스 기반 RAG MVP

#### Phase 2
- FastAPI 기반 API 서비스 제공
- Async 처리 도입

#### Phase 3
- MSA 전환
  - ingestion-service
  - retrieval-service
  - generation-service

#### Phase 4
- Multi-tenant scaling
- caching
- reranking

---

## 13. 수용 기준 (Acceptance Criteria)

1. 사용자 token을 통해 user_id를 식별할 수 있다.
2. 문서를 파일 또는 문자열 형태로 입력받아 적재할 수 있다.
3. 적재된 문서는 청킹 및 임베딩 과정을 거쳐 벡터 저장소에 저장된다.
4. 문서 메타데이터에는 doc_id, user_id, source, created_at이 포함된다.
5. 질의 시 query embedding을 생성하고 top-k 검색을 수행할 수 있다.
6. 검색 결과는 반드시 해당 user_id 범위로 제한된다.
7. 시스템은 검색된 컨텍스트를 포함한 프롬프트로 LLM 응답을 생성할 수 있다.
8. 프로세스 재시작 이후에도 최소 메타데이터는 유지된다.
9. 내부 구조는 ingestion / retrieval / generation 단위로 분리되어 있어 향후 서비스화가 가능하다.

---

## 14. 요약

DocMesh RAG Core Service는 문서 적재, 검색, 생성의 전 과정을 담당하는 RAG 핵심 모듈이다. MVP에서는 단일 클래스 기반으로 빠르게 구현하되, 멀티 유저 데이터 격리와 확장 가능한 구조를 핵심 원칙으로 삼는다. 본 PRD는 해당 서비스의 기능 범위, 비기능 요구사항, 아키텍처 방향, 리스크, 수용 기준을 정의한다.
