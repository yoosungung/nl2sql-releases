#!/usr/bin/env bash
# Validate MDL via POST /api/metadata/fs/validate (no git commit).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
NL2SQL_ENV="${NL2SQL_ENV:-$REPO_ROOT/../../.env}"

export METADATA_REPO_ROOT="${METADATA_REPO_ROOT:-$REPO_ROOT}"
export NL2SQL_BACKEND_URL="${NL2SQL_BACKEND_URL:-http://127.0.0.1:8080}"
export VALIDATE_USER="${VALIDATE_USER:-validator}"
export VALIDATE_EMAIL="${VALIDATE_EMAIL:-validator@local}"

if [[ -f "$NL2SQL_ENV" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$NL2SQL_ENV"
  set +a
  # metadata clone에서 실행 시 repo 루트 우선
  if [[ -n "${METADATA_REPO_PATH:-}" && -d "$METADATA_REPO_PATH" ]]; then
    export METADATA_REPO_ROOT="$METADATA_REPO_PATH"
  fi
fi

exec python3 "$SCRIPT_DIR/validate_metadata.py" "$@"
