#!/usr/bin/env python3
"""One-off: consolidated sqlite-sakila/*.model.json and *.relationship.json from PG introspection."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "sqlite-sakila"
SCHEMA = "sqlite-sakila"
SOURCE = "local_postgres"


def mdl_type(pg: str, precision: int | None = None, scale: int | None = None) -> str:
    if pg == "numeric" and precision is not None and scale is not None:
        return f"decimal({precision},{scale})"
    if pg == "numeric":
        return "decimal"
    mapping = {
        "bigint": "bigint",
        "int8": "bigint",
        "smallint": "smallint",
        "int2": "smallint",
        "text": "text",
        "timestamp without time zone": "timestamp",
        "bytea": "bytes",
    }
    return mapping.get(pg, "text")


def phys(
    name: str,
    alias: str,
    col: str,
    pg: str,
    not_null: bool = False,
    *,
    precision: int | None = None,
    scale: int | None = None,
    desc: str | None = None,
) -> dict:
    c: dict = {
        "name": name,
        "kind": "physical",
        "type": mdl_type(pg, precision, scale),
        "from": f"{alias}.{col}",
    }
    if not_null:
        c["notNull"] = True
    if desc:
        c["description"] = desc
    return c


def calc(name: str, expr: str, typ: str = "text", not_null: bool = True, desc: str | None = None) -> dict:
    c = {"name": name, "kind": "calculated", "type": typ, "expression": expr, "notNull": not_null}
    if desc:
        c["description"] = desc
    return c


def rel(name: str, to: str, via: str, desc: str | None = None) -> dict:
    c = {"name": name, "kind": "relation", "to": to, "via": via}
    if desc:
        c["description"] = desc
    return c


def relationship(
    stem: str,
    from_model: str,
    from_col: str,
    to_model: str,
    to_col: str,
    join_type: str,
    desc: str,
) -> dict:
    return {
        "name": stem,
        "joinType": join_type,
        "from": {"model": from_model, "column": from_col},
        "to": {"model": to_model, "column": to_col},
        "description": desc,
    }


def write_model(data: dict) -> None:
    path = OUT / f"{data['name']}.model.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_rel(data: dict) -> None:
    path = OUT / f"{data['name']}.relationship.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    write_model(
        {
            "name": "location",
            "source": SOURCE,
            "description": "주소·도시·국가(location). address를 grain으로 city·country를 join.",
            "tables": [
                {"alias": "a", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "address"}},
                {
                    "alias": "c",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "city"},
                    "join": {"to": "a", "type": "left", "on": [{"left": "city_id", "right": "city_id"}]},
                },
                {
                    "alias": "co",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "country"},
                    "join": {"to": "c", "type": "left", "on": [{"left": "country_id", "right": "country_id"}]},
                },
            ],
            "primaryKey": "address_id",
            "columns": [
                phys("address_id", "a", "address_id", "bigint", True),
                phys("address", "a", "address", "text", True),
                phys("address2", "a", "address2", "text"),
                phys("district", "a", "district", "text", True),
                phys("city_id", "a", "city_id", "bigint", True),
                phys("postal_code", "a", "postal_code", "text"),
                phys("phone", "a", "phone", "text", True),
                phys("address_last_update", "a", "last_update", "timestamp", True),
                phys("city", "c", "city", "text", True),
                phys("city_country_id", "c", "country_id", "smallint", True),
                phys("city_last_update", "c", "last_update", "timestamp", True),
                phys("country", "co", "country", "text", True),
                phys("country_last_update", "co", "last_update", "timestamp"),
            ],
        }
    )

    write_model(
        {
            "name": "film",
            "source": SOURCE,
            "description": "영화 카탈로그(film, film_text, language 참조). 출연·분류 junction은 film_cast·film_category.",
            "tables": [
                {"alias": "f", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "film"}},
                {
                    "alias": "ft",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "film_text"},
                    "join": {"to": "f", "type": "left", "on": [{"left": "film_id", "right": "film_id"}]},
                },
                {
                    "alias": "lang",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "language"},
                    "join": {"to": "f", "type": "left", "on": [{"left": "language_id", "right": "language_id"}]},
                },
                {
                    "alias": "olang",
                    "priority": 4,
                    "tableReference": {"schema": SCHEMA, "table": "language"},
                    "join": {"to": "f", "type": "left", "on": [{"left": "language_id", "right": "original_language_id"}]},
                },
            ],
            "primaryKey": "film_id",
            "columns": [
                phys("film_id", "f", "film_id", "bigint", True),
                phys("title", "f", "title", "text", True),
                phys("description", "f", "description", "text"),
                phys("release_year", "f", "release_year", "text"),
                phys("language_id", "f", "language_id", "smallint", True),
                phys("original_language_id", "f", "original_language_id", "smallint"),
                phys("rental_duration", "f", "rental_duration", "smallint", True),
                phys("rental_rate", "f", "rental_rate", "numeric", True, precision=4, scale=2),
                phys("length", "f", "length", "smallint"),
                phys("replacement_cost", "f", "replacement_cost", "numeric", True, precision=5, scale=2),
                phys("rating", "f", "rating", "text"),
                phys("special_features", "f", "special_features", "text"),
                phys("last_update", "f", "last_update", "timestamp", True),
                phys("film_text_title", "ft", "title", "text"),
                phys("film_text_description", "ft", "description", "text"),
                phys("language_name", "lang", "name", "text"),
                phys("original_language_name", "olang", "name", "text"),
                rel("language", "language", "film_to_language", "dotted path: film.language"),
                rel(
                    "original_language",
                    "language",
                    "film_to_original_language",
                    "dotted path: film.original_language",
                ),
            ],
        }
    )

    write_model(
        {
            "name": "film_cast",
            "source": SOURCE,
            "description": "영화 출연(film_actor)·film·actor를 join으로 구성.",
            "tables": [
                {"alias": "fa", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "film_actor"}},
                {
                    "alias": "f",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "film"},
                    "join": {"to": "fa", "type": "left", "on": [{"left": "film_id", "right": "film_id"}]},
                },
                {
                    "alias": "a",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "actor"},
                    "join": {"to": "fa", "type": "left", "on": [{"left": "actor_id", "right": "actor_id"}]},
                },
            ],
            "primaryKey": "cast_id",
            "columns": [
                calc("cast_id", "actor_id || ':' || film_id", desc="actor·film 복합 키"),
                phys("actor_id", "fa", "actor_id", "bigint", True),
                phys("film_id", "fa", "film_id", "bigint", True),
                phys("cast_last_update", "fa", "last_update", "timestamp", True),
                phys("film_title", "f", "title", "text"),
                phys("actor_first_name", "a", "first_name", "text"),
                phys("actor_last_name", "a", "last_name", "text"),
                rel("film", "film", "film_cast_to_film"),
                rel("actor", "actor", "film_cast_to_actor"),
            ],
        }
    )

    write_model(
        {
            "name": "film_category",
            "source": SOURCE,
            "description": "영화 분류(film_category)·film·category를 join으로 구성.",
            "tables": [
                {"alias": "fc", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "film_category"}},
                {
                    "alias": "f",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "film"},
                    "join": {"to": "fc", "type": "left", "on": [{"left": "film_id", "right": "film_id"}]},
                },
                {
                    "alias": "cat",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "category"},
                    "join": {"to": "fc", "type": "left", "on": [{"left": "category_id", "right": "category_id"}]},
                },
            ],
            "primaryKey": "link_id",
            "columns": [
                calc("link_id", "film_id || ':' || category_id", desc="film·category 복합 키"),
                phys("film_id", "fc", "film_id", "bigint", True),
                phys("category_id", "fc", "category_id", "smallint", True),
                phys("link_last_update", "fc", "last_update", "timestamp", True),
                phys("film_title", "f", "title", "text"),
                phys("category_name", "cat", "name", "text"),
                rel("film", "film", "film_category_to_film"),
                rel("category", "category", "film_category_to_category"),
            ],
        }
    )

    write_model(
        {
            "name": "category",
            "source": SOURCE,
            "description": "DVD 분류 마스터(category).",
            "tables": [{"alias": "m", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "category"}}],
            "primaryKey": "category_id",
            "columns": [
                phys("category_id", "m", "category_id", "smallint", True),
                phys("name", "m", "name", "text", True),
                phys("last_update", "m", "last_update", "timestamp", True),
            ],
        }
    )

    write_model(
        {
            "name": "language",
            "source": SOURCE,
            "description": "영화 언어 마스터(language).",
            "tables": [{"alias": "m", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "language"}}],
            "primaryKey": "language_id",
            "columns": [
                phys("language_id", "m", "language_id", "smallint", True),
                phys("name", "m", "name", "text", True),
                phys("last_update", "m", "last_update", "timestamp", True),
            ],
        }
    )

    write_model(
        {
            "name": "actor",
            "source": SOURCE,
            "description": "배우 마스터(actor).",
            "tables": [{"alias": "m", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "actor"}}],
            "primaryKey": "actor_id",
            "columns": [
                phys("actor_id", "m", "actor_id", "numeric", True),
                phys("first_name", "m", "first_name", "text", True),
                phys("last_name", "m", "last_name", "text", True),
                phys("last_update", "m", "last_update", "timestamp", True),
            ],
        }
    )

    write_model(
        {
            "name": "customer",
            "source": SOURCE,
            "description": "고객(customer).",
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
                rel("location", "location", "customer_to_location", "dotted path: customer.location"),
                rel("store", "store", "customer_to_store", "dotted path: customer.store"),
            ],
        }
    )

    write_model(
        {
            "name": "employee",
            "source": SOURCE,
            "description": "직원(staff).",
            "tables": [{"alias": "m", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "staff"}}],
            "primaryKey": "staff_id",
            "columns": [
                phys("staff_id", "m", "staff_id", "smallint", True),
                phys("first_name", "m", "first_name", "text", True),
                phys("last_name", "m", "last_name", "text", True),
                phys("address_id", "m", "address_id", "bigint", True),
                phys("picture", "m", "picture", "bytea"),
                phys("email", "m", "email", "text"),
                phys("store_id", "m", "store_id", "bigint", True),
                phys("active", "m", "active", "smallint", True),
                phys("username", "m", "username", "text", True),
                phys("password", "m", "password", "text"),
                phys("last_update", "m", "last_update", "timestamp", True),
                rel("location", "location", "employee_to_location", "dotted path: employee.location"),
                rel("store", "store", "employee_to_store", "dotted path: employee.store"),
            ],
        }
    )

    write_model(
        {
            "name": "store",
            "source": SOURCE,
            "description": "매장(store).",
            "tables": [{"alias": "m", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "store"}}],
            "primaryKey": "store_id",
            "columns": [
                phys("store_id", "m", "store_id", "bigint", True),
                phys("manager_staff_id", "m", "manager_staff_id", "smallint", True),
                phys("address_id", "m", "address_id", "bigint", True),
                phys("last_update", "m", "last_update", "timestamp", True),
                rel("location", "location", "store_to_location", "dotted path: store.location"),
                rel("employee", "employee", "store_to_employee", "dotted path: store.employee"),
            ],
        }
    )

    write_model(
        {
            "name": "inventory",
            "source": SOURCE,
            "description": "매장별 재고(inventory).",
            "tables": [{"alias": "m", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "inventory"}}],
            "primaryKey": "inventory_id",
            "columns": [
                phys("inventory_id", "m", "inventory_id", "bigint", True),
                phys("film_id", "m", "film_id", "bigint", True),
                phys("store_id", "m", "store_id", "bigint", True),
                phys("last_update", "m", "last_update", "timestamp", True),
                rel("film", "film", "inventory_to_film", "dotted path: inventory.film"),
                rel("store", "store", "inventory_to_store", "dotted path: inventory.store"),
            ],
        }
    )

    write_model(
        {
            "name": "rental",
            "source": SOURCE,
            "description": "대여·결제(rental, payment). rental grain, payment 1:1 left join.",
            "tables": [
                {"alias": "r", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "rental"}},
                {
                    "alias": "p",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "payment"},
                    "join": {"to": "r", "type": "left", "on": [{"left": "rental_id", "right": "rental_id"}]},
                },
            ],
            "primaryKey": "rental_id",
            "columns": [
                phys("rental_id", "r", "rental_id", "bigint", True),
                phys("rental_date", "r", "rental_date", "timestamp", True),
                phys("inventory_id", "r", "inventory_id", "bigint", True),
                phys("customer_id", "r", "customer_id", "bigint", True),
                phys("return_date", "r", "return_date", "timestamp"),
                phys("staff_id", "r", "staff_id", "smallint", True),
                phys("rental_last_update", "r", "last_update", "timestamp", True),
                phys("payment_id", "p", "payment_id", "bigint"),
                phys("payment_customer_id", "p", "customer_id", "bigint"),
                phys("payment_staff_id", "p", "staff_id", "smallint"),
                phys("amount", "p", "amount", "numeric", precision=5, scale=2),
                phys("payment_date", "p", "payment_date", "timestamp"),
                phys("payment_last_update", "p", "last_update", "timestamp"),
                rel("customer", "customer", "rental_to_customer", "dotted path: rental.customer"),
                rel("employee", "employee", "rental_to_employee", "dotted path: rental.employee"),
                rel("inventory", "inventory", "rental_to_inventory", "dotted path: rental.inventory"),
            ],
        }
    )

    rels = [
        relationship(
            "customer_to_location",
            "customer",
            "address_id",
            "location",
            "address_id",
            "many_to_one",
            "고객 → 주소(location)",
        ),
        relationship(
            "employee_to_location",
            "employee",
            "address_id",
            "location",
            "address_id",
            "many_to_one",
            "직원 → 주소(location)",
        ),
        relationship(
            "store_to_location",
            "store",
            "address_id",
            "location",
            "address_id",
            "many_to_one",
            "매장 → 주소(location)",
        ),
        relationship(
            "customer_to_store",
            "customer",
            "store_id",
            "store",
            "store_id",
            "many_to_one",
            "고객 → 매장",
        ),
        relationship(
            "employee_to_store",
            "employee",
            "store_id",
            "store",
            "store_id",
            "many_to_one",
            "직원 → 매장",
        ),
        relationship(
            "store_to_employee",
            "store",
            "manager_staff_id",
            "employee",
            "staff_id",
            "many_to_one",
            "매장 → 매니저 직원",
        ),
        relationship(
            "film_to_language",
            "film",
            "language_id",
            "language",
            "language_id",
            "many_to_one",
            "영화 → 언어",
        ),
        relationship(
            "film_to_original_language",
            "film",
            "original_language_id",
            "language",
            "language_id",
            "many_to_one",
            "영화 → 원어",
        ),
        relationship(
            "film_cast_to_film",
            "film_cast",
            "film_id",
            "film",
            "film_id",
            "many_to_one",
            "출연 → 영화",
        ),
        relationship(
            "film_cast_to_actor",
            "film_cast",
            "actor_id",
            "actor",
            "actor_id",
            "many_to_one",
            "출연 → 배우",
        ),
        relationship(
            "film_category_to_film",
            "film_category",
            "film_id",
            "film",
            "film_id",
            "many_to_one",
            "분류 링크 → 영화",
        ),
        relationship(
            "film_category_to_category",
            "film_category",
            "category_id",
            "category",
            "category_id",
            "many_to_one",
            "분류 링크 → category",
        ),
        relationship(
            "inventory_to_film",
            "inventory",
            "film_id",
            "film",
            "film_id",
            "many_to_one",
            "재고 → 영화",
        ),
        relationship(
            "inventory_to_store",
            "inventory",
            "store_id",
            "store",
            "store_id",
            "many_to_one",
            "재고 → 매장",
        ),
        relationship(
            "rental_to_customer",
            "rental",
            "customer_id",
            "customer",
            "customer_id",
            "many_to_one",
            "대여 → 고객",
        ),
        relationship(
            "rental_to_employee",
            "rental",
            "staff_id",
            "employee",
            "staff_id",
            "many_to_one",
            "대여 → 직원",
        ),
        relationship(
            "rental_to_inventory",
            "rental",
            "inventory_id",
            "inventory",
            "inventory_id",
            "many_to_one",
            "대여 → 재고",
        ),
    ]
    for r in rels:
        write_rel(r)

    obsolete = [
        "film_to_actor",
        "actor_to_film",
        "film_to_category",
        "category_to_film",
    ]
    for stem in obsolete:
        p = OUT / f"{stem}.relationship.json"
        if p.exists():
            p.unlink()

    print(f"wrote sqlite-sakila: 11 models, {len(rels)} relationships")


if __name__ == "__main__":
    main()
