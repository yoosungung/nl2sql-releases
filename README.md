# nl2sql

자연어 질문을 의미 계층(MDL) 기반 SQL로 변환해 워크하우스에서 실행하고 결과를 시각화하는 시스템. 세 컴포넌트:

- [`frontend/`](frontend/) — Vite + React SPA (채팅 UI + 메타데이터 콘솔)
- [`backend/`](backend/) — FastAPI + deepagents. canonical metadata git repo 보유, agent 실행, MCP 호출.
- [`mcp/`](mcp/) — Rust + DataFusion. semantic SQL → warehouse SQL 재작성기.

문서 안내:

- 시스템 규칙·계약 + 컴포넌트 간 인터페이스 형태: [ARCHITECTURE.md](ARCHITECTURE.md) (§1 계약 / §2 이후 형태)
- 수행 계획: [ROADMAP.md](ROADMAP.md)
- 컴포넌트 내부 설계: [backend/DESIGN.md](backend/DESIGN.md)(공통), [backend/src/nl2sql_backend/DESIGN.md](backend/src/nl2sql_backend/DESIGN.md), [frontend/DESIGN.md](frontend/DESIGN.md), [mcp/DESIGN.md](mcp/DESIGN.md)
- k8s 사전 의존성 + dev→운영 컷오버: [deploy/dependencies.md](deploy/dependencies.md)
- k8s 설치·Secret·PVC: [deploy/SETUP.md](deploy/SETUP.md), 매니페스트 베이스 [deploy/k8s/base/](deploy/k8s/base/)
- PR/push CI: [.github/workflows/ci.yml](.github/workflows/ci.yml)
- 공개 README·바이너리 릴리스: [yoosungung/nl2sql-releases](https://github.com/yoosungung/nl2sql-releases) (private `nl2sql`에서 Actions로 미러)

운영 통합 이미지 빌드는 [backend/DESIGN.md ## Commands](backend/DESIGN.md#commands)·[mcp/DESIGN.md Commands](mcp/DESIGN.md#commands)를 본다.

---

## Quickstart — Phase 1 로컬 데모

세 컴포넌트(`mcp`, `backend`, `frontend`) + DuckDB 한 파일로 돌아간다. 외부 클러스터 없이 한 노트북에서 시연 가능한 최소 셋업.

### 사전 조건

| 도구 | 버전 |
|---|---|
| Rust toolchain | stable (mcp 빌드용) |
| Python | 3.11+ (backend) |
| `uv` | 0.9+ (Python pkg/venv) |
| Node | 20+ |
| npm | 10+ |
| DuckDB CLI | 1.1+ (DuckDB 데모용, 선택) |

LLM API 키 (`ANTHROPIC_API_KEY`) 1개 — `agent.builder.build_agent`가 이걸 보고 모델 핸들을 만든다. 미설정이면 `/chat`이 503을 반환한다.

### 1. metadata 샘플 repo 초기화

[`deploy/sample-metadata/`](deploy/sample-metadata/)는 손작성 MDL 매니페스트(customers / products / orders 3 모델). backend가 canonical working tree로 쓰려면 **그 폴더 안에서 git init**해야 한다 — backend는 경로를 그대로 받아 `pygit2.Repository`로 열기 때문이다.

```bash
cp -R deploy/sample-metadata /tmp/nl2sql-metadata
cd /tmp/nl2sql-metadata
git init -q && git add -A
git -c user.email="demo@local" -c user.name="demo" commit -q -m "seed"
```

`/tmp/nl2sql-metadata`는 예시 — 임의 경로로 바꿔도 된다. 아래 env에서 같은 경로를 가리키면 된다.

### 2. 웨어하우스

**Postgres만 (권장, Spider2·클러스터):** 루트 `.env`에 `MCP_POSTGRES_URL`·`MCP_POSTGRES_SOURCE_NAME=local_postgres`를 두고 mcp를 띄운다. `MCP_DUCKDB_PATH`는 설정하지 않는다. Spider2-Lite 자산·PG 적재·Opik 평가: [spider2-eval/DESIGN.md](spider2-eval/DESIGN.md) (`uv run spider2-load-pg` 등).

metadata의 source 이름은 `local_postgres`와 일치해야 한다([deploy/sample-metadata/](deploy/sample-metadata/)).

### 3. 환경 변수

| 변수 | 컴포넌트 | 값 (예시) |
|---|---|---|
| `MCP_BIND_ADDR` | mcp | `127.0.0.1:8800` |
| `MCP_METADATA_REPO` | mcp | `/tmp/nl2sql-metadata` (로컬 clone 경로; Phase 4에선 mcp 전용 PVC) |
| `MCP_METADATA_GIT_REMOTE` | mcp | (선택) GitLab mirror HTTPS URL. unset이면 로컬 quickstart처럼 기존 working tree만 연다 |
| `MCP_GIT_PULL_TOKEN` | mcp | (선택) read-only HTTP(S) token — unset이면 공개 또는 자격증명 미사용 원격만 |
| `MCP_POSTGRES_URL` | mcp | (Postgres만) libpq URL |
| `MCP_POSTGRES_SOURCE_NAME` | mcp | `local_postgres` (기본값) |
| `MCP_SHARED_TOKEN` | mcp, backend | 임의의 16+ 바이트 문자열 |
| `MCP_URL` | backend | `http://127.0.0.1:8800/mcp` |
| `METADATA_REPO_PATH` | backend | `/tmp/nl2sql-metadata` |
| `METADATA_SCHEMA_PATH` | backend | repo-root `schemas/mdl.schema.json` 절대경로 (정본). 이미지에선 `/app/schemas/mdl.schema.json` 기본 set |
| `CONVERSATION_DB_URL` | backend | SQLAlchemy URL. 기본 `sqlite+aiosqlite:///./conversations.db`. Phase 4 운영은 postgres로 교체 |
| `NL2SQL_DEV_USER` | backend | `demo@local` (OIDC 우회 dev 모드) |
| `ANTHROPIC_API_KEY` | backend | provider API 키 |

### 4. 부팅

세 터미널에서:

```bash
# 터미널 1 — mcp
cd mcp
MCP_BIND_ADDR=127.0.0.1:8800 \
MCP_METADATA_REPO=/tmp/nl2sql-metadata \
MCP_POSTGRES_URL=postgresql://... \
MCP_SHARED_TOKEN=dev-shared-token-please-change \
cargo run --release
```

```bash
# 터미널 2 — backend
cd backend
MCP_URL=http://127.0.0.1:8800/mcp \
MCP_SHARED_TOKEN=dev-shared-token-please-change \
METADATA_REPO_PATH=/tmp/nl2sql-metadata \
NL2SQL_DEV_USER=demo@local \
ANTHROPIC_API_KEY=sk-... \
uv run python -m nl2sql_backend
```

```bash
# 터미널 3 — frontend
cd frontend
npm install   # 첫 회만
npm run dev
```

브라우저: <http://localhost:5173>. vite는 `/api/*`만 backend(8080)로 프록시한다([frontend/vite.config.ts](frontend/vite.config.ts)). 정적 자산은 vite dev server가 직접 서빙 — HMR 유지.

### 테스트

```bash
cd backend
uv run pytest tests/test_mdl_compose.py tests/test_mdl_lifecycle.py -v
```

### 데모 질문 예시

```
지난달 주문 합계가 가장 큰 고객 3명은?
국가별 주문 합계
electronics 카테고리 상품 목록
```
