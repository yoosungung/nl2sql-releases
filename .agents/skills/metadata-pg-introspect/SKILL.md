---
name: metadata-pg-introspect
description: >-
  Introspects PostgreSQL via MCP_POSTGRES_URL for MDL model authoring: schemas,
  tables, columns, foreign keys, FK cardinality, sample rows. Maps PG types to
  MDL physical types. Use when creating or editing *.model.json or
  *.relationship.json in nl2sql-metadata, or when the user mentions list_schemas,
  describe_table, discover_fks, or warehouse skills.
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
---

# metadata-pg-introspect

Postgres **실측** 전용. FK·join·`joinType`은 추측하지 말고 이 skill 출력만 근거로 쓴다.  
연결: repo 루트 `.env`의 `MCP_POSTGRES_URL`(없으면 환경 변수). URL은 로그·문서에 붙이지 않는다.

작성 절차·JSON 형태 → [MODEL_AUTHORING.md](../../../MODEL_AUTHORING.md). 같은 비즈니스 주제 테이블은 **한 model에 join 통합** 우선; `*.relationship.json`은 주제가 다른 model 간만.

## 실행

repo 루트에서:

```bash
.agents/skills/metadata-pg-introspect/scripts/pg-inspect.sh <cmd> [args...]
```

| cmd | args | skill 이름 |
|-----|------|------------|
| `schemas` | — | list_schemas |
| `tables` | `<schema>` | list_tables |
| `describe` | `<schema> <table>` | describe_table |
| `fks` | `<schema>` | discover_fks |
| `cardinality` | `<schema> <child_table> <fk_col> <parent_table> <parent_col>` | cardinality_check |
| `sample` | `<schema> <table> [limit]` | sample_rows (기본 limit=5) |

`psql`이 없으면 동일 SQL을 `psql "$MCP_POSTGRES_URL" -c "..."`로 직접 실행한다.

## MDL `type` 매핑 (physical)

| PostgreSQL (information_schema) | MDL |
|---------------------------------|-----|
| boolean | boolean |
| smallint, int2 | smallint |
| integer, int, int4 | int |
| bigint, int8 | bigint |
| real, float4 | float |
| double precision, float8 | double |
| numeric(p,s), decimal(p,s) | decimal(p,s) |
| text | text |
| character varying, varchar(n) | varchar |
| date | date |
| time without time zone | time |
| timestamp without time zone | timestamp |
| timestamp with time zone | timestamptz |
| interval | interval |
| bytea | bytes |
| json, jsonb | json |
| uuid | uuid |

애매하면 `varchar` 또는 `text`. 배열·composite는 v0에서 쓰지 않는다.

## cardinality → `joinType`

`cardinality` 출력의 `suggested_join_type`은 **child → parent** FK 기준:

- child 행마다 FK 값이 거의 유일 → 보통 `many_to_one` (child model `from`, parent model `to`)
- child 쪽 FK가 parent PK와 1:1 → `one_to_one`
- parent 한 행에 child 여러 행 → child에서 보면 `many_to_one`; parent model에서 child로 가면 `one_to_many`

relationship 파일의 `from`/`to` **model·column**은 `fks`·카디널리티 결과와 [MODEL_AUTHORING.md §4](../../../MODEL_AUTHORING.md)를 맞춘다(**주제 간**만).

## 출력 활용

1. `schemas` → 작업 스키마 `S`
2. `tables S` → 비즈니스 **주제** 후보(`product`, `sale`, …)·같은 주제에 넣을 `join` 후보
3. `describe S T` → `tableReference`, `columns[]`, `primaryKey`
4. `fks S` + 카디널리티 → (a) **같은 주제**면 model 내부 `join.on`, (b) **다른 주제**면 `S/*.relationship.json`
5. `cardinality …` → `joinType` (relationship용)
6. `sample S T` → `description` 보강 (선택)
