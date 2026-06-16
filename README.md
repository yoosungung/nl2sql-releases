# nl2sql — 설치·사용 가이드

자연어로 데이터에 질문하면, 시스템이 메타데이터(테이블·조인 정의)를 바탕으로 SQL을 만들고 데이터베이스에서 실행한 뒤 표·차트로 보여 줍니다.

바이너리는 이 저장소의 [Releases](https://github.com/yoosungung/nl2sql-releases/releases)에서 받습니다.

---

## 무엇을 받을 수 있나

| 항목 | 이 Releases |
|------|-------------|
| **mcp** (`nl2sql-mcp-linux-amd64`) | 포함 — Linux x86_64용 실행 파일 |
| **backend + 웹 UI** | 포함하지 않음 — 운영팀이 제공하는 이미지·패키지 사용 |
| **메타데이터 정의** | 포함하지 않음 — 조직에서 별도 git 저장소로 관리 |

nl2sql을 쓰려면 **mcp**, **backend(UI 포함)**, **메타데이터 저장소**, **PostgreSQL(또는 지원 DB)**, **LLM API**가 모두 필요합니다. 이 페이지는 그중 **mcp 설치·연동**을 다룹니다.

---

## 구성 요소

| 구성 요소 | 역할 |
|-----------|------|
| **웹 UI** | 채팅(질의·결과·차트) + 메타데이터 편집 화면 |
| **backend** | API·채팅 에이전트·메타데이터 관리 |
| **mcp** | 질의용 SQL 생성·실행 |
| **메타데이터** | 어떤 테이블·조인을 쓸지 정의한 JSON 파일 모음 |
| **웨어하우스** | 실제 데이터가 있는 DB (예: PostgreSQL) |
| **LLM** | 채팅 에이전트용 API |

---

## 사전 준비

운영팀 또는 설치 가이드에서 아래를 먼저 준비합니다.

| 항목 | 설명 |
|------|------|
| Linux x86_64 서버 | mcp 바이너리 실행 환경 |
| PostgreSQL | 질의 대상 DB 접속 정보 |
| 메타데이터 저장소 | 모델·관계 정의가 들어 있는 디렉터리(또는 git clone) |
| backend + UI | 배포된 서비스 URL·이미지 |
| LLM API | Anthropic 또는 OpenAI 호환 API |

메타데이터 디렉터리는 비어 있으면 mcp·backend가 시작되지 않습니다.

---

## 1. mcp 바이너리 설치

[Releases](https://github.com/yoosungung/nl2sql-releases/releases)에서 최신 `nl2sql-mcp-linux-amd64`를 받습니다.

```bash
# 버전은 Releases 페이지의 태그로 바꿉니다 (예: v0.1.0)
VERSION=v0.1.0
curl -LO "https://github.com/yoosungung/nl2sql-releases/releases/download/${VERSION}/nl2sql-mcp-linux-amd64"
chmod +x nl2sql-mcp-linux-amd64
sudo mv nl2sql-mcp-linux-amd64 /usr/local/bin/nl2sql-mcp
```

---

## 2. 환경 변수

backend와 **같은 값**으로 맞춰야 하는 항목이 있습니다. Kubernetes 등에서는 Secret·ConfigMap에 동일한 키 이름으로 넣으면 됩니다.

### mcp

| 변수 | 필수 | 설명 |
|------|------|------|
| `MCP_SHARED_TOKEN` | 예 | backend와 **동일한** 인증 토큰 |
| `MCP_METADATA_REPO` | 예 | 메타데이터 디렉터리 경로 |
| `MCP_POSTGRES_URL` | DB 사용 시 | `postgresql://user:pass@host:5432/dbname` |
| `MCP_POSTGRES_SOURCE_NAME` | | 메타데이터에 적힌 source 이름과 동일 (예: `local_postgres`) |
| `MCP_BIND_ADDR` | | 기본 `127.0.0.1:8800`. 다른 서버에서 접속하면 `0.0.0.0:8800` 등 |
| `MCP_METADATA_GIT_REMOTE` | 선택 | 메타데이터를 원격 git에서 받을 때 URL |
| `MCP_GIT_PULL_TOKEN` | 선택 | private git용 읽기 전용 토큰 |

### backend (mcp와 연동할 때)

| 변수 | 필수 | 설명 |
|------|------|------|
| `MCP_URL` | 예 | `http://<mcp-호스트>:8800/mcp` |
| `MCP_SHARED_TOKEN` | 예 | mcp와 동일 |
| `METADATA_REPO_PATH` | 예 | mcp의 `MCP_METADATA_REPO`와 같은 내용 |
| `ANTHROPIC_API_KEY` | LLM | Anthropic 사용 시 |
| `OPENAI_API_BASE` | LLM | OpenAI 호환 API 주소 |
| `OPENAI_API_KEY` | LLM | API 키 |
| `NL2SQL_MODEL` | | 사용할 모델 이름 (예: `openai:model-name`) |
| `CONVERSATION_DB_URL` | | 대화 기록 DB (미설정 시 SQLite 파일) |

LLM 변수는 **둘 중 하나 방식**만 쓰면 됩니다(Anthropic 또는 OpenAI 호환).

---

## 3. 기동·확인

### mcp 실행

```bash
export MCP_BIND_ADDR=0.0.0.0:8800
export MCP_METADATA_REPO=/var/lib/nl2sql/metadata
export MCP_POSTGRES_URL='postgresql://user:pass@host:5432/warehouse'
export MCP_POSTGRES_SOURCE_NAME=local_postgres
export MCP_SHARED_TOKEN='your-shared-secret'

nl2sql-mcp
```

정상 여부:

```bash
curl -s http://127.0.0.1:8800/health
# ok
```

### backend·UI

backend는 운영 환경에 맞게 이미 배포되어 있어야 합니다. 위 mcp 주소·공유 토큰·메타데이터 경로·LLM 설정이 backend 쪽과 일치하는지 확인합니다.

```bash
curl -s http://<backend-호스트>:8080/api/ready
```

브라우저에서는 **backend가 제공하는 URL**로 접속합니다(UI는 backend에 포함된 경우가 많습니다).

---

## 4. 사용 방법

1. 브라우저에서 채팅 화면을 엽니다.
2. 자연어로 질문합니다. 예:
   - `지난달 주문 합계가 가장 큰 고객 3명은?`
   - `국가별 주문 합계`
3. 결과가 표·차트로 표시됩니다.
4. 권한이 있으면 **메타데이터 콘솔**에서 테이블·조인 정의를 수정할 수 있습니다.

메타데이터를 바꾼 뒤에는 backend가 저장·동기화하고, 이후 질의는 갱신된 정의를 사용합니다.

---

## 5. 문제 해결

| 증상 | 확인할 것 |
|------|-----------|
| 채팅이 안 됨(503) | LLM API 키·모델 설정 |
| mcp 연결 거부(401) | `MCP_SHARED_TOKEN`이 backend와 같은지 |
| SQL 실행 실패 | DB 접속 URL, 메타데이터 source 이름, 테이블 정의 |
| mcp가 안 뜸 | 메타데이터 경로, `MCP_SHARED_TOKEN` 설정 |
| 메타데이터 오류 | 메타데이터 디렉터리에 유효한 정의 파일이 있는지 |

mcp 응답 확인(토큰 필요):

```bash
curl -s -H "Authorization: Bearer $MCP_SHARED_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
  http://127.0.0.1:8800/mcp
```

---

## 6. 업그레이드

1. [Releases](https://github.com/yoosungung/nl2sql-releases/releases)에서 새 `nl2sql-mcp-linux-amd64`를 받아 교체합니다.
2. mcp 프로세스(또는 컨테이너)를 재시작합니다.
3. backend·UI 버전은 운영팀 안내에 따릅니다.
4. 릴리스 노트에 breaking change가 있으면 메타데이터 호환 여부를 확인합니다.

---

## 문의

backend·UI·메타데이터·인프라는 조직별로 배포 방식이 다릅니다. 이 Releases에는 **mcp 바이너리**만 올라옵니다. 그 외는 담당 운영팀에 문의하세요.
