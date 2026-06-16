#!/usr/bin/env python3
"""Manually consolidated education_business metadata."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "education_business"
SCHEMA = "education_business"
SOURCE = "local_postgres"


def phys(name: str, alias: str, col: str, typ: str, not_null: bool = False) -> dict:
    c = {"name": name, "kind": "physical", "type": typ, "from": f"{alias}.{col}"}
    if not_null:
        c["notNull"] = True
    return c


def calc(name: str, expr: str, typ: str = "text", not_null: bool = True, desc: str | None = None) -> dict:
    c = {"name": name, "kind": "calculated", "type": typ, "expression": expr, "notNull": not_null}
    if desc:
        c["description"] = desc
    return c


def rel(name: str, to: str, via: str) -> dict:
    return {"name": name, "kind": "relation", "to": to, "via": via}


def relationship(stem: str, fm: str, fc: str, tm: str, tc: str, desc: str) -> dict:
    return {
        "name": stem,
        "joinType": "many_to_one",
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
            "name": "hardware_sale",
            "source": SOURCE,
            "description": "하드웨어 판매 주제. 월별 판매 fact·제품·고객·가격·원가·할인을 join으로 구성.",
            "tables": [
                {
                    "alias": "s",
                    "priority": 1,
                    "tableReference": {"schema": SCHEMA, "table": "hardware_fact_sales_monthly"},
                },
                {
                    "alias": "p",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "hardware_dim_product"},
                    "join": {"to": "s", "type": "left", "on": [{"left": "product_code", "right": "product_code"}]},
                },
                {
                    "alias": "c",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "hardware_dim_customer"},
                    "join": {"to": "s", "type": "left", "on": [{"left": "customer_code", "right": "customer_code"}]},
                },
                {
                    "alias": "gp",
                    "priority": 4,
                    "tableReference": {"schema": SCHEMA, "table": "hardware_fact_gross_price"},
                    "join": {
                        "to": "s",
                        "type": "left",
                        "on": [
                            {"left": "product_code", "right": "product_code"},
                            {"left": "fiscal_year", "right": "fiscal_year"},
                        ],
                    },
                },
                {
                    "alias": "mc",
                    "priority": 5,
                    "tableReference": {"schema": SCHEMA, "table": "hardware_fact_manufacturing_cost"},
                    "join": {
                        "to": "s",
                        "type": "left",
                        "on": [
                            {"left": "product_code", "right": "product_code"},
                            {"left": "cost_year", "right": "fiscal_year"},
                        ],
                    },
                },
                {
                    "alias": "ded",
                    "priority": 6,
                    "tableReference": {"schema": SCHEMA, "table": "hardware_fact_pre_invoice_deductions"},
                    "join": {
                        "to": "s",
                        "type": "left",
                        "on": [
                            {"left": "customer_code", "right": "customer_code"},
                            {"left": "fiscal_year", "right": "fiscal_year"},
                        ],
                    },
                },
            ],
            "primaryKey": "id",
            "columns": [
                calc("id", "product_code || ':' || customer_code || ':' || date", desc="product·customer·date grain"),
                phys("date", "s", "date", "text"),
                phys("product_code", "s", "product_code", "text"),
                phys("customer_code", "s", "customer_code", "bigint"),
                phys("sold_quantity", "s", "sold_quantity", "bigint"),
                phys("fiscal_year", "s", "fiscal_year", "bigint"),
                phys("division", "p", "division", "text"),
                phys("segment", "p", "segment", "text"),
                phys("category", "p", "category", "text"),
                phys("product", "p", "product", "text"),
                phys("variant", "p", "variant", "text"),
                phys("customer", "c", "customer", "text"),
                phys("platform", "c", "platform", "text"),
                phys("channel", "c", "channel", "text"),
                phys("gross_price", "gp", "gross_price", "double"),
                phys("manufacturing_cost", "mc", "manufacturing_cost", "double"),
                phys("pre_invoice_discount_pct", "ded", "pre_invoice_discount_pct", "double"),
            ],
        }
    )

    write_model(
        {
            "name": "course",
            "source": SOURCE,
            "description": "대학 교과목 참조.",
            "tables": [{"alias": "c", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "university_course"}}],
            "primaryKey": "course_no",
            "columns": [
                phys("course_no", "c", "CourseNo", "text"),
                phys("crs_desc", "c", "CrsDesc", "text"),
                phys("crs_units", "c", "CrsUnits", "bigint"),
            ],
        }
    )

    write_model(
        {
            "name": "faculty",
            "source": SOURCE,
            "description": "대학 교수 참조.",
            "tables": [{"alias": "f", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "university_faculty"}}],
            "primaryKey": "fac_no",
            "columns": [
                phys("fac_no", "f", "FacNo", "bigint"),
                phys("fac_first_name", "f", "FacFirstName", "text"),
                phys("fac_last_name", "f", "FacLastName", "text"),
                phys("fac_rank", "f", "FacRank", "text"),
                phys("fac_salary", "f", "FacSalary", "bigint"),
                phys("fac_supervisor", "f", "FacSupervisor", "bigint"),
            ],
        }
    )

    write_model(
        {
            "name": "student",
            "source": SOURCE,
            "description": "대학 학생 참조.",
            "tables": [{"alias": "s", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "university_student"}}],
            "primaryKey": "std_no",
            "columns": [
                phys("std_no", "s", "StdNo", "bigint"),
                phys("std_first_name", "s", "StdFirstName", "text"),
                phys("std_last_name", "s", "StdLastName", "text"),
                phys("std_city", "s", "StdCity", "text"),
                phys("std_state", "s", "StdState", "text"),
                phys("std_zip", "s", "StdZip", "text"),
                phys("std_major", "s", "StdMajor", "text"),
                phys("std_class", "s", "StdClass", "text"),
                phys("std_gpa", "s", "StdGPA", "double"),
            ],
        }
    )

    write_model(
        {
            "name": "offering",
            "source": SOURCE,
            "description": "개설 강좌 주제. offering·course·faculty를 join으로 구성.",
            "tables": [
                {"alias": "o", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "university_offering"}},
                {
                    "alias": "c",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "university_course"},
                    "join": {"to": "o", "type": "left", "on": [{"left": "CourseNo", "right": "CourseNo"}]},
                },
                {
                    "alias": "f",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "university_faculty"},
                    "join": {"to": "o", "type": "left", "on": [{"left": "FacNo", "right": "FacNo"}]},
                },
            ],
            "primaryKey": "offer_no",
            "columns": [
                phys("offer_no", "o", "OfferNo", "bigint"),
                phys("course_no", "o", "CourseNo", "text"),
                phys("off_term", "o", "OffTerm", "text"),
                phys("off_year", "o", "OffYear", "bigint"),
                phys("off_location", "o", "OffLocation", "text"),
                phys("off_time", "o", "OffTime", "text"),
                phys("fac_no", "o", "FacNo", "double"),
                phys("off_days", "o", "OffDays", "text"),
                phys("crs_desc", "c", "CrsDesc", "text"),
                phys("crs_units", "c", "CrsUnits", "bigint"),
                phys("fac_first_name", "f", "FacFirstName", "text"),
                phys("fac_last_name", "f", "FacLastName", "text"),
                rel("course", "course", "offering_to_course"),
                rel("faculty", "faculty", "offering_to_faculty"),
            ],
        }
    )

    write_model(
        {
            "name": "enrollment",
            "source": SOURCE,
            "description": "수강 등록 주제. enrollment·offering·student를 join으로 구성.",
            "tables": [
                {"alias": "e", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "university_enrollment"}},
                {
                    "alias": "o",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "university_offering"},
                    "join": {"to": "e", "type": "left", "on": [{"left": "OfferNo", "right": "OfferNo"}]},
                },
                {
                    "alias": "s",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "university_student"},
                    "join": {"to": "e", "type": "left", "on": [{"left": "StdNo", "right": "StdNo"}]},
                },
            ],
            "primaryKey": "id",
            "columns": [
                calc("id", "offer_no || ':' || std_no", desc="OfferNo·StdNo 복합 키"),
                phys("offer_no", "e", "OfferNo", "bigint"),
                phys("std_no", "e", "StdNo", "bigint"),
                phys("enr_grade", "e", "EnrGrade", "double"),
                phys("course_no", "o", "CourseNo", "text"),
                phys("off_term", "o", "OffTerm", "text"),
                phys("off_year", "o", "OffYear", "bigint"),
                phys("std_first_name", "s", "StdFirstName", "text"),
                phys("std_last_name", "s", "StdLastName", "text"),
                rel("offering", "offering", "enrollment_to_offering"),
                rel("student", "student", "enrollment_to_student"),
            ],
        }
    )

    write_model(
        {
            "name": "web_account",
            "source": SOURCE,
            "description": "웹 CRM 계정 주제. accounts·sales_rep·region을 join으로 구성.",
            "tables": [
                {"alias": "a", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "web_accounts"}},
                {
                    "alias": "r",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "web_sales_reps"},
                    "join": {"to": "a", "type": "left", "on": [{"left": "id", "right": "sales_rep_id"}]},
                },
                {
                    "alias": "g",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "web_region"},
                    "join": {"to": "r", "type": "left", "on": [{"left": "id", "right": "region_id"}]},
                },
            ],
            "primaryKey": "account_id",
            "columns": [
                phys("account_id", "a", "id", "bigint"),
                phys("name", "a", "name", "text"),
                phys("website", "a", "website", "text"),
                phys("lat", "a", "lat", "double"),
                phys("long", "a", "long", "double"),
                phys("primary_poc", "a", "primary_poc", "text"),
                phys("sales_rep_id", "a", "sales_rep_id", "bigint"),
                phys("sales_rep_name", "r", "name", "text"),
                phys("region_name", "g", "name", "text"),
            ],
        }
    )

    write_model(
        {
            "name": "web_order",
            "source": SOURCE,
            "description": "웹 주문 fact.",
            "tables": [{"alias": "o", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "web_orders"}}],
            "primaryKey": "order_id",
            "columns": [
                phys("order_id", "o", "id", "bigint"),
                phys("account_id", "o", "account_id", "bigint"),
                phys("occurred_at", "o", "occurred_at", "text"),
                phys("standard_qty", "o", "standard_qty", "bigint"),
                phys("gloss_qty", "o", "gloss_qty", "bigint"),
                phys("poster_qty", "o", "poster_qty", "bigint"),
                phys("total", "o", "total", "bigint"),
                phys("standard_amt_usd", "o", "standard_amt_usd", "double"),
                phys("gloss_amt_usd", "o", "gloss_amt_usd", "double"),
                phys("poster_amt_usd", "o", "poster_amt_usd", "double"),
                phys("total_amt_usd", "o", "total_amt_usd", "double"),
                rel("web_account", "web_account", "web_order_to_account"),
            ],
        }
    )

    write_model(
        {
            "name": "web_event",
            "source": SOURCE,
            "description": "웹 계정 이벤트 fact.",
            "tables": [{"alias": "e", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "web_events"}}],
            "primaryKey": "event_id",
            "columns": [
                phys("event_id", "e", "id", "bigint"),
                phys("account_id", "e", "account_id", "bigint"),
                phys("occurred_at", "e", "occurred_at", "text"),
                phys("channel", "e", "channel", "text"),
                rel("web_account", "web_account", "web_event_to_account"),
            ],
        }
    )

    write_model(
        {
            "name": "staff_hour",
            "source": SOURCE,
            "description": "직원 근무 시간 로그.",
            "tables": [{"alias": "h", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "StaffHours"}}],
            "primaryKey": "id",
            "columns": [
                calc("id", "staff_member || ':' || event_date || ':' || event_time || ':' || event_type"),
                phys("staff_member", "h", "StaffMember", "text"),
                phys("event_date", "h", "EventDate", "text"),
                phys("event_time", "h", "EventTime", "text"),
                phys("event_type", "h", "EventType", "text"),
            ],
        }
    )

    write_model(
        {
            "name": "salary",
            "source": SOURCE,
            "description": "기업 직무·급여 참고 데이터셋.",
            "tables": [{"alias": "s", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "SalaryDataset"}}],
            "primaryKey": "salary_index",
            "columns": [
                phys("salary_index", "s", "index", "bigint"),
                phys("company_name", "s", "CompanyName", "text"),
                phys("job_title", "s", "JobTitle", "text"),
                phys("salaries_reported", "s", "SalariesReported", "double"),
                phys("location", "s", "Location", "text"),
                phys("salary", "s", "Salary", "text"),
            ],
        }
    )

    rels = [
        ("offering_to_course", "offering", "course_no", "course", "course_no", "offering → course"),
        ("offering_to_faculty", "offering", "fac_no", "faculty", "fac_no", "offering → faculty"),
        ("enrollment_to_offering", "enrollment", "offer_no", "offering", "offer_no", "enrollment → offering"),
        ("enrollment_to_student", "enrollment", "std_no", "student", "std_no", "enrollment → student"),
        ("web_order_to_account", "web_order", "account_id", "web_account", "account_id", "web_order → web_account"),
        ("web_event_to_account", "web_event", "account_id", "web_account", "account_id", "web_event → web_account"),
    ]
    for args in rels:
        write_rel(relationship(*args))

    print(f"wrote {len(list(OUT.glob('*.model.json')))} models, {len(list(OUT.glob('*.relationship.json')))} rels")


if __name__ == "__main__":
    main()
