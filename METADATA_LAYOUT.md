# METADATA_LAYOUT.md

이 repo에 둘 수 있는 **metadata 파일** 규칙과 권장 폴더 구조.

## 파일 kind (6종)

이름: `…<stem>.<kind>.json` — kind는 **끝에서 두 번째 segment**(예: `customers.v2.model.json` → `model`).

| ext | 개수 | 용도 |
|-----|------|------|
| `*.manifest.json` | 루트 **1개** | `catalog`, `schema` (semantic 네임스페이스) |
| `*.source.json` | N | 워크하우스 연결 (`connectionRef`) |
| `*.model.json` | N | 시맨틱 **주제** 1개 (`product`, `sale`, …). 같은 주제의 여러 물리 테이블은 **한 model**에 `tables[]`+`join`으로 통합(기본) |
| `*.relationship.json` | N | **주제가 다른** model 간 FK·카디널리티 (`via`). 같은 주제 내부 join은 model에만 둠 |
| `*.view.json` | N | semantic SQL 스니펫(재사용 질의) |
| `*.policy.json` | N | 모델별 행 필터·컬럼 마스크 |

위 kind가 아닌 `*.json`은 metadata로 쓰지 않는다. `README.md` 등 일반 파일은 자유.

## 작성 규칙

- 자격증명은 넣지 않는다 → `connectionRef: "env:MCP_POSTGRES_URL"` 등 참조만.
- 같은 kind 안에서 본문 `name`은 **전역 유일**.
- 새 파일은 보통 **stem = `name`**.
- 폴더 위치는 자유(정리용). **PG 스키마 이름**으로 디렉터리를 두고, 그 안에 `*.model.json`과 `*.relationship.json`을 **같이** 둔다.
- **model 개수:** PG 테이블 수와 맞출 필요 없음. 주제 단위로 적을수록 좋다 → [MODEL_AUTHORING.md §0](MODEL_AUTHORING.md).

## 권장 트리

```
nl2sql.manifest.json
local_postgres.source.json
<postgres_schema>/          # 예: adventureworks — PG 스키마명과 동일하게
  <topic>.model.json        # 예: product.model.json, sale.model.json
  <name>.relationship.json  # 주제 간만
views/
  <name>.view.json
policies/
  <name>.policy.json
```

`model`·`relationship` 작성 절차 → [MODEL_AUTHORING.md](MODEL_AUTHORING.md). `view`·`policy`는 kind 표 참고, 본문은 manifest `$schema` 기준.
