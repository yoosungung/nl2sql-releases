# MODEL_AUTHORING.md

`MCP_POSTGRES_URL` Postgres에서 **`*.model.json`**, **`*.relationship.json`** 만드는 절차. 파일 규칙 → [METADATA_LAYOUT.md](METADATA_LAYOUT.md).

---

## 0. 전제 (OLAP·가변 join)

nl2sql 엔진은 질의에 따라 **join을 가감**할 수 있다(OLAP/시맨틱 레이어에 가깝다). metadata는 **물리 테이블 수·grain에 맞춰 쪼개기보다, 같은 비즈니스 주제 안에서는 최대한 한 `*.model.json`에 `tables[]` + inner/left `join`으로 모으는 것**을 기본으로 한다.

- **모델 수를 줄인다** → `search_tables`·엔티티 선택이 단순해지고, 헤더·라인·위성(satellite) 속성을 한 주제에서 dotted path 없이 쓸 수 있다.
- **`*.relationship.json`** 은 **주제가 다른 엔티티** 사이(예: `sale` ↔ `customer`, `sale` ↔ `product`) 또는 junction을 **독립 주제**로 둘 때만 쓴다. 같은 주제 안의 FK는 우선 **model 내부 `join`**.
- grain(헤더 vs 라인) 차이는 **모델을 나누는 주된 이유가 아니다**. 라인 grain이 필요하면 PK·질의 예시로 맞추고, 헤더 컬럼은 join으로 함께 노출한다.

---

## 1. 사전 조사 (skills)

Cursor skill **`metadata-pg-introspect`** (`.agents/skills/metadata-pg-introspect/`) — 모델 작성 전에 호출한다.

| 절차 | 스크립트 |
|------|----------|
| list_schemas | `pg-inspect.sh schemas` |
| list_tables | `pg-inspect.sh tables <S>` |
| describe_table | `pg-inspect.sh describe <S> <table>` |
| discover_fks | `pg-inspect.sh fks <S>` |
| cardinality_check | `pg-inspect.sh cardinality <S> <child> <fk_col> <parent> <parent_col>` |
| sample_rows | `pg-inspect.sh sample <S> <table> [n]` |

```bash
.agents/skills/metadata-pg-introspect/scripts/pg-inspect.sh schemas
.agents/skills/metadata-pg-introspect/scripts/pg-inspect.sh describe adventureworks product
```

FK·inner `join.on`·`joinType`은 skill 출력만 근거로 쓴다( formal FK가 없으면 컬럼명·카디널리티 실측). PG→MDL `type` 매핑은 skill 본문 표를 따른다.

---

## 2. 작성 절차 (스키마 `S` 단위)

### 모델 설계 원칙 (시맨틱 주제)

1. 스키마 `S`에서 **비즈니스 주제** 후보를 적는다(예: `product`, `sale`, `customer` — PG 테이블명과 1:1일 필요 없음).
2. **같은 주제**에 속하는 물리 테이블은 한 `S/<주제>.model.json`에 `tables[]` + `join`으로 **우선 통합**한다.
   - 예: `salesorderheader` + `salesorderdetail` → `sale`
   - 예: `product` + `productsubcategory` + `productcategory` → `product`
   - 예: 같은 제품 도메인의 `productreview`, junction(`productmodelproductdescriptionculture`) + `productdescription` → 통합 후보(카디널리티·질의 패턴 확인)
3. **다른 주제**만 별도 model + `*.relationship.json` (dotted path: `sale.product.name`).
4. **m:n:** relationship 한 줄로 우회하지 않는다. junction은 (a) **한 주제 model에 join**으로 넣거나, (b) junction 자체가 독립 질의 주제일 때만 별도 model + relationship 두 개.

### 통합 vs 분리 (결정 요약)

| 상황 | 기본 |
|------|------|
| 헤더 + 라인, 마스터 + 1:1·N:1 위성 | **한 model**, inner/left `join` |
| 차원/참조(`customer`, `product` 카탈로그)를 판매 주제에서 참조 | **relationship** (`sale` → `product`) |
| junction이 **그 주제의 속성** (모델-설명-문화권) | **해당 주제 model에 join** 우선 |
| junction·엔티티가 **질의 주제 자체** (할당량 이력만 조회) | 별도 model 허용 |

### 절차

1. 주제별로 물리 테이블·`join` 그래프를 적는다.
2. 주제마다 `describe_table` → `S/<주제>.model.json` (`tables[]`, `columns[]`, `primaryKey`).
3. **주제 간** 연결만 `S/<name>.relationship.json` + from model의 `kind: relation`.
4. relation **대상** model에 `primaryKey` 필수.
5. semantic SQL 스모크 — 예: `SELECT sales_order_id, order_date, line_amount FROM sale LIMIT 5`.

**이름·설명:** stem = 주제명 (`product`, `sale`). `description` = 그 주제가 무엇인지 한 문장. `tableReference.schema` = `S`.

---

## 3. `*.model.json`

공통: `source` = `local_postgres`(또는 해당 `*.source.json`의 `name`). inner table 중 **`join` 없는 것 1개** = 마스터(보통 grain의 기준 테이블). `from` = `"alias.column"` (alias는 밖에 안 나감).

### 3.1 주제 통합 (여러 물리 테이블 → 한 model) — **기본 패턴**

`orders` + `order_lines` → **`sale`** 한 파일.

```json
{
  "name": "sale",
  "source": "local_postgres",
  "description": "판매 주제. 주문 헤더·라인을 join으로 구성.",
  "tables": [
    {
      "alias": "hdr",
      "priority": 1,
      "tableReference": { "schema": "S", "table": "orders" }
    },
    {
      "alias": "ln",
      "priority": 2,
      "tableReference": { "schema": "S", "table": "order_lines" },
      "join": {
        "to": "hdr",
        "type": "left",
        "on": [{ "left": "order_id", "right": "id" }]
      }
    }
  ],
  "primaryKey": "sales_order_detail_id",
  "columns": [
    {
      "name": "sales_order_detail_id",
      "kind": "physical",
      "type": "bigint",
      "from": "ln.id",
      "notNull": true,
      "description": "라인 grain PK"
    },
    {
      "name": "sales_order_id",
      "kind": "physical",
      "type": "bigint",
      "from": "hdr.id",
      "notNull": true
    },
    {
      "name": "order_date",
      "kind": "physical",
      "type": "date",
      "from": "hdr.order_date"
    },
    {
      "name": "line_amount",
      "kind": "physical",
      "type": "decimal(18,2)",
      "from": "ln.amount"
    }
  ]
}
```

- join 그래프: 비순환·연결.
- **PK**는 주제에서 가장 흔한 질의 grain(보통 라인 ID). 헤더만 집계하는 질의는 엔진이 join을 조정한다.
- 같은 이름 컬럼이 여러 inner table에 있으면 `"from": ["hdr.id", "ln.id"]` → `COALESCE` 순서는 **배열 순서**.

### 3.2 단일 물리 테이블만 있는 주제 (최소 예시)

테이블 하나로 주제가 **이미 닫혀 있을 때**의 시작점이다. “테이블 1개 = 무조건 별도 model”이 **아니다** — 같은 주제의 다른 테이블이 있으면 §3.1로 합친다.

```json
{
  "name": "customer",
  "source": "local_postgres",
  "description": "고객 주제.",
  "tables": [
    {
      "alias": "m",
      "priority": 1,
      "tableReference": { "schema": "S", "table": "customers" }
    }
  ],
  "primaryKey": "id",
  "columns": [
    { "name": "id", "kind": "physical", "type": "bigint", "from": "m.id", "notNull": true },
    { "name": "name", "kind": "physical", "type": "text", "from": "m.name" }
  ]
}
```

`customer_addresses` 등이 **같은 `customer` 주제**면 같은 model에 `join` 추가. **다른 주제**(예: `address`를 전사 주소록으로만 쓸 때)면 model을 나누고 relationship.

### 3.3 계산 컬럼 (선택)

`expression`은 **노출된 model 컬럼명**만 (inner alias 금지).

```json
{ "name": "amount_usd", "kind": "calculated", "type": "double", "expression": "amount / 1300.0" }
```

---

## 4. `*.relationship.json`

**주제 간** 연결에만 사용한다. 같은 `sale` model 안의 헤더↔라인은 §3.1 `join`으로 처리하고 relationship 파일을 만들지 않는다.

**1) 관계 파일** `S/sale_to_customer.relationship.json`

```json
{
  "name": "sale_to_customer",
  "joinType": "many_to_one",
  "from": { "model": "sale", "column": "customer_id" },
  "to": { "model": "customer", "column": "id" },
  "description": "판매 N건 → 고객 1명"
}
```

- `joinType`: **from → to** 방향 cardinality (`one_to_one` | `one_to_many` | `many_to_one`).
- `name` = relation 컬럼의 `via`와 **동일**.

**2) from model** (`sale.model.json`)에 relation 컬럼

```json
{
  "name": "customer",
  "kind": "relation",
  "to": "customer",
  "via": "sale_to_customer",
  "description": "dotted path: sale.customer.name"
}
```

---

## 5. 검증

| 항목 | 확인 |
|------|------|
| 구조 | `source` 일치, `via` = relationship `name`, join `to`/alias, 대상 model `primaryKey`, `type` vocabulary |
| 통합 | 같은 주제 테이블이 불필요하게 쪼개지지 않았는지(헤더·라인·분류 위성 등) |
| 의미 | FK·카디널리티 skill 재확인 |
| 질의 | `search_tables`에 주제 model이 보이는지, semantic SQL 스모크 |

흔한 오류: 주제 내부를 relationship으로만 연결, `join.on` left/right 뒤바뀜, `via` 오타, calculated에 `m.col` 사용, relation 대상에 PK 없음.

---

## 6. 예: AdventureWorks (`adventureworks` 스키마)

PG 13테이블 기준 **권장 주제** (실측·리팩터 시 목표):

| 주제 model | 통합 후보 (inner/left join) | relationship으로 빼는 쪽 |
|------------|----------------------------|---------------------------|
| `product` | `product`, `productsubcategory`, `productcategory`, `productreview`, `productdescription`, junction `productmodelproductdescriptionculture` | (다른 스키마 주제가 생기면) |
| `sale` | `salesorderheader`, `salesorderdetail` | `product` (`product_id`), `salesperson`, `sales_territory`, `currency_rate` 등 **참조 차원** |
| (선택) `salesperson`, `sales_territory`, … | 할당량 이력·지역만 **단독 질의**가 많으면 유지 | `sale`에서 dotted path |

