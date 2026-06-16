# nl2sql — 설치·사용 가이드

자연어로 데이터에 질문하면, 시스템이 메타데이터(테이블·조인 정의)를 바탕으로 SQL을 만들고 데이터베이스에서 실행한 뒤 표·차트로 보여 줍니다.

배포물은 [Releases](https://github.com/yoosungung/nl2sql-releases/releases)(mcp 바이너리)와 [GHCR](https://github.com/yoosungung/nl2sql/pkgs/container/nl2sql-backend)(backend+UI Docker 이미지)에서 받습니다. **같은 릴리스 태그**를 쓰면 됩니다.

---

## 무엇을 받을 수 있나

| 항목 | 배포 위치 |
|------|-----------|
| **mcp** `nl2sql-mcp-linux-amd64` | [Releases](https://github.com/yoosungung/nl2sql-releases/releases) asset |
| **mcp** `nl2sql-mcp-macos-arm64` | [Releases](https://github.com/yoosungung/nl2sql-releases/releases) asset (Apple Silicon Mac) |
| **backend + 웹 UI** | `ghcr.io/yoosungung/nl2sql-backend:<태그>` |
| **메타데이터 정의** | 포함하지 않음 — 조직에서 별도 git 저장소로 관리 |

nl2sql을 쓰려면 **mcp**, **backend(UI 포함)**, **메타데이터 저장소**, **PostgreSQL(또는 지원 DB)**, **LLM API**가 모두 필요합니다.

---

## 구성 요소

| 구성 요소 | 역할 |
|-----------|------|
| **웹 UI** | 채팅(질의·결과·차트) + 메타데이터 편집 화면 |
| **backend** | API·채팅 에이전트·메타데이터 관리 (UI 정적 파일 포함) |
| **mcp** | 질의용 SQL 생성·실행 |
| **메타데이터** | 어떤 테이블·조인을 쓸지 정의한 JSON 파일 모음 |
| **웨어하우스** | 실제 데이터가 있는 DB (예: PostgreSQL) |
| **LLM** | 채팅 에이전트용 API |

---

## 사전 준비

| 항목 | 설명 |
|------|------|
| mcp 실행 환경 | Linux x86_64 서버, 또는 Apple Silicon Mac |
| Docker | backend+UI 이미지 실행용 |
| PostgreSQL | 질의 대상 DB 접속 정보 |
| 메타데이터 저장소 | 모델·관계 정의 디렉터리(또는 git clone) |
| LLM API | Anthropic 또는 OpenAI 호환 API |

메타데이터 디렉터리는 비어 있으면 mcp·backend가 시작되지 않습니다.

---

## 1. mcp 바이너리 설치

[Releases](https://github.com/yoosungung/nl2sql-releases/releases)에서 OS에 맞는 파일을 받습니다.

### Linux (x86_64)

```bash
VERSION=v0.1.0   # Releases 태그로 변경
curl -LO "https://github.com/yoosungung/nl2sql-releases/releases/download/${VERSION}/nl2sql-mcp-linux-amd64"
chmod +x nl2sql-mcp-linux-amd64
sudo mv nl2sql-mcp-linux-amd64 /usr/local/bin/nl2sql-mcp
```

### macOS (Apple Silicon)

```bash
VERSION=v0.1.0
curl -LO "https://github.com/yoosungung/nl2sql-releases/releases/download/${VERSION}/nl2sql-mcp-macos-arm64"
chmod +x nl2sql-mcp-macos-arm64
sudo mv nl2sql-mcp-macos-arm64 /usr/local/bin/nl2sql-mcp
```

---

## 2. backend + UI (Docker)

frontend가 빌드되어 `/app/static`으로 포함된 **통합 이미지**입니다. 별도 frontend 서버는 필요 없습니다.

```bash
VERSION=v0.1.0
docker pull ghcr.io/yoosungung/nl2sql-backend:${VERSION}
```

GHCR 패키지가 private이면 먼저 로그인합니다 (`read:packages` 권한 PAT):

```bash
echo "$GITHUB_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USER --password-stdin
```

실행 예 (메타데이터·env는 환경에 맞게 volume·변수 추가):

```bash
docker run --rm -p 8080:8080 \
  -e MCP_URL=http://host.docker.internal:8800/mcp \
  -e MCP_SHARED_TOKEN=your-shared-secret \
  -e METADATA_REPO_PATH=/var/lib/nl2sql/metadata \
  -e ANTHROPIC_API_KEY=sk-... \
  -v /path/to/metadata:/var/lib/nl2sql/metadata \
  ghcr.io/yoosungung/nl2sql-backend:${VERSION}
```

브라우저: `http://localhost:8080`

---

## 3. 환경 변수

backend와 **같은 값**으로 맞춰야 하는 항목이 있습니다.

### mcp

| 변수 | 필수 | 설명 |
|------|------|------|
| `MCP_SHARED_TOKEN` | 예 | backend와 **동일한** 인증 토큰 |
| `MCP_METADATA_REPO` | 예 | 메타데이터 디렉터리 경로 |
| `MCP_POSTGRES_URL` | DB 사용 시 | `postgresql://user:pass@host:5432/dbname` |
| `MCP_POSTGRES_SOURCE_NAME` | | 메타데이터 source 이름과 동일 (예: `local_postgres`) |
| `MCP_BIND_ADDR` | | 기본 `127.0.0.1:8800` |
| `MCP_METADATA_GIT_REMOTE` | 선택 | 메타데이터 원격 git URL |
| `MCP_GIT_PULL_TOKEN` | 선택 | private git 읽기 토큰 |

### backend

| 변수 | 필수 | 설명 |
|------|------|------|
| `MCP_URL` | 예 | `http://<mcp-호스트>:8800/mcp` |
| `MCP_SHARED_TOKEN` | 예 | mcp와 동일 |
| `METADATA_REPO_PATH` | 예 | mcp의 `MCP_METADATA_REPO`와 동일 내용 |
| `ANTHROPIC_API_KEY` | LLM | Anthropic 사용 시 |
| `OPENAI_API_BASE` | LLM | OpenAI 호환 API 주소 |
| `OPENAI_API_KEY` | LLM | API 키 |
| `NL2SQL_MODEL` | | 모델 이름 (예: `openai:model-name`) |
| `CONVERSATION_DB_URL` | | 대화 기록 DB (미설정 시 SQLite) |

LLM은 Anthropic **또는** OpenAI 호환 방식 중 하나만 설정하면 됩니다.

---

## 4. 기동·확인

### mcp

```bash
export MCP_BIND_ADDR=0.0.0.0:8800
export MCP_METADATA_REPO=/var/lib/nl2sql/metadata
export MCP_POSTGRES_URL='postgresql://user:pass@host:5432/warehouse'
export MCP_POSTGRES_SOURCE_NAME=local_postgres
export MCP_SHARED_TOKEN='your-shared-secret'

nl2sql-mcp
```

```bash
curl -s http://127.0.0.1:8800/health   # ok
```

### backend

```bash
curl -s http://127.0.0.1:8080/api/ready
```

---

## 5. 사용 방법

1. 브라우저에서 backend URL(예: `http://localhost:8080`)을 엽니다.
2. 자연어로 질문합니다. 예:
   - `지난달 주문 합계가 가장 큰 고객 3명은?`
   - `국가별 주문 합계`
3. 결과가 표·차트로 표시됩니다.
4. 권한이 있으면 **메타데이터 콘솔**에서 테이블·조인 정의를 수정할 수 있습니다.

---

## 6. 문제 해결

| 증상 | 확인할 것 |
|------|-----------|
| 채팅이 안 됨(503) | LLM API 키·모델 설정 |
| mcp 연결 거부(401) | `MCP_SHARED_TOKEN`이 backend와 같은지 |
| SQL 실행 실패 | DB URL, 메타데이터 source 이름, 테이블 정의 |
| UI가 안 보임 | backend 이미지가 정상 기동했는지, 포트 8080 |
| `docker pull` 실패 | GHCR 로그인·패키지 공개 여부 |

---

## 7. 업그레이드

1. [Releases](https://github.com/yoosungung/nl2sql-releases/releases)에서 mcp 바이너리를 새 태그로 교체합니다.
2. `docker pull ghcr.io/yoosungung/nl2sql-backend:<새-태그>` 후 backend 컨테이너를 재시작합니다.
3. mcp 프로세스도 재시작합니다.
4. 릴리스 노트에 breaking change가 있으면 메타데이터 호환 여부를 확인합니다.

---

## 문의

메타데이터·인프라는 조직별로 다릅니다. mcp·backend 배포물 외 사항은 담당 운영팀에 문의하세요.
