#!/usr/bin/env python3
"""Generate consolidated *.model.json / *.relationship.json from PostgreSQL."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE = "local_postgres"
SKIP_SCHEMAS = {"adventureworks", "airlines", "bank_sales_trading", "pg_catalog", "information_schema"}

LINE_PAT = re.compile(r"detail|line|item|payment|review|passes|segment", re.I)
SALE_CHILD_PAT = re.compile(
    r"order[_ ]?(items|details|lines|payments|reviews)|invoice[_ ]?lines?|"
    r"ticket_flights|boarding_passes|salesorderdetail|order_details|order_items|"
    r"leads_closed|leads_qualified|ball_by_ball|batsman_scored|extra_runs|wicket_taken",
    re.I,
)
SALE_HDR_PAT = re.compile(
    r"orders|salesorder|sales_order|invoice(?!_line)|bookings?|tickets|"
    r"olist_orders|pizza_.*orders|rental(?!s)|matches(?!_)",
    re.I,
)

TOPIC_RULES: list[tuple[re.Pattern[str], str]] = [
    (SALE_CHILD_PAT, "sale_line"),
    (SALE_HDR_PAT, "sale"),
    (re.compile(r"product|film(?!_)|item(?!s)|veg_cat|pizza_names|mst_products", re.I), "product"),
    (re.compile(r"customer|client|passenger|shopper|bowler(?!_)|student(?!s)", re.I), "customer"),
    (re.compile(r"employee|staff|faculty|driver|agent|salesperson|seller|enterainer|member(?!s)", re.I), "employee"),
    (re.compile(r"player|batter|pitcher|wrestler|driver(?!s)", re.I), "player"),
    (re.compile(r"^team|teams|franchise|constructor(?!s)", re.I), "team"),
    (re.compile(r"flight(?!s)|race(?!s)|match(?!_|es)|game(?!s)|event(?!s)", re.I), "event"),
    (re.compile(r"payment|transaction|txn|deliveries|orders(?!_)", re.I), "payment"),
    (re.compile(r"airport|city|country|region|territor|location|address|hub", re.I), "location"),
    (re.compile(r"aircraft|seat", re.I), "aircraft"),
]

# Shared table-prefix → topic (2+ tables with same prefix)
PREFIX_TOPICS: dict[str, str] = {
    "hardware": "hardware",
    "web": "web",
    "university": "university",
    "pizza": "pizza",
    "shopping_cart": "shopping_cart",
    "veg": "vegetable",
    "bitcoin": "bitcoin",
    "interest": "interest",
    "companies": "company",
    "companies_industries": "company",
    "companies_funding": "company",
    "companies_dates": "company",
}

# Explicit table-set merges (pattern → topic)
MERGE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^film(_actor|_category|_text)?$|^film$", re.I), "film"),
    (re.compile(r"^(rental|payment)$", re.I), "rental"),
    (re.compile(r"^(invoice_items|invoices)$", re.I), "sale"),
    (re.compile(r"^(order_items|order_payments|order_reviews|orders|order_details|"
                r"olist_order_items|olist_order_payments|olist_order_reviews|olist_orders)$", re.I), "sale"),
    (re.compile(r"^(products|olist_products|olist_products_dataset|product_category_name_translation)$", re.I), "product"),
    (re.compile(r"^(customers|olist_customers)$", re.I), "customer"),
    (re.compile(r"^(sellers|olist_sellers)$", re.I), "employee"),
    (re.compile(r"^(geolocation|olist_geolocation)$", re.I), "location"),
    (re.compile(r"^(tracks|albums|artists|genres|playlist_track|playlists|media_types|"
                r"Album|Artist|Genre|Track|Playlist|PlaylistTrack|MediaType)$", re.I), "music_catalog"),
    (re.compile(r"^(player|batting|pitching|fielding|appearances|all_star|salary|hall_of_fame|"
                r"player_award|player_college|fielding_outfield)(_|$|_postseason)", re.I), "player"),
    (re.compile(r"^manager(_award|_half|_award_vote)?(_|$)", re.I), "manager"),
    (re.compile(r"^(home_game|team_half|team_franchise|team)$", re.I), "team"),
    (re.compile(r"^(ball_by_ball|batsman_scored|extra_runs|wicket_taken|player_match)$", re.I), "match_event"),
    (re.compile(r"^(M_Cast|M_Country|M_Director|M_Genre|M_Language|M_Location|M_Producer)$", re.I), "movie_link"),
    (re.compile(r"^(collisions|parties|victims|case_ids)$", re.I), "collision"),
    (re.compile(r"^deliveries$", re.I), "delivery"),
    (re.compile(r"^(leads_closed|leads_qualified)$", re.I), "lead"),
    (re.compile(r"^(Engagements|Entertainer_Members|Entertainer_Styles|Entertainers|"
                r"Musical_Preferences|Musical_Styles)$", re.I), "entertainment"),
    (re.compile(r"^(Student_Schedules|Faculty_Classes|Faculty_Categories|Faculty_Subjects|"
                r"Classes|Students|Faculty)$", re.I), "school"),
    (re.compile(r"^(Matches|Cards|Events|Wrestlers|Belts|Promotions|Locations|Match_Types|Tables)$", re.I), "wrestling"),
]

PG_TO_MDL = {
    "boolean": "boolean", "smallint": "smallint", "integer": "int", "bigint": "bigint",
    "real": "float", "double precision": "double", "numeric": "decimal",
    "text": "text", "character varying": "varchar", "date": "date",
    "time without time zone": "time", "timestamp without time zone": "timestamp",
    "timestamp with time zone": "timestamptz", "json": "json", "jsonb": "json",
    "uuid": "uuid", "bytea": "bytes",
}


@dataclass
class Column:
    name: str
    data_type: str
    is_nullable: bool
    precision: str = ""
    scale: str = ""


@dataclass
class TableMeta:
    name: str
    columns: list[Column] = field(default_factory=list)
    pk_cols: list[str] = field(default_factory=list)


@dataclass
class FK:
    from_table: str
    from_col: str
    to_table: str
    to_col: str


class UF:
    def __init__(self, items: list[str]) -> None:
        self.p = {x: x for x in items}

    def find(self, x: str) -> str:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra

    def groups(self) -> dict[str, list[str]]:
        g: dict[str, list[str]] = defaultdict(list)
        for x in self.p:
            g[self.find(x)].append(x)
        return g


def load_env() -> None:
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def psql_query(sql: str) -> list[list[str]]:
    url = os.environ["MCP_POSTGRES_URL"]
    proc = subprocess.run(
        ["psql", url, "-v", "ON_ERROR_STOP=1", "-At", "-F", "\t", "-c", sql],
        capture_output=True, text=True, check=True,
    )
    return [ln.split("\t") for ln in proc.stdout.strip().splitlines() if ln]


def to_snake(name: str) -> str:
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return re.sub(r"_+", "_", s.replace("-", "_").replace(" ", "_").lower()).strip("_")


def mdl_type(data_type: str, precision: str, scale: str) -> str:
    dt = data_type.lower()
    if dt == "numeric" and precision:
        return f"decimal({precision},{scale or '0'})"
    return PG_TO_MDL.get(dt, "text")


def normalize_table_name(table: str) -> str:
    t = re.sub(r"_archive$", "", table, flags=re.I)
    t = re.sub(r"_postseason$", "", t, flags=re.I)
    return t


def prefix_topic(table: str) -> str | None:
    tl = table.lower()
    for prefix, topic in sorted(PREFIX_TOPICS.items(), key=lambda x: -len(x[0])):
        if tl.startswith(prefix):
            return topic
    if tl.startswith("olist_"):
        if re.search(r"order_(items|payments|reviews)|orders", tl):
            return "sale"
        if "product" in tl:
            return "product"
        if "customer" in tl:
            return "customer"
        if "seller" in tl:
            return "employee"
        if "geolocation" in tl:
            return "location"
    return None


def apply_merge_patterns(assignment: dict[str, str], tables: list[str]) -> None:
    for pat, topic in MERGE_PATTERNS:
        matched = [t for t in tables if pat.search(t)]
        if not matched:
            continue
        for t in matched:
            assignment[t] = topic


def topic_for_table(table: str) -> str:
    base = normalize_table_name(table)
    pt = prefix_topic(table)
    if pt:
        return pt
    for pat, topic in TOPIC_RULES:
        if pat.search(base) or pat.search(table):
            return topic
    return to_snake(base)


def fetch_schemas() -> list[str]:
    rows = psql_query("""
        SELECT schema_name FROM information_schema.schemata
        WHERE schema_name NOT IN ('pg_catalog','information_schema','pg_toast')
          AND schema_name NOT LIKE 'pg_%' ORDER BY 1
    """)
    return [r[0] for r in rows if r[0] not in SKIP_SCHEMAS]


def fetch_tables(schema: str) -> list[str]:
    rows = psql_query(f"""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = '{schema}' AND table_type = 'BASE TABLE' ORDER BY 1
    """)
    return [r[0] for r in rows]


def fetch_columns(schema: str, table: str) -> list[Column]:
    rows = psql_query(f"""
        SELECT column_name, data_type, is_nullable,
               COALESCE(numeric_precision::text,''), COALESCE(numeric_scale::text,'')
        FROM information_schema.columns
        WHERE table_schema = '{schema}' AND table_name = '{table}'
        ORDER BY ordinal_position
    """)
    return [Column(r[0], r[1], r[2] == "YES", r[3] if len(r) > 3 else "", r[4] if len(r) > 4 else "")
            for r in rows if len(r) >= 3]


def fetch_pk(schema: str, table: str) -> list[str]:
    rows = psql_query(f"""
        SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema AND tc.table_name = kcu.table_name
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema = '{schema}' AND tc.table_name = '{table}'
        ORDER BY kcu.ordinal_position
    """)
    return [r[0] for r in rows]


def fetch_fks(schema: str) -> list[FK]:
    rows = psql_query(f"""
        SELECT tc.table_name, kcu.column_name, ccu.table_name, ccu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
          ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = '{schema}'
        ORDER BY 1,2
    """)
    return [FK(r[0], r[1], r[2], r[3]) for r in rows]


def table_matches_base(table: str, base: str) -> bool:
    tl, b = table.lower(), base.lower()
    if tl == b or tl == b + "s" or tl.rstrip("s") == b.rstrip("s"):
        return True
    if tl.endswith("_" + b) or tl.endswith("_" + b + "s"):
        return True
    return False


def resolve_pk_col(tmeta: TableMeta, hint: str | None = None) -> str | None:
    if tmeta.pk_cols:
        return tmeta.pk_cols[0]
    if hint:
        for c in tmeta.columns:
            if c.name.lower() == hint.lower():
                return c.name
    for c in tmeta.columns:
        cl = c.name.lower()
        if cl in ("id",) or cl.endswith("_id") or (cl.endswith("id") and cl != "guid"):
            return c.name
    return tmeta.columns[0].name if tmeta.columns else None


def infer_fks(tables: dict[str, TableMeta]) -> list[FK]:
    fks: list[FK] = []
    seen: set[tuple[str, str, str]] = set()
    for tname, tmeta in tables.items():
        for col in tmeta.columns:
            cn = col.name.lower()
            bases: list[str] = []
            if cn.endswith("_id") and cn != "id":
                bases.append(cn[:-3])
            elif cn.endswith("id") and cn not in ("id", "rowguid", "uuid", "guid") and len(cn) > 2:
                bases.append(cn[:-2])
            for base in bases:
                for target, ttarget in tables.items():
                    if target == tname or not table_matches_base(target, base):
                        continue
                    pk = resolve_pk_col(ttarget, col.name)
                    if pk and (tname, col.name, target) not in seen:
                        seen.add((tname, col.name, target))
                        fks.append(FK(tname, col.name, target, pk))
                    break
    return fks


def should_fk_merge(a: str, b: str, fks: list[FK]) -> bool:
    ta, tb = topic_for_table(a), topic_for_table(b)
    if ta == tb:
        return True
    sale_topics = {"sale", "sale_line"}
    if ta in sale_topics and tb in sale_topics:
        return True
    if SALE_CHILD_PAT.search(a) and SALE_HDR_PAT.search(b):
        return True
    if SALE_CHILD_PAT.search(b) and SALE_HDR_PAT.search(a):
        return True
    if re.sub(r"_postseason$|_archive$", "", a, flags=re.I) == re.sub(
        r"_postseason$|_archive$", "", b, flags=re.I
    ):
        return True
    # junction / link tables M_* merge with film/movie topic partner
    if a.lower().startswith("m_") or b.lower().startswith("m_"):
        return ta == tb or "movie" in ta or "movie" in tb or "film" in ta or "film" in tb
    return False


def pick_model_name(tables: list[str], fks: list[FK]) -> str:
    topics = {topic_for_table(t) for t in tables}
    if topics <= {"sale", "sale_line"} or (topics & {"sale", "sale_line"}):
        return "sale"
    if len(topics) == 1:
        return next(iter(topics))
    # hub = most referenced
    refs = defaultdict(int)
    for fk in fks:
        if fk.to_table in tables:
            refs[fk.to_table] += 1
    if refs:
        hub = max(refs, key=lambda t: refs[t])
        ht = topic_for_table(hub)
        if ht not in ("sale_line",):
            return ht
        return to_snake(hub)
    return to_snake(sorted(tables)[0])


def assign_topics(tables: list[str], fks: list[FK]) -> dict[str, str]:
    uf = UF(tables)
    for fk in fks:
        if fk.from_table in tables and fk.to_table in tables:
            if should_fk_merge(fk.from_table, fk.to_table, fks):
                uf.union(fk.from_table, fk.to_table)

    # merge same-prefix groups only for explicit PREFIX_TOPICS keys
    by_prefix: dict[str, list[str]] = defaultdict(list)
    for t in tables:
        for prefix in PREFIX_TOPICS:
            if t.lower().startswith(prefix):
                by_prefix[prefix].append(t)
    for prefix, group in by_prefix.items():
        if len(group) >= 2:
            for i in range(1, len(group)):
                uf.union(group[0], group[i])

    assignment: dict[str, str] = {}
    used: set[str] = set()
    for _, group in uf.groups().items():
        stem = pick_model_name(group, fks)
        base, n = stem, 2
        while stem in used:
            stem = f"{base}_{n}"
            n += 1
        used.add(stem)
        for t in group:
            assignment[t] = stem

    for t in tables:
        if t not in assignment:
            stem = topic_for_table(t)
            base, n = stem, 2
            while stem in used:
                stem = f"{base}_{n}"
                n += 1
            used.add(stem)
            assignment[t] = stem

    apply_merge_patterns(assignment, tables)
    return assignment


def alias_for(i: int) -> str:
    return ["m", "t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9"][i] if i < 10 else f"t{i}"


def col_semantic_name(table: str, col: str, used: set[str]) -> str:
    name = to_snake(col)
    if name in used:
        name = f"{to_snake(table)}_{name}"
    base, n = name, 2
    while name in used:
        name = f"{base}_{n}"
        n += 1
    used.add(name)
    return name


def build_model(schema: str, model_name: str, table_names: list[str],
                all_tables: dict[str, TableMeta], intra_fks: list[FK]) -> dict:
    line_tables = [t for t in table_names if LINE_PAT.search(t) or SALE_CHILD_PAT.search(t)]
    refs = defaultdict(int)
    for fk in intra_fks:
        refs[fk.to_table] += 1
    if line_tables and model_name == "sale":
        ordered = sorted(line_tables, key=lambda t: (-refs.get(t, 0), t))
        ordered += sorted([t for t in table_names if t not in line_tables], key=lambda t: (-refs.get(t, 0), t))
    else:
        ordered = sorted(table_names, key=lambda t: (-refs.get(t, 0), t))

    alias_map = {t: alias_for(i) for i, t in enumerate(ordered)}
    join_plan: dict[str, FK | None] = {ordered[0]: None}
    remaining = ordered[1:]

    while remaining:
        progress = False
        for t in list(remaining):
            for fk in intra_fks:
                if fk.from_table == t and fk.to_table in join_plan:
                    join_plan[t] = fk
                    remaining.remove(t)
                    progress = True
                    break
                if fk.to_table == t and fk.from_table in join_plan:
                    join_plan[t] = FK(fk.to_table, fk.to_col, fk.from_table, fk.from_col)
                    remaining.remove(t)
                    progress = True
                    break
        if not progress:
            join_plan[remaining.pop(0)] = None

    tables_json = []
    for i, t in enumerate(ordered):
        entry: dict = {
            "alias": alias_map[t],
            "priority": i + 1,
            "tableReference": {"schema": schema, "table": t},
        }
        fk = join_plan.get(t)
        if fk and fk.from_table == t:
            entry["join"] = {"to": alias_map[fk.to_table], "type": "left",
                             "on": [{"left": fk.from_col, "right": fk.to_col}]}
        elif fk and fk.to_table == t:
            entry["join"] = {"to": alias_map[fk.from_table], "type": "left",
                             "on": [{"left": fk.from_col, "right": fk.to_col}]}
        tables_json.append(entry)

    used_cols: set[str] = set()
    physical_cols: list[dict] = []
    pk_candidates: list[tuple[str, str, str]] = []
    for t in ordered:
        for c in all_tables[t].columns:
            sem = col_semantic_name(t, c.name, used_cols)
            physical_cols.append({
                "name": sem, "kind": "physical",
                "type": mdl_type(c.data_type, c.precision, c.scale),
                "from": f"{alias_map[t]}.{c.name}",
                **({"notNull": True} if not c.is_nullable else {}),
            })
            cl = c.name.lower()
            if c.name in all_tables[t].pk_cols or cl == "id" or cl.endswith("_id") or cl.endswith("id"):
                pk_candidates.append((sem, t, c.name))

    pk_name = None
    skip_fk_cols = {"order_id", "customer_id", "product_id", "seller_id", "invoice_id", "book_ref", "ticket_no", "flight_id"}
    for sem, t, col in pk_candidates:
        if LINE_PAT.search(t) or SALE_CHILD_PAT.search(t):
            if col.lower().endswith("_id") and col.lower() not in skip_fk_cols:
                pk_name = sem
                break
    if not pk_name:
        for sem, t, _ in pk_candidates:
            if LINE_PAT.search(t) or SALE_CHILD_PAT.search(t):
                pk_name = sem
                break
    if not pk_name and pk_candidates:
        pk_name = pk_candidates[0][0]
    if not pk_name and physical_cols:
        pk_name = physical_cols[0]["name"]

    desc = ", ".join(ordered[:4]) + (", …" if len(ordered) > 4 else "")
    return {
        "name": model_name,
        "source": SOURCE,
        "description": f"{schema} 스키마 {model_name} 주제 ({desc}).",
        "tables": tables_json,
        "primaryKey": pk_name,
        "columns": physical_cols,
    }


def cardinality(schema: str, fk: FK) -> str:
    try:
        rows = psql_query(f"""
            SELECT COUNT(*)::bigint, COUNT(DISTINCT c."{fk.from_col}")::bigint
            FROM "{schema}"."{fk.from_table}" c WHERE c."{fk.from_col}" IS NOT NULL
        """)
        cr, df = int(rows[0][0]), int(rows[0][1])
        return "one_to_one" if cr and df == cr else "many_to_one"
    except subprocess.CalledProcessError:
        return "many_to_one"


def generate_schema(schema: str, out_root: Path) -> tuple[int, int]:
    table_list = fetch_tables(schema)
    if not table_list:
        return 0, 0

    all_tables: dict[str, TableMeta] = {}
    for t in table_list:
        all_tables[t] = TableMeta(t, fetch_columns(schema, t), fetch_pk(schema, t))

    fks = fetch_fks(schema)
    inferred = infer_fks(all_tables)
    fk_set = {(f.from_table, f.from_col, f.to_table, f.to_col) for f in fks}
    for f in inferred:
        if (f.from_table, f.from_col, f.to_table, f.to_col) not in fk_set:
            fks.append(f)

    assignment = assign_topics(table_list, fks)
    models_tables: dict[str, list[str]] = defaultdict(list)
    for t, m in assignment.items():
        models_tables[m].append(t)

    out_dir = out_root / schema
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.model.json"):
        old.unlink()
    for old in out_dir.glob("*.relationship.json"):
        old.unlink()

    model_jsons: dict[str, dict] = {}
    for model_name, tnames in sorted(models_tables.items()):
        intra = [fk for fk in fks if assignment.get(fk.from_table) == model_name
                 and assignment.get(fk.to_table) == model_name]
        model_jsons[model_name] = build_model(schema, model_name, tnames, all_tables, intra)

    rels: list[dict] = []
    seen: set[str] = set()
    for fk in fks:
        fm, tm = assignment.get(fk.from_table), assignment.get(fk.to_table)
        if not fm or not tm or fm == tm:
            continue
        fc, tc = to_snake(fk.from_col), to_snake(fk.to_col)
        rel_name = f"{fm}_to_{tm}"
        if rel_name in seen:
            continue
        seen.add(rel_name)
        rels.append({
            "name": rel_name, "joinType": cardinality(schema, fk),
            "from": {"model": fm, "column": fc},
            "to": {"model": tm, "column": tc},
            "description": f"{fm} → {tm}",
        })
        if fm in model_jsons:
            cols = {c["name"] for c in model_jsons[fm]["columns"]}
            if fc in cols and not any(c.get("kind") == "relation" and c.get("to") == tm
                                      for c in model_jsons[fm]["columns"]):
                model_jsons[fm]["columns"].append({
                    "name": tm, "kind": "relation", "to": tm, "via": rel_name,
                    "description": f"dotted path: {fm}.{tm}",
                })

    for name, mj in model_jsons.items():
        (out_dir / f"{name}.model.json").write_text(json.dumps(mj, indent=2, ensure_ascii=False) + "\n")
    for rel in rels:
        (out_dir / f"{rel['name']}.relationship.json").write_text(json.dumps(rel, indent=2, ensure_ascii=False) + "\n")
    return len(model_jsons), len(rels)


def main() -> None:
    load_env()
    if not os.environ.get("MCP_POSTGRES_URL"):
        sys.exit("MCP_POSTGRES_URL not set")
    schemas = fetch_schemas()
    if len(sys.argv) > 1:
        schemas = [s for s in sys.argv[1:] if s not in SKIP_SCHEMAS]
    total_m = total_r = 0
    for schema in schemas:
        m, r = generate_schema(schema, REPO_ROOT)
        print(f"{schema}: {m} models, {r} relationships")
        total_m += m
        total_r += r
    print(f"TOTAL: {total_m} models, {total_r} relationships across {len(schemas)} schemas")


if __name__ == "__main__":
    main()
