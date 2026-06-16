#!/usr/bin/env python3
"""Validate MDL metadata via POST /api/metadata/fs/validate (no git commit)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
# deploy/sample-metadata 또는 metadata clone 루트
DEFAULT_REPO_ROOT = SCRIPT_DIR.parents[3]

API_BASE = f"{os.environ.get('NL2SQL_BACKEND_URL', 'http://127.0.0.1:8080').rstrip('/')}/api"
REPO_ROOT = Path(os.environ.get("METADATA_REPO_ROOT", DEFAULT_REPO_ROOT))
AUTH_HEADERS = {
    "X-Forwarded-User": os.environ.get("VALIDATE_USER", "validator"),
    "X-Forwarded-Email": os.environ.get("VALIDATE_EMAIL", "validator@local"),
    "Content-Type": "application/json",
}


def _request(
    method: str,
    path: str,
    payload: dict | None = None,
) -> tuple[int, object]:
    url = f"{API_BASE}{path}"
    data = None if payload is None else json.dumps(payload).encode()
    headers = AUTH_HEADERS if payload is not None else {
        k: v for k, v in AUTH_HEADERS.items() if k != "Content-Type"
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw) if raw else {"detail": e.reason}
        except json.JSONDecodeError:
            return e.code, raw or str(e.reason)
    except urllib.error.URLError as e:
        return 0, {"detail": f"cannot reach backend at {API_BASE}: {e}"}


def post_validate(payload: dict) -> tuple[int, object]:
    return _request("POST", "/metadata/fs/validate", payload)


def post_delete_plan(path: str) -> tuple[int, object]:
    return _request("POST", "/metadata/fs/delete-plan", {"path": path.lstrip("/")})


def emit_result(
    status: int,
    body: object,
    *,
    label: str,
    as_json: bool,
) -> int:
    if as_json:
        out = {"label": label, "http_status": status, "result": body}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        if status != 200:
            return 1
        return 0 if isinstance(body, dict) and body.get("ok") else 1

    if status != 200:
        print(f"{label}: HTTP {status}: {body}", file=sys.stderr)
        return 1
    if not isinstance(body, dict):
        print(f"{label}: unexpected response", file=sys.stderr)
        return 1
    if body.get("ok"):
        print(f"{label}: ok")
        return 0
    issues = body.get("issues", [])
    if not isinstance(issues, list):
        print(f"{label}: missing issues", file=sys.stderr)
        return 1
    codes = Counter(
        i.get("code", "?") for i in issues if isinstance(i, dict)
    )
    print(f"{label}: issues={len(issues)} by_code={dict(codes)}")
    for i in issues[:40]:
        if not isinstance(i, dict):
            continue
        print(f"  [{i.get('code')}] {i.get('path')}: {str(i.get('message', ''))[:120]}")
    if len(issues) > 40:
        print(f"  ... and {len(issues) - 40} more")
    return 1


def cmd_manifest(*, as_json: bool) -> int:
    status, body = post_validate({"scope": "repo"})
    return emit_result(status, body, label="scope=repo", as_json=as_json)


def cmd_file(rel: str, *, as_json: bool) -> int:
    rel = rel.lstrip("/")
    status, body = post_validate({"path": rel})
    return emit_result(status, body, label=rel, as_json=as_json)


def cmd_draft(rel: str, source: str | None, *, as_json: bool) -> int:
    rel = rel.lstrip("/")
    if source is None or source == "-":
        src = REPO_ROOT / rel
    else:
        src = Path(source)
    if not src.is_file():
        print(f"draft: file not found: {src}", file=sys.stderr)
        return 1
    draft = json.loads(src.read_text(encoding="utf-8"))
    status, body = post_validate({"path": rel, "body": draft})
    return emit_result(status, body, label=rel, as_json=as_json)


def cmd_delete(rel: str, *, as_json: bool) -> int:
    rel = rel.lstrip("/")
    status, body = post_validate({"path": rel, "delete": True})
    return emit_result(status, body, label=f"delete {rel}", as_json=as_json)


def cmd_delete_plan(rel: str, *, as_json: bool) -> int:
    rel = rel.lstrip("/")
    status, plan = post_delete_plan(rel)
    if status != 200 or not isinstance(plan, dict):
        print(f"delete-plan: HTTP {status}: {plan}", file=sys.stderr)
        return 1
    paths = plan.get("paths")
    if not isinstance(paths, list) or not paths:
        print("delete-plan: empty paths", file=sys.stderr)
        return 1
    status, body = post_validate({"paths": paths, "delete": True})
    return emit_result(status, body, label=f"delete-plan {rel}", as_json=as_json)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate MDL via POST /api/metadata/fs/validate",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print machine-readable JSON (exit 1 if ok=false)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("manifest", help="validate entire repo at HEAD")

    p_file = sub.add_parser("file", help="validate committed file at HEAD")
    p_file.add_argument("path", help="repo-relative *.kind.json")

    p_draft = sub.add_parser("draft", help="validate JSON before commit (path + body)")
    p_draft.add_argument("path", help="target repo-relative path")
    p_draft.add_argument(
        "source",
        nargs="?",
        help="local JSON file (default: read from metadata repo at path)",
    )

    p_del = sub.add_parser("delete", help="validate hypothetical delete")
    p_del.add_argument("path")

    p_plan = sub.add_parser("delete-plan", help="delete-plan paths + batch validate")
    p_plan.add_argument("path")

    args = parser.parse_args(argv)
    as_json = args.json

    if args.cmd == "manifest":
        return cmd_manifest(as_json=as_json)
    if args.cmd == "file":
        return cmd_file(args.path, as_json=as_json)
    if args.cmd == "draft":
        return cmd_draft(args.path, args.source, as_json=as_json)
    if args.cmd == "delete":
        return cmd_delete(args.path, as_json=as_json)
    if args.cmd == "delete-plan":
        return cmd_delete_plan(args.path, as_json=as_json)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
