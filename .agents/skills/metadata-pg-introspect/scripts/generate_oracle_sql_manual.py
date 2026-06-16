#!/usr/bin/env python3
"""Manually consolidated oracle_sql/*.model.json and *.relationship.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "oracle_sql"
SCHEMA = "oracle_sql"
SOURCE = "local_postgres"


def phys(name: str, alias: str, col: str, typ: str = "text", not_null: bool = False) -> dict:
    c = {"name": name, "kind": "physical", "type": typ, "from": f"{alias}.{col}"}
    if not_null:
        c["notNull"] = True
    return c


def rel(name: str, to: str, via: str, desc: str | None = None) -> dict:
    c = {"name": name, "kind": "relation", "to": to, "via": via}
    if desc:
        c["description"] = desc
    return c


def relationship(stem: str, fm: str, fc: str, tm: str, tc: str, desc: str, join_type: str = "many_to_one") -> dict:
    return {
        "name": stem,
        "joinType": join_type,
        "from": {"model": fm, "column": fc},
        "to": {"model": tm, "column": tc},
        "description": desc,
    }


def write_model(data: dict) -> None:
    (OUT / f"{data['name']}.model.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_rel(data: dict) -> None:
    (OUT / f"{data['name']}.relationship.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob("*.model.json"):
        p.unlink()
    for p in OUT.glob("*.relationship.json"):
        p.unlink()

    write_model(
        {
            "name": "sale",
            "source": SOURCE,
            "description": "판매 주제. 주문 라인(orderlines)·주문 헤더(orders)를 join으로 구성.",
            "tables": [
                {"alias": "ln", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "orderlines"}},
                {
                    "alias": "hdr",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "orders"},
                    "join": {"to": "ln", "type": "left", "on": [{"left": "id", "right": "order_id"}]},
                },
            ],
            "primaryKey": "order_line_id",
            "columns": [
                phys("order_line_id", "ln", "id", "bigint", True),
                phys("order_id", "ln", "order_id", "bigint", True),
                phys("product_id", "ln", "product_id", "bigint", True),
                phys("qty", "ln", "qty", "double", True),
                phys("amount", "ln", "amount", "double", True),
                phys("customer_id", "hdr", "customer_id", "bigint", True),
                phys("ordered", "hdr", "ordered", "text"),
                phys("delivery", "hdr", "delivery", "text"),
                rel("customer", "customer", "sale_to_customer", "dotted path: sale.customer"),
                rel("product", "product", "sale_to_product", "dotted path: sale.product"),
            ],
        }
    )

    write_model(
        {
            "name": "customer",
            "source": SOURCE,
            "description": "고객 주제. customers·즐겨찾기·리뷰 목록을 join으로 구성.",
            "tables": [
                {"alias": "c", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "customers"}},
                {
                    "alias": "fav",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "customer_favorites"},
                    "join": {"to": "c", "type": "left", "on": [{"left": "customer_id", "right": "id"}]},
                },
                {
                    "alias": "rev",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "customer_reviews"},
                    "join": {"to": "c", "type": "left", "on": [{"left": "customer_id", "right": "id"}]},
                },
            ],
            "primaryKey": "customer_id",
            "columns": [
                phys("customer_id", "c", "id", "bigint", True),
                phys("customer_name", "c", "name", "text", True),
                phys("favorite_list", "fav", "favorite_list", "text"),
                phys("review_list", "rev", "review_list", "text"),
            ],
        }
    )

    write_model(
        {
            "name": "employee",
            "source": SOURCE,
            "description": "직원 주제. 고용 이력·직원 마스터·상급자를 join으로 구성.",
            "tables": [
                {"alias": "per", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "emp_hire_periods"}},
                {
                    "alias": "emp",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "employees"},
                    "join": {"to": "per", "type": "left", "on": [{"left": "id", "right": "emp_id"}]},
                },
                {
                    "alias": "sup",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "employees"},
                    "join": {"to": "emp", "type": "left", "on": [{"left": "id", "right": "supervisor_id"}]},
                },
            ],
            "primaryKey": "employee_id",
            "columns": [
                phys("employee_id", "per", "emp_id", "bigint", True),
                phys("hire_start", "per", "start_", "text", True),
                phys("hire_end", "per", "end_", "text"),
                phys("period_title", "per", "title", "text", True),
                phys("employee_name", "emp", "name", "text", True),
                phys("employee_title", "emp", "title", "text", True),
                phys("supervisor_id", "emp", "supervisor_id", "bigint"),
                phys("supervisor_name", "sup", "name", "text"),
            ],
        }
    )

    write_model(
        {
            "name": "product",
            "source": SOURCE,
            "description": "제품 카탈로그 주제. products·그룹·알코올·최소주문·월별 실적을 join으로 구성.",
            "tables": [
                {"alias": "p", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "products"}},
                {
                    "alias": "grp",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "product_groups"},
                    "join": {"to": "p", "type": "left", "on": [{"left": "id", "right": "group_id"}]},
                },
                {
                    "alias": "alc",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "product_alcohol"},
                    "join": {"to": "p", "type": "left", "on": [{"left": "product_id", "right": "id"}]},
                },
                {
                    "alias": "min",
                    "priority": 4,
                    "tableReference": {"schema": SCHEMA, "table": "product_minimums"},
                    "join": {"to": "p", "type": "left", "on": [{"left": "product_id", "right": "id"}]},
                },
            ],
            "primaryKey": "product_id",
            "columns": [
                phys("product_id", "p", "id", "bigint", True),
                phys("product_name", "p", "name", "text", True),
                phys("group_id", "p", "group_id", "bigint", True),
                phys("group_name", "grp", "name", "text", True),
                phys("sales_volume", "alc", "sales_volume", "double", True),
                phys("abv", "alc", "abv", "double", True),
                phys("qty_minimum", "min", "qty_minimum", "double", True),
                phys("qty_purchase", "min", "qty_purchase", "double", True),
            ],
        }
    )

    write_model(
        {
            "name": "monthly",
            "source": SOURCE,
            "description": "제품 월별 계획·실적. monthly_budget·monthly_sales를 product_id·mth로 join.",
            "tables": [
                {"alias": "bud", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "monthly_budget"}},
                {
                    "alias": "sal",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "monthly_sales"},
                    "join": {
                        "to": "bud",
                        "type": "left",
                        "on": [{"left": "product_id", "right": "product_id"}, {"left": "mth", "right": "mth"}],
                    },
                },
            ],
            "primaryKey": "month_key",
            "columns": [
                phys("product_id", "bud", "product_id", "bigint", True),
                phys("month_key", "bud", "mth", "text", True),
                phys("budget_qty", "bud", "qty", "double", True),
                phys("sales_qty", "sal", "qty", "bigint"),
                rel("product", "product", "monthly_to_product", "dotted path: monthly.product"),
            ],
        }
    )

    write_model(
        {
            "name": "location",
            "source": SOURCE,
            "description": "창고 슬롯(로케이션) 참조.",
            "tables": [{"alias": "loc", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "locations"}}],
            "primaryKey": "location_id",
            "columns": [
                phys("location_id", "loc", "id", "bigint", True),
                phys("warehouse", "loc", "warehouse", "bigint", True),
                phys("aisle", "loc", "aisle", "text", True),
                phys("position", "loc", "position", "bigint", True),
            ],
        }
    )

    write_model(
        {
            "name": "inventory",
            "source": SOURCE,
            "description": "재고 주제. inventory·로케이션·매입·양조장을 join으로 구성.",
            "tables": [
                {"alias": "inv", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "inventory"}},
                {
                    "alias": "loc",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "locations"},
                    "join": {"to": "inv", "type": "left", "on": [{"left": "id", "right": "location_id"}]},
                },
                {
                    "alias": "pur",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "purchases"},
                    "join": {"to": "inv", "type": "left", "on": [{"left": "id", "right": "purchase_id"}]},
                },
                {
                    "alias": "brw",
                    "priority": 4,
                    "tableReference": {"schema": SCHEMA, "table": "breweries"},
                    "join": {"to": "pur", "type": "left", "on": [{"left": "id", "right": "brewery_id"}]},
                },
            ],
            "primaryKey": "inventory_id",
            "columns": [
                phys("inventory_id", "inv", "id", "bigint", True),
                phys("location_id", "inv", "location_id", "bigint", True),
                phys("product_id", "inv", "product_id", "bigint", True),
                phys("purchase_id", "inv", "purchase_id", "bigint", True),
                phys("qty", "inv", "qty", "double", True),
                phys("warehouse", "loc", "warehouse", "bigint", True),
                phys("aisle", "loc", "aisle", "text", True),
                phys("position", "loc", "position", "bigint", True),
                phys("purchased", "pur", "purchased", "text", True),
                phys("purchase_qty", "pur", "qty", "bigint", True),
                phys("purchase_cost", "pur", "cost", "double", True),
                phys("brewery_id", "pur", "brewery_id", "bigint", True),
                phys("brewery_name", "brw", "name", "text", True),
                rel("product", "product", "inventory_to_product", "dotted path: inventory.product"),
                rel("location", "location", "inventory_to_location", "dotted path: inventory.location"),
            ],
        }
    )

    write_model(
        {
            "name": "picking",
            "source": SOURCE,
            "description": "피킹 주제. 피킹 라인·리스트·로그·로케이션·피커 직원을 join으로 구성.",
            "tables": [
                {"alias": "ln", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "picking_line"}},
                {
                    "alias": "pl",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "picking_list"},
                    "join": {"to": "ln", "type": "left", "on": [{"left": "id", "right": "picklist_id"}]},
                },
                {
                    "alias": "loc",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "locations"},
                    "join": {"to": "ln", "type": "left", "on": [{"left": "id", "right": "location_id"}]},
                },
                {
                    "alias": "emp",
                    "priority": 4,
                    "tableReference": {"schema": SCHEMA, "table": "employees"},
                    "join": {"to": "pl", "type": "left", "on": [{"left": "id", "right": "picker_emp_id"}]},
                },
                {
                    "alias": "log",
                    "priority": 5,
                    "tableReference": {"schema": SCHEMA, "table": "picking_log"},
                    "join": {
                        "to": "ln",
                        "type": "left",
                        "on": [
                            {"left": "picklist_id", "right": "picklist_id"},
                            {"left": "pickline_no", "right": "line_no"},
                        ],
                    },
                },
            ],
            "primaryKey": "picklist_id",
            "columns": [
                phys("picklist_id", "ln", "picklist_id", "bigint", True),
                phys("line_no", "ln", "line_no", "bigint", True),
                phys("location_id", "ln", "location_id", "bigint", True),
                phys("order_id", "ln", "order_id", "bigint", True),
                phys("product_id", "ln", "product_id", "bigint", True),
                phys("pick_qty", "ln", "qty", "double", True),
                phys("picklist_created", "pl", "created", "text", True),
                phys("picker_emp_id", "pl", "picker_emp_id", "bigint"),
                phys("warehouse", "loc", "warehouse", "bigint", True),
                phys("aisle", "loc", "aisle", "text", True),
                phys("position", "loc", "position", "bigint", True),
                phys("picker_name", "emp", "name", "text"),
                phys("log_time", "log", "log_time", "text"),
                phys("log_activity", "log", "activity", "text"),
                phys("log_location_id", "log", "location_id", "bigint"),
                rel("product", "product", "picking_to_product", "dotted path: picking.product"),
                rel("sale", "sale", "picking_to_sale", "dotted path: picking.sale"),
                rel("location", "location", "picking_to_location", "dotted path: picking.location"),
                rel("employee", "employee", "picking_to_employee", "dotted path: picking.employee"),
            ],
        }
    )

    write_model(
        {
            "name": "packaging",
            "source": SOURCE,
            "description": "포장 주제. 포장 관계·외부·내부 포장 마스터를 join으로 구성.",
            "tables": [
                {"alias": "rel", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "packaging_relations"}},
                {
                    "alias": "outer",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "packaging"},
                    "join": {"to": "rel", "type": "left", "on": [{"left": "id", "right": "packaging_id"}]},
                },
                {
                    "alias": "inner",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "packaging"},
                    "join": {"to": "rel", "type": "left", "on": [{"left": "id", "right": "contains_id"}]},
                },
            ],
            "primaryKey": "packaging_id",
            "columns": [
                phys("packaging_id", "rel", "packaging_id", "bigint", True),
                phys("contains_id", "rel", "contains_id", "bigint", True),
                phys("contains_qty", "rel", "qty", "bigint", True),
                phys("outer_pack_name", "outer", "name", "text", True),
                phys("inner_pack_name", "inner", "name", "text", True),
            ],
        }
    )

    write_model(
        {
            "name": "stock",
            "source": SOURCE,
            "description": "주식 시세 주제. 일별 ticker·종목 마스터(stock)를 join으로 구성.",
            "tables": [
                {"alias": "t", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "ticker"}},
                {
                    "alias": "s",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "stock"},
                    "join": {"to": "t", "type": "left", "on": [{"left": "symbol", "right": "symbol"}]},
                },
            ],
            "primaryKey": "symbol",
            "columns": [
                phys("symbol", "t", "symbol", "text", True),
                phys("trade_day", "t", "day", "text", True),
                phys("price", "t", "price", "double", True),
                phys("company", "s", "company", "text", True),
            ],
        }
    )

    write_model(
        {
            "name": "web",
            "source": SOURCE,
            "description": "웹 앱 주제. 페이지·앱·일별 카운터·방문 로그를 join으로 구성.",
            "tables": [
                {"alias": "cnt", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "web_counter_hist"}},
                {
                    "alias": "pg",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "web_pages"},
                    "join": {
                        "to": "cnt",
                        "type": "left",
                        "on": [{"left": "app_id", "right": "app_id"}, {"left": "page_no", "right": "page_no"}],
                    },
                },
                {
                    "alias": "app",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "web_apps"},
                    "join": {"to": "pg", "type": "left", "on": [{"left": "id", "right": "app_id"}]},
                },
                {
                    "alias": "vis",
                    "priority": 4,
                    "tableReference": {"schema": SCHEMA, "table": "web_page_visits"},
                    "join": {
                        "to": "pg",
                        "type": "left",
                        "on": [{"left": "app_id", "right": "app_id"}, {"left": "page_no", "right": "page_no"}],
                    },
                },
            ],
            "primaryKey": "counter_day",
            "columns": [
                phys("app_id", "cnt", "app_id", "bigint", True),
                phys("page_no", "cnt", "page_no", "bigint", True),
                phys("counter_day", "cnt", "day", "text", True),
                phys("counter", "cnt", "counter", "bigint", True),
                phys("friendly_url", "pg", "friendly_url", "text", True),
                phys("app_name", "app", "name", "text", True),
                phys("client_ip", "vis", "client_ip", "text"),
                phys("visit_time", "vis", "visit_time", "text"),
            ],
        }
    )

    write_model(
        {
            "name": "web_audience",
            "source": SOURCE,
            "description": "웹 오디언스 일별 지표. demographics·devices를 day로 join.",
            "tables": [
                {"alias": "demo", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "web_demographics"}},
                {
                    "alias": "dev",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "web_devices"},
                    "join": {"to": "demo", "type": "left", "on": [{"left": "day", "right": "day"}]},
                },
            ],
            "primaryKey": "audience_day",
            "columns": [
                phys("audience_day", "demo", "day", "text", True),
                phys("m_tw_cnt", "demo", "m_tw_cnt", "bigint"),
                phys("m_tw_qty", "demo", "m_tw_qty", "bigint"),
                phys("m_fb_cnt", "demo", "m_fb_cnt", "bigint"),
                phys("m_fb_qty", "demo", "m_fb_qty", "bigint"),
                phys("f_tw_cnt", "demo", "f_tw_cnt", "bigint"),
                phys("f_tw_qty", "demo", "f_tw_qty", "bigint"),
                phys("f_fb_cnt", "demo", "f_fb_cnt", "bigint"),
                phys("f_fb_qty", "demo", "f_fb_qty", "bigint"),
                phys("pc", "dev", "pc", "bigint"),
                phys("tablet", "dev", "tablet", "bigint"),
                phys("phone", "dev", "phone", "bigint"),
            ],
        }
    )

    write_model(
        {
            "name": "collection",
            "source": SOURCE,
            "description": "ID·이름 컬렉션 주제. 항목·컬렉션 타입을 join으로 구성.",
            "tables": [
                {"alias": "ent", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "id_name_coll_entries"}},
                {
                    "alias": "typ",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "id_name_coll_type"},
                    "join": {"to": "ent", "type": "left", "on": [{"left": "collection_id", "right": "collection_id"}]},
                },
            ],
            "primaryKey": "entry_id",
            "columns": [
                phys("collection_id", "ent", "collection_id", "bigint", True),
                phys("entry_id", "ent", "id", "bigint", True),
                phys("entry_name", "ent", "name", "text"),
            ],
        }
    )

    for name, table, pk, cols, desc in [
        (
            "id_name_type",
            "id_name_type",
            "id",
            [phys("id", "t", "id", "bigint", True), phys("name", "t", "name", "text")],
            "ID·이름 단순 참조 타입.",
        ),
        (
            "favorite_coll_type",
            "favorite_coll_type",
            "id",
            [phys("id", "t", "id", "bigint", True)],
            "즐겨찾기 컬렉션 타입 참조.",
        ),
        (
            "channels_dim",
            "channels_dim",
            "channel_id",
            [
                phys("channel_id", "t", "id", "bigint", True),
                phys("channel_name", "t", "name", "text", True),
                phys("shortcut", "t", "shortcut", "text", True),
            ],
            "채널 차원.",
        ),
        (
            "gender_dim",
            "gender_dim",
            "letter",
            [phys("letter", "t", "letter", "text", True), phys("gender_name", "t", "name", "text")],
            "성별 차원.",
        ),
        (
            "conway_gen_zero",
            "conway_gen_zero",
            "cell_x",
            [
                phys("cell_x", "t", "x", "bigint", True),
                phys("cell_y", "t", "y", "bigint", True),
                phys("alive", "t", "alive", "bigint", True),
            ],
            "Conway 게임 오브 라이프 초기 격자.",
        ),
        (
            "server_heartbeat",
            "server_heartbeat",
            "server",
            [
                phys("server", "t", "server", "text", True),
                phys("beat_time", "t", "beat_time", "text", True),
            ],
            "서버 하트비트 로그.",
        ),
    ]:
        write_model(
            {
                "name": name,
                "source": SOURCE,
                "description": desc,
                "tables": [{"alias": "t", "priority": 1, "tableReference": {"schema": SCHEMA, "table": table}}],
                "primaryKey": pk,
                "columns": cols,
            }
        )

    write_rel(relationship("sale_to_customer", "sale", "customer_id", "customer", "customer_id", "sale → customer"))
    write_rel(relationship("sale_to_product", "sale", "product_id", "product", "product_id", "sale → product"))
    write_rel(relationship("monthly_to_product", "monthly", "product_id", "product", "product_id", "monthly → product"))
    write_rel(relationship("inventory_to_product", "inventory", "product_id", "product", "product_id", "inventory → product"))
    write_rel(
        relationship(
            "inventory_to_location",
            "inventory",
            "location_id",
            "location",
            "location_id",
            "inventory → location",
            "many_to_one",
        )
    )
    write_rel(relationship("picking_to_product", "picking", "product_id", "product", "product_id", "picking → product"))
    write_rel(relationship("picking_to_sale", "picking", "order_id", "sale", "order_id", "picking → sale (주문 헤더)"))
    write_rel(
        relationship(
            "picking_to_location",
            "picking",
            "location_id",
            "location",
            "location_id",
            "picking → location",
            "many_to_one",
        )
    )
    write_rel(
        relationship(
            "picking_to_employee",
            "picking",
            "picker_emp_id",
            "employee",
            "employee_id",
            "picking → employee (피커)",
            "many_to_one",
        )
    )


if __name__ == "__main__":
    main()
