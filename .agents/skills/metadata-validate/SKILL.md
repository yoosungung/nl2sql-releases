---
name: metadata-validate
description: >-
  Validates MDL metadata via POST /api/metadata/fs/validate before git commit.
  Use after editing *.model.json or *.relationship.json, before PUT/save, or
  when the user asks to validate metadata. Never use PUT only to check validity.
allowed-tools:
  - Bash
  - Read
  - Grep
  - Glob
---

# metadata-validate

**반드시** `POST /api/metadata/fs/validate`로 점검한다. `PUT /api/metadata/fs/{path}`로 검증만 시도하지 않는다(통과 시 noop commit·push·sync가 돈다).

| API | 용도 |
|-----|------|
| `POST …/validate` | commit **전** preflight — `{ ok, issues }`, 항상 HTTP 200 |
| `PUT …/fs/{path}` | 검증 통과 **후** 저장 (`base_sha` + `body`) |

규칙 → [METADATA_LAYOUT.md](../../../METADATA_LAYOUT.md). API 계약 → [ARCHITECTURE.md §5.2 validate](../../../../ARCHITECTURE.md#validate-post-fsvalidate).

## 사전 조건

1. metadata repo 루트에서 실행(또는 `METADATA_REPO_ROOT` / `METADATA_REPO_PATH`가 그 경로).
2. backend 실행 — `NL2SQL_BACKEND_URL`(기본 `http://127.0.0.1:8080`), `.env`의 `METADATA_REPO_PATH`와 동일 tree.
3. 인증 — `X-Forwarded-User` + `X-Forwarded-Email`(스크립트 기본 `validator` / `validator@local`).

## 실행 (이 skill의 유일한 검증 경로)

metadata **repo 루트**에서:

```bash
.agents/skills/metadata-validate/scripts/validate-metadata.sh <subcommand> ...
```

| subcommand | 인자 | API body |
|------------|------|----------|
| `manifest` | — | `{ "scope": "repo" }` |
| `file` | `<repo-relative-path>` | `{ "path" }` — HEAD 내용 |
| `draft` | `<path> [source.json]` | `{ "path", "body" }` — **commit 전** |
| `delete` | `<path>` | `{ "path", "delete": true }` |
| `delete-plan` | `<path>` | delete-plan → `{ "paths", "delete": true }` |

`draft`에서 `source` 생략 시 → repo 루트의 `<path>` 파일을 body로 읽는다(방금 저장한 파일 점검).

공통 옵션: `--json` — `{ "label", "http_status", "result": { "ok", "issues" } }` 출력.

종료 코드: **0** = `ok: true`, **1** = issues 있음 또는 HTTP 오류.

### Agent 워크플로 (필수)

1. `*.model.json` / `*.relationship.json` 수정을 **디스크에 쓴 뒤** (아직 commit 안 해도 됨):
   ```bash
   .agents/skills/metadata-validate/scripts/validate-metadata.sh draft adventureworks/sale.model.json
   ```
2. `ok: true`가 아니면 `issues`의 `code`·`path`·`message`로 수정 후 1번 반복.
3. 저장이 필요하면 콘솔/API **`PUT`** (`base_sha` + `body`) — validate는 저장하지 않음.
4. 여러 파일·관계 수정 후 repo 전체:
   ```bash
   .agents/skills/metadata-validate/scripts/validate-metadata.sh manifest
   ```
5. 파일 삭제 예정:
   ```bash
   .agents/skills/metadata-validate/scripts/validate-metadata.sh delete-plan customers.model.json
   ```

편집 중 내용이 repo 파일과 다르면 `draft path /tmp/edited.json`으로 명시.

## 수동 curl (스크립트 없을 때)

```bash
curl -s -X POST -H 'Content-Type: application/json' \
  -H 'X-Forwarded-User: validator' -H 'X-Forwarded-Email: validator@local' \
  -d '{"path":"adventureworks/sale.model.json","body":{"name":"sale",...}}' \
  http://127.0.0.1:8080/api/metadata/fs/validate
```

## issue 코드

| code | 조치 |
|------|------|
| `schema_violation` | [mdl.schema.json](../../../../schemas/mdl.schema.json) 대조 |
| `duplicate_entity` | `name` 전역 유일 — 다른 폴더와 충돌 시 prefix·rename |
| `unknown_source` / `unknown_relationship` / `unknown_model` / `unknown_column` | cross-ref·컬럼·통합 model 점검 |
| `invalid_primary_key` / `missing_primary_key` | physical PK vs calculated |

## pg-introspect와 분리

| skill | 시점 |
|-------|------|
| [metadata-pg-introspect](../metadata-pg-introspect/SKILL.md) | 작성 **전** PG 실측 |
| **metadata-validate** | 작성 **후**, commit/PUT **전** |
