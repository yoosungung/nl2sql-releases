#!/usr/bin/env bash
# PostgreSQL introspection for nl2sql-metadata model authoring.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
if [[ -f "$REPO_ROOT/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$REPO_ROOT/.env"
  set +a
fi

if [[ -z "${MCP_POSTGRES_URL:-}" ]]; then
  echo "error: MCP_POSTGRES_URL is not set (repo .env or environment)" >&2
  exit 1
fi

run_sql() {
  psql "$MCP_POSTGRES_URL" -v ON_ERROR_STOP=1 -At -F $'\t' "$@"
}

run_sql_expanded() {
  psql "$MCP_POSTGRES_URL" -v ON_ERROR_STOP=1 "$@"
}

cmd="${1:-}"
shift || true

case "$cmd" in
  schemas)
    echo "# list_schemas"
    run_sql -c "
      SELECT schema_name
      FROM information_schema.schemata
      WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
        AND schema_name NOT LIKE 'pg_%'
      ORDER BY 1;
    "
    ;;

  tables)
    schema="${1:?usage: tables <schema>}"
    echo "# list_tables schema=$schema"
    run_sql -c "
      SELECT table_name
      FROM information_schema.tables
      WHERE table_schema = '$schema' AND table_type = 'BASE TABLE'
      ORDER BY 1;
    "
    ;;

  describe)
    schema="${1:?usage: describe <schema> <table>}"
    table="${2:?usage: describe <schema> <table>}"
    echo "# describe_table $schema.$table"
    echo "## columns"
    run_sql_expanded -c "
      SELECT
        column_name,
        data_type,
        udt_name,
        is_nullable,
        character_maximum_length,
        numeric_precision,
        numeric_scale
      FROM information_schema.columns
      WHERE table_schema = '$schema' AND table_name = '$table'
      ORDER BY ordinal_position;
    "
    echo "## primary_key"
    run_sql -c "
      SELECT kcu.column_name
      FROM information_schema.table_constraints tc
      JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
        AND tc.table_name = kcu.table_name
      WHERE tc.constraint_type = 'PRIMARY KEY'
        AND tc.table_schema = '$schema'
        AND tc.table_name = '$table'
      ORDER BY kcu.ordinal_position;
    "
    ;;

  fks)
    schema="${1:?usage: fks <schema>}"
    echo "# discover_fks schema=$schema"
    run_sql_expanded -c "
      SELECT
        tc.table_name AS from_table,
        kcu.column_name AS from_column,
        ccu.table_schema AS to_schema,
        ccu.table_name AS to_table,
        ccu.column_name AS to_column,
        tc.constraint_name
      FROM information_schema.table_constraints tc
      JOIN information_schema.key_column_usage kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
      JOIN information_schema.constraint_column_usage ccu
        ON ccu.constraint_name = tc.constraint_name
        AND ccu.table_schema = tc.table_schema
      WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_schema = '$schema'
      ORDER BY from_table, from_column;
    "
    ;;

  cardinality)
    schema="${1:?usage: cardinality <schema> <child_table> <fk_col> <parent_table> <parent_col>}"
    child="${2:?}"
    fk_col="${3:?}"
    parent="${4:?}"
    parent_col="${5:?}"
    echo "# cardinality_check $schema.$child.$fk_col -> $schema.$parent.$parent_col"
    run_sql_expanded -c "
      SELECT
        COUNT(*)::bigint AS child_rows,
        COUNT(DISTINCT c.\"$fk_col\")::bigint AS distinct_fk,
        (SELECT COUNT(*)::bigint FROM \"$schema\".\"$parent\") AS parent_rows
      FROM \"$schema\".\"$child\" c
      WHERE c.\"$fk_col\" IS NOT NULL;
    "
    echo "# suggested_join_type (child model from -> parent model to): many_to_one if distinct_fk << child_rows; one_to_one if distinct_fk = child_rows and child_rows <= parent_rows"
    ;;

  sample)
    schema="${1:?usage: sample <schema> <table> [limit]}"
    table="${2:?}"
    limit="${3:-5}"
    echo "# sample_rows $schema.$table limit=$limit"
    run_sql_expanded -c "SELECT * FROM \"$schema\".\"$table\" LIMIT $limit;"
    ;;

  *)
    echo "usage: pg-inspect.sh <schemas|tables|describe|fks|cardinality|sample> [args...]" >&2
    exit 1
    ;;
esac
