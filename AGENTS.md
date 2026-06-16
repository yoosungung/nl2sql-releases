# AGENTS.md

nl2sql **semantic metadata** git. 질의는 모델·뷰 이름(semantic SQL)만 쓰고, Postgres 실측은 `MCP_POSTGRES_URL`. 로컬 env: `cp .env.sample .env`.

## 문서

| 파일 | 용도 |
|------|------|
| [METADATA_LAYOUT.md](METADATA_LAYOUT.md) | 파일 kind 6종, 명명·폴더 규칙 |
| [MODEL_AUTHORING.md](MODEL_AUTHORING.md) | PG → model·relationship 작성 절차 (주제 통합 우선) |
| `.agents/skills/metadata-pg-introspect/` | Postgres 실측 skill + `pg-inspect.sh` |
| `.agents/skills/metadata-validate/` | backend API로 MDL 점검 skill + `validate-metadata.sh` |

한 문서 = 한 용도. 내용 겹치면 합치거나 한쪽만 링크.

## 모델링 (요약)

- 엔진은 질의에 따라 join을 **가감**할 수 있다 → **같은 비즈니스 주제는 한 `*.model.json`에 최대한 `tables[]`+`join`으로 통합**.
- `*.relationship.json`은 **주제가 다른 model** 사이만 (예: `sale` → `product`). 헤더·라인처럼 같은 주제 내부는 relationship으로 쪼개지 않는다.
- 상세·AdventureWorks 예시 → [MODEL_AUTHORING.md](MODEL_AUTHORING.md).

## 수행

1. 구조·신규 파일 → [METADATA_LAYOUT.md](METADATA_LAYOUT.md)
2. Postgres 실측 → skill `metadata-pg-introspect` (또는 `pg-inspect.sh`)
3. 모델·관계 → [MODEL_AUTHORING.md](MODEL_AUTHORING.md) (**통합 우선**, 테이블당 model 1개 금지 습관)
4. backend 검증 → skill `metadata-validate` — 수정 후 `draft <path>`, 전체는 `manifest` (**PUT으로 검증만 하지 않음**)
5. 질의는 `search_tables` → semantic SQL → `execute_select_query` (물리 테이블명 금지)

## Status

- 루트: `nl2sql.manifest.json`, `local_postgres.source.json`
- `adventureworks/`: model 11개 + relationship 9개 — PG `adventureworks` 13테이블 실측 기반 **초안**(헤더/라인 분리 등). 목표 주제는 `product`·`sale` 통합 등 → [MODEL_AUTHORING.md §6](MODEL_AUTHORING.md)
