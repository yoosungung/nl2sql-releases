#!/usr/bin/env python3
"""Consolidated pagila metadata (PG introspected types, topic-first joins)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "pagila"
SCHEMA = "pagila"
SOURCE = "local_postgres"


def phys(name: str, alias: str, col: str, typ: str, not_null: bool = False) -> dict:
    c = {"name": name, "kind": "physical", "type": typ, "from": f"{alias}.{col}"}
    if not_null:
        c["notNull"] = True
    return c


def rel(name: str, to: str, via: str, desc: str | None = None) -> dict:
    c = {"name": name, "kind": "relation", "to": to, "via": via}
    if desc:
        c["description"] = desc
    else:
        c["description"] = f"dotted path: {name}"
    return c


def relationship(stem: str, fm: str, fc: str, tm: str, tc: str, desc: str, jt: str = "many_to_one") -> dict:
    return {
        "name": stem,
        "joinType": jt,
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
            "name": "film",
            "source": SOURCE,
            "description": "DVD 카탈로그. 영화·출연(junction)·분류·전문검색·언어·카테고리를 join으로 통합.",
            "tables": [
                {"alias": "m", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "film"}},
                {
                    "alias": "fa",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "film_actor"},
                    "join": {"to": "m", "type": "left", "on": [{"left": "film_id", "right": "film_id"}]},
                },
                {
                    "alias": "fc",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "film_category"},
                    "join": {"to": "m", "type": "left", "on": [{"left": "film_id", "right": "film_id"}]},
                },
                {
                    "alias": "ft",
                    "priority": 4,
                    "tableReference": {"schema": SCHEMA, "table": "film_text"},
                    "join": {"to": "m", "type": "left", "on": [{"left": "film_id", "right": "film_id"}]},
                },
                {
                    "alias": "cat",
                    "priority": 5,
                    "tableReference": {"schema": SCHEMA, "table": "category"},
                    "join": {"to": "fc", "type": "left", "on": [{"left": "category_id", "right": "category_id"}]},
                },
                {
                    "alias": "lang",
                    "priority": 6,
                    "tableReference": {"schema": SCHEMA, "table": "language"},
                    "join": {"to": "m", "type": "left", "on": [{"left": "language_id", "right": "language_id"}]},
                },
                {
                    "alias": "orig",
                    "priority": 7,
                    "tableReference": {"schema": SCHEMA, "table": "language"},
                    "join": {
                        "to": "m",
                        "type": "left",
                        "on": [{"left": "language_id", "right": "original_language_id"}],
                    },
                },
            ],
            "primaryKey": "film_id",
            "columns": [
                phys("film_id", "m", "film_id", "bigint", True),
                phys("title", "m", "title", "text", True),
                phys("description", "m", "description", "text"),
                phys("release_year", "m", "release_year", "text"),
                phys("language_id", "m", "language_id", "smallint", True),
                phys("original_language_id", "m", "original_language_id", "smallint"),
                phys("rental_duration", "m", "rental_duration", "smallint", True),
                phys("rental_rate", "m", "rental_rate", "decimal(4,2)", True),
                phys("length", "m", "length", "smallint"),
                phys("replacement_cost", "m", "replacement_cost", "decimal(5,2)", True),
                phys("rating", "m", "rating", "text"),
                phys("special_features", "m", "special_features", "text"),
                phys("last_update", "m", "last_update", "timestamp", True),
                phys("actor_id", "fa", "actor_id", "bigint"),
                phys("film_actor_last_update", "fa", "last_update", "timestamp"),
                phys("film_category_category_id", "fc", "category_id", "smallint"),
                phys("film_category_last_update", "fc", "last_update", "timestamp"),
                phys("film_text_title", "ft", "title", "text"),
                phys("film_text_description", "ft", "description", "text"),
                phys("category_name", "cat", "name", "text"),
                phys("category_last_update", "cat", "last_update", "timestamp"),
                phys("language_name", "lang", "name", "text"),
                phys("language_last_update", "lang", "last_update", "timestamp"),
                phys("original_language_name", "orig", "name", "text"),
                phys("original_language_last_update", "orig", "last_update", "timestamp"),
                rel("actor", "actor", "film_to_actor", "dotted path: film.actor"),
            ],
        }
    )

    write_model(
        {
            "name": "actor",
            "source": SOURCE,
            "description": "배우 마스터. film_actor junction으로 영화 연결.",
            "tables": [
                {"alias": "m", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "actor"}},
                {
                    "alias": "fa",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "film_actor"},
                    "join": {"to": "m", "type": "left", "on": [{"left": "actor_id", "right": "actor_id"}]},
                },
            ],
            "primaryKey": "actor_id",
            "columns": [
                phys("actor_id", "m", "actor_id", "decimal", True),
                phys("first_name", "m", "first_name", "text", True),
                phys("last_name", "m", "last_name", "text", True),
                phys("last_update", "m", "last_update", "timestamp", True),
                phys("film_id", "fa", "film_id", "bigint"),
                phys("film_actor_last_update", "fa", "last_update", "timestamp"),
                rel("film", "film", "actor_to_film", "dotted path: actor.film"),
            ],
        }
    )

    write_model(
        {
            "name": "location",
            "source": SOURCE,
            "description": "주소·도시·국가 위치 계층 (address 기준).",
            "tables": [
                {"alias": "m", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "address"}},
                {
                    "alias": "city",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "city"},
                    "join": {"to": "m", "type": "left", "on": [{"left": "city_id", "right": "city_id"}]},
                },
                {
                    "alias": "cty",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "country"},
                    "join": {"to": "city", "type": "left", "on": [{"left": "country_id", "right": "country_id"}]},
                },
            ],
            "primaryKey": "address_id",
            "columns": [
                phys("address_id", "m", "address_id", "bigint", True),
                phys("address", "m", "address", "text", True),
                phys("address2", "m", "address2", "text"),
                phys("district", "m", "district", "text", True),
                phys("city_id", "m", "city_id", "bigint", True),
                phys("postal_code", "m", "postal_code", "text"),
                phys("phone", "m", "phone", "text", True),
                phys("address_last_update", "m", "last_update", "timestamp", True),
                phys("city", "city", "city", "text", True),
                phys("country_id", "city", "country_id", "smallint", True),
                phys("city_last_update", "city", "last_update", "timestamp", True),
                phys("country", "cty", "country", "text", True),
                phys("country_last_update", "cty", "last_update", "timestamp"),
            ],
        }
    )

    write_model(
        {
            "name": "rental",
            "source": SOURCE,
            "description": "대여·결제. rental 헤더 grain에 payment를 left join.",
            "tables": [
                {"alias": "m", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "rental"}},
                {
                    "alias": "pay",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "payment"},
                    "join": {"to": "m", "type": "left", "on": [{"left": "rental_id", "right": "rental_id"}]},
                },
            ],
            "primaryKey": "rental_id",
            "columns": [
                phys("rental_id", "m", "rental_id", "bigint", True),
                phys("rental_date", "m", "rental_date", "timestamp", True),
                phys("inventory_id", "m", "inventory_id", "bigint", True),
                phys("customer_id", "m", "customer_id", "bigint", True),
                phys("return_date", "m", "return_date", "timestamp"),
                phys("staff_id", "m", "staff_id", "smallint", True),
                phys("rental_last_update", "m", "last_update", "timestamp", True),
                phys("payment_id", "pay", "payment_id", "bigint"),
                phys("payment_customer_id", "pay", "customer_id", "bigint"),
                phys("payment_staff_id", "pay", "staff_id", "smallint"),
                phys("amount", "pay", "amount", "decimal(5,2)"),
                phys("payment_date", "pay", "payment_date", "timestamp"),
                phys("payment_last_update", "pay", "last_update", "timestamp"),
                rel("customer", "customer", "rental_to_customer"),
                rel("employee", "employee", "rental_to_employee"),
                rel("inventory", "inventory", "rental_to_inventory"),
            ],
        }
    )

    write_model(
        {
            "name": "customer",
            "source": SOURCE,
            "description": "고객 마스터.",
            "tables": [{"alias": "m", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "customer"}}],
            "primaryKey": "customer_id",
            "columns": [
                phys("customer_id", "m", "customer_id", "bigint", True),
                phys("store_id", "m", "store_id", "bigint", True),
                phys("first_name", "m", "first_name", "text", True),
                phys("last_name", "m", "last_name", "text", True),
                phys("email", "m", "email", "text"),
                phys("address_id", "m", "address_id", "bigint", True),
                phys("active", "m", "active", "text", True),
                phys("create_date", "m", "create_date", "timestamp", True),
                phys("last_update", "m", "last_update", "timestamp", True),
                rel("location", "location", "customer_to_location"),
                rel("store", "store", "customer_to_store"),
            ],
        }
    )

    write_model(
        {
            "name": "employee",
            "source": SOURCE,
            "description": "직원(staff) 마스터.",
            "tables": [{"alias": "m", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "staff"}}],
            "primaryKey": "staff_id",
            "columns": [
                phys("staff_id", "m", "staff_id", "smallint", True),
                phys("first_name", "m", "first_name", "text", True),
                phys("last_name", "m", "last_name", "text", True),
                phys("address_id", "m", "address_id", "bigint", True),
                phys("picture", "m", "picture", "bytes"),
                phys("email", "m", "email", "text"),
                phys("store_id", "m", "store_id", "bigint", True),
                phys("active", "m", "active", "smallint", True),
                phys("username", "m", "username", "text", True),
                phys("password", "m", "password", "text"),
                phys("last_update", "m", "last_update", "timestamp", True),
                rel("location", "location", "employee_to_location"),
                rel("store", "store", "employee_to_store"),
            ],
        }
    )

    write_model(
        {
            "name": "store",
            "source": SOURCE,
            "description": "매장 마스터.",
            "tables": [{"alias": "m", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "store"}}],
            "primaryKey": "store_id",
            "columns": [
                phys("store_id", "m", "store_id", "bigint", True),
                phys("manager_staff_id", "m", "manager_staff_id", "smallint", True),
                phys("address_id", "m", "address_id", "bigint", True),
                phys("last_update", "m", "last_update", "timestamp", True),
                rel("location", "location", "store_to_location"),
                rel("employee", "employee", "store_to_employee"),
            ],
        }
    )

    write_model(
        {
            "name": "inventory",
            "source": SOURCE,
            "description": "매장별 영화 재고(inventory).",
            "tables": [{"alias": "m", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "inventory"}}],
            "primaryKey": "inventory_id",
            "columns": [
                phys("inventory_id", "m", "inventory_id", "bigint", True),
                phys("film_id", "m", "film_id", "bigint", True),
                phys("store_id", "m", "store_id", "bigint", True),
                phys("last_update", "m", "last_update", "timestamp", True),
                rel("film", "film", "inventory_to_film"),
                rel("store", "store", "inventory_to_store"),
            ],
        }
    )

    rels = [
        relationship("film_to_actor", "film", "actor_id", "actor", "actor_id", "영화 출연 → 배우"),
        relationship("actor_to_film", "actor", "film_id", "film", "film_id", "배우 출연 → 영화"),
        relationship("rental_to_customer", "rental", "customer_id", "customer", "customer_id", "대여 → 고객"),
        relationship("rental_to_employee", "rental", "staff_id", "employee", "staff_id", "대여 처리 직원"),
        relationship("rental_to_inventory", "rental", "inventory_id", "inventory", "inventory_id", "대여 재고"),
        relationship("inventory_to_film", "inventory", "film_id", "film", "film_id", "재고 → 영화"),
        relationship("inventory_to_store", "inventory", "store_id", "store", "store_id", "재고 → 매장"),
        relationship("customer_to_location", "customer", "address_id", "location", "address_id", "고객 주소"),
        relationship("customer_to_store", "customer", "store_id", "store", "store_id", "고객 소속 매장"),
        relationship("employee_to_location", "employee", "address_id", "location", "address_id", "직원 주소"),
        relationship("employee_to_store", "employee", "store_id", "store", "store_id", "직원 소속 매장"),
        relationship("store_to_location", "store", "address_id", "location", "address_id", "매장 주소"),
        relationship(
            "store_to_employee",
            "store",
            "manager_staff_id",
            "employee",
            "staff_id",
            "매장 관리 직원",
        ),
    ]
    for r in rels:
        write_rel(r)

    print(f"pagila: {len(list(OUT.glob('*.model.json')))} models, {len(rels)} relationships")


if __name__ == "__main__":
    main()
