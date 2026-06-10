# Wiki Schema

## Domain
이 위키는 **LLM을 활용한 Python 기반 RAG 시스템**을 다룹니다. 현재는 SDK 형태로 제공되며, 추후 **API**, **MCP**, 기타 인터페이스를 연결해 재사용 가능한 지식 베이스와 구현 문서를 축적하는 것을 목표로 합니다.

포함 범위:
- RAG 아키텍처와 설계 결정
- Python SDK 구조, 모듈, 인터페이스
- API / MCP 연동 방식
- 임베딩, 검색, 인덱싱, 청킹, 평가, 운영 이슈
- 외부 문서/논문/실험 결과의 축적 및 교차참조

제외 범위:
- 도메인과 무관한 일반 Python 문법
- 일회성 잡무나 휘발성 메모
- raw/에 없는 주장의 무근거 확정 서술

## Conventions
- File names: lowercase, hyphens, no spaces (e.g., `retrieval-pipeline.md`)
- Every wiki page starts with YAML frontmatter
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- When updating a page, always bump the `updated` date
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`
- On pages synthesizing 3+ sources, append provenance markers like `^[raw/articles/source-file.md]` at paragraph ends when specific claims should be traceable
- Prefer concise, implementation-oriented writing: architecture, constraints, trade-offs, interfaces, failure modes, open questions
- Use English slugs/file names even when body text includes Korean

## Frontmatter
```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [from taxonomy below]
sources: [raw/articles/source-name.md]
confidence: high | medium | low
contested: true
contradictions: [other-page-slug]
---
```

Notes:
- `confidence`, `contested`, and `contradictions` are optional but recommended for evolving implementation guidance or conflicting source material.
- `sources` should list raw source files whenever the page depends on imported material.
- For project-internal knowledge derived from code/docs inspection, cite the inspected file path in prose and keep `confidence` at `medium` unless corroborated.

## raw/ Frontmatter
```yaml
---
source_url: https://example.com/article
ingested: YYYY-MM-DD
sha256: <hex digest of the raw content below the frontmatter>
---
```

The sha256 is computed over the body only, not the frontmatter.

## Tag Taxonomy
Architecture / system
- rag
- architecture
- pipeline
- retrieval
- indexing
- ingestion
- chunking
- embeddings
- reranking
- vector-store

Interfaces / product
- sdk
- api
- mcp
- cli
- integration

Implementation
- python
- config
- schema
- evaluation
- testing
- performance
- observability
- deployment

Knowledge / governance
- source
- decision
- comparison
- issue
- roadmap
- security

Rule: every tag on a page must appear in this taxonomy. If a new tag is needed, add it here first.

## Page Thresholds
- **Create a page** when an entity/concept appears in 2+ sources OR is central to one source
- **Add to existing page** when a source mentions something already covered
- **DON'T create a page** for passing mentions, trivial helper functions, or out-of-scope details
- **Split a page** when it exceeds ~200 lines
- **Archive a page** when fully superseded by newer architecture or interface docs

## Entity Pages
Use for notable system components, libraries, services, interfaces, or organizations. Include:
- What it is
- Role in the RAG system
- Key interfaces and dependencies
- Related pages via [[wikilinks]]
- Sources and evidence

## Concept Pages
Use for core topics such as retrieval strategy, chunking policy, embedding model selection, API design, or MCP transport. Include:
- Definition
- Current implementation / intended design
- Trade-offs
- Failure modes / open questions
- Related concepts via [[wikilinks]]

## Comparison Pages
Use for alternatives such as vector store choices, embedding models, SDK vs API interfaces, or MCP vs direct adapters. Include:
- Scope of comparison
- Dimensions (table preferred)
- Recommendation or synthesis
- Sources

## Query Pages
Use for substantial answers worth preserving, such as architecture deep dives, integration plans, or design rationale recovered from multiple pages/sources.

## Update Policy
When new information conflicts with existing content:
1. Check timestamps and source authority
2. If newer source supersedes older content, preserve the older claim briefly and note the change
3. If genuinely contradictory, document both positions with dates and sources
4. Mark frontmatter with `contested: true` and `contradictions: [page-name]` where appropriate
5. Surface the issue in lint output for review
