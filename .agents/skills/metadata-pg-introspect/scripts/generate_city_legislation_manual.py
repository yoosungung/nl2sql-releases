#!/usr/bin/env python3
"""Consolidated city_legislation metadata (PG introspect + topic merge)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "city_legislation"
SCHEMA = "city_legislation"
SOURCE = "local_postgres"


def phys(name: str, alias: str, col: str, typ: str, not_null: bool = False, desc: str | None = None) -> dict:
    c: dict = {"name": name, "kind": "physical", "type": typ, "from": f"{alias}.{col}"}
    if not_null:
        c["notNull"] = True
    if desc:
        c["description"] = desc
    return c


def calc(name: str, expr: str, typ: str = "text", not_null: bool = True, desc: str | None = None) -> dict:
    c: dict = {"name": name, "kind": "calculated", "type": typ, "expression": expr, "notNull": not_null}
    if desc:
        c["description"] = desc
    return c


def write_model(data: dict) -> None:
    (OUT / f"{data['name']}.model.json").write_text(
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
            "name": "alien",
            "source": SOURCE,
            "description": "외계인 등록 주제. aliens·상세·거주지를 join으로 구성 (alien_data는 동일 주제의 비정규화 테이블).",
            "tables": [
                {
                    "alias": "a",
                    "priority": 1,
                    "tableReference": {"schema": SCHEMA, "table": "aliens"},
                },
                {
                    "alias": "d",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "aliens_details"},
                    "join": {
                        "to": "a",
                        "type": "left",
                        "on": [{"left": "detail_id", "right": "id"}],
                    },
                },
                {
                    "alias": "l",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "aliens_location"},
                    "join": {
                        "to": "a",
                        "type": "left",
                        "on": [{"left": "loc_id", "right": "id"}],
                    },
                },
            ],
            "primaryKey": "alien_id",
            "columns": [
                phys("alien_id", "a", "id", "bigint", not_null=True),
                phys("first_name", "a", "first_name", "text"),
                phys("last_name", "a", "last_name", "text"),
                phys("email", "a", "email", "text"),
                phys("gender", "a", "gender", "text"),
                phys("alien_type", "a", "type", "text", desc="외계인 유형"),
                phys("birth_year", "a", "birth_year", "bigint"),
                phys("favorite_food", "d", "favorite_food", "text"),
                phys("feeding_frequency", "d", "feeding_frequency", "text"),
                phys("aggressive", "d", "aggressive", "bigint"),
                phys("current_location", "l", "current_location", "text"),
                phys("location_state", "l", "state", "text", desc="거주 주/도"),
                phys("location_country", "l", "country", "text"),
                phys("occupation", "l", "occupation", "text"),
            ],
        }
    )

    write_model(
        {
            "name": "city",
            "source": SOURCE,
            "description": "도시·국가·통화·언어 주제. cities를 기준으로 국가·통화·언어 참조를 join.",
            "tables": [
                {
                    "alias": "c",
                    "priority": 1,
                    "tableReference": {"schema": SCHEMA, "table": "cities"},
                },
                {
                    "alias": "ctr",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "cities_countries"},
                    "join": {
                        "to": "c",
                        "type": "left",
                        "on": [{"left": "country_code_2", "right": "country_code_2"}],
                    },
                },
                {
                    "alias": "cur",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "cities_currencies"},
                    "join": {
                        "to": "ctr",
                        "type": "left",
                        "on": [{"left": "country_code_2", "right": "country_code_2"}],
                    },
                },
                {
                    "alias": "lang",
                    "priority": 4,
                    "tableReference": {"schema": SCHEMA, "table": "cities_languages"},
                    "join": {
                        "to": "ctr",
                        "type": "left",
                        "on": [{"left": "country_code_2", "right": "country_code_2"}],
                    },
                },
            ],
            "primaryKey": "city_id",
            "columns": [
                phys("city_id", "c", "city_id", "bigint", not_null=True),
                phys("city_name", "c", "city_name", "text"),
                phys("latitude", "c", "latitude", "double"),
                phys("longitude", "c", "longitude", "double"),
                phys("country_code_2", "c", "country_code_2", "text"),
                phys("capital", "c", "capital", "bigint"),
                phys("population", "c", "population", "double"),
                phys("insert_date", "c", "insert_date", "text"),
                phys("country_id", "ctr", "country_id", "bigint"),
                phys("country_name", "ctr", "country_name", "text"),
                phys("country_code_3", "ctr", "country_code_3", "text"),
                phys("region", "ctr", "region", "text"),
                phys("sub_region", "ctr", "sub_region", "text"),
                phys("intermediate_region", "ctr", "intermediate_region", "text"),
                phys("country_created_on", "ctr", "created_on", "text"),
                phys("currency_id", "cur", "currency_id", "bigint"),
                phys("currency_name", "cur", "currency_name", "text"),
                phys("currency_code", "cur", "currency_code", "text"),
                phys("language_id", "lang", "language_id", "bigint"),
                phys("language", "lang", "language", "text"),
            ],
        }
    )

    write_model(
        {
            "name": "job_posting",
            "source": SOURCE,
            "description": "채용 공고 주제. job_postings_fact·회사·스킬 junction·스킬 차원을 join.",
            "tables": [
                {
                    "alias": "j",
                    "priority": 1,
                    "tableReference": {"schema": SCHEMA, "table": "job_postings_fact"},
                },
                {
                    "alias": "co",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "job_company"},
                    "join": {
                        "to": "j",
                        "type": "left",
                        "on": [{"left": "company_id", "right": "company_id"}],
                    },
                },
                {
                    "alias": "sj",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "skills_job_dim"},
                    "join": {
                        "to": "j",
                        "type": "left",
                        "on": [{"left": "job_id", "right": "job_id"}],
                    },
                },
                {
                    "alias": "sk",
                    "priority": 4,
                    "tableReference": {"schema": SCHEMA, "table": "skills_dim"},
                    "join": {
                        "to": "sj",
                        "type": "left",
                        "on": [{"left": "skill_id", "right": "skill_id"}],
                    },
                },
            ],
            "primaryKey": "job_id",
            "columns": [
                phys("job_id", "j", "job_id", "bigint", not_null=True),
                phys("company_id", "j", "company_id", "bigint"),
                phys("job_title_short", "j", "job_title_short", "text"),
                phys("job_title", "j", "job_title", "text"),
                phys("job_location", "j", "job_location", "text"),
                phys("job_via", "j", "job_via", "text"),
                phys("job_schedule_type", "j", "job_schedule_type", "text"),
                phys("job_work_from_home", "j", "job_work_from_home", "bigint"),
                phys("search_location", "j", "search_location", "text"),
                phys("job_posted_date", "j", "job_posted_date", "text"),
                phys("job_no_degree_mention", "j", "job_no_degree_mention", "bigint"),
                phys("job_health_insurance", "j", "job_health_insurance", "bigint"),
                phys("job_country", "j", "job_country", "text"),
                phys("salary_rate", "j", "salary_rate", "text"),
                phys("salary_year_avg", "j", "salary_year_avg", "double"),
                phys("salary_hour_avg", "j", "salary_hour_avg", "double"),
                phys("company_name", "co", "name", "text"),
                phys("company_link", "co", "link", "text"),
                phys("company_link_google", "co", "link_google", "text"),
                phys("skill_id", "sj", "skill_id", "bigint"),
                phys("skill_name", "sk", "skills", "text"),
                phys("skill_type", "sk", "type", "text"),
            ],
        }
    )

    write_model(
        {
            "name": "legislator",
            "source": SOURCE,
            "description": "의원·임기 주제. legislators_terms를 기준으로 의원 프로필·임기 시작일 차원을 join.",
            "tables": [
                {
                    "alias": "t",
                    "priority": 1,
                    "tableReference": {"schema": SCHEMA, "table": "legislators_terms"},
                },
                {
                    "alias": "l",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "legislators"},
                    "join": {
                        "to": "t",
                        "type": "left",
                        "on": [{"left": "id_bioguide", "right": "id_bioguide"}],
                    },
                },
                {
                    "alias": "dd",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "legislation_date_dim"},
                    "join": {
                        "to": "t",
                        "type": "left",
                        "on": [{"left": "date", "right": "term_start"}],
                    },
                },
            ],
            "primaryKey": "term_id",
            "columns": [
                phys("term_id", "t", "term_id", "text", not_null=True),
                phys("id_bioguide", "t", "id_bioguide", "text"),
                phys("term_number", "t", "term_number", "bigint"),
                phys("term_type", "t", "term_type", "text"),
                phys("term_start", "t", "term_start", "text"),
                phys("term_end", "t", "term_end", "text"),
                phys("term_state", "t", "state", "text", desc="임기 주/도"),
                phys("district", "t", "district", "double"),
                phys("term_class", "t", "class", "double"),
                phys("party", "t", "party", "text"),
                phys("how", "t", "how", "text"),
                phys("term_url", "t", "url", "text"),
                phys("address", "t", "address", "text"),
                phys("phone", "t", "phone", "text"),
                phys("fax", "t", "fax", "text"),
                phys("contact_form", "t", "contact_form", "text"),
                phys("office", "t", "office", "text"),
                phys("state_rank", "t", "state_rank", "text"),
                phys("rss_url", "t", "rss_url", "text"),
                phys("caucus", "t", "caucus", "text"),
                phys("full_name", "l", "full_name", "text"),
                phys("first_name", "l", "first_name", "text"),
                phys("last_name", "l", "last_name", "text"),
                phys("middle_name", "l", "middle_name", "text"),
                phys("nickname", "l", "nickname", "text"),
                phys("suffix", "l", "suffix", "text"),
                phys("other_names_end", "l", "other_names_end", "text"),
                phys("other_names_middle", "l", "other_names_middle", "double"),
                phys("other_names_last", "l", "other_names_last", "text"),
                phys("birthday", "l", "birthday", "text"),
                phys("gender", "l", "gender", "text"),
                phys("leg_id_bioguide", "l", "id_bioguide", "text", desc="의원 Bioguide ID"),
                phys("id_bioguide_previous_0", "l", "id_bioguide_previous_0", "text"),
                phys("id_govtrack", "l", "id_govtrack", "bigint"),
                phys("id_icpsr", "l", "id_icpsr", "double"),
                phys("id_wikipedia", "l", "id_wikipedia", "text"),
                phys("id_wikidata", "l", "id_wikidata", "text"),
                phys("id_google_entity_id", "l", "id_google_entity_id", "text"),
                phys("id_house_history", "l", "id_house_history", "double"),
                phys("id_house_history_alternate", "l", "id_house_history_alternate", "double"),
                phys("id_thomas", "l", "id_thomas", "double"),
                phys("id_cspan", "l", "id_cspan", "double"),
                phys("id_votesmart", "l", "id_votesmart", "double"),
                phys("id_lis", "l", "id_lis", "text"),
                phys("id_ballotpedia", "l", "id_ballotpedia", "text"),
                phys("id_opensecrets", "l", "id_opensecrets", "text"),
                phys("id_fec_0", "l", "id_fec_0", "text"),
                phys("id_fec_1", "l", "id_fec_1", "text"),
                phys("id_fec_2", "l", "id_fec_2", "text"),
                phys("term_start_month_name", "dd", "month_name", "text"),
                phys("term_start_day_of_month", "dd", "day_of_month", "bigint"),
            ],
        }
    )

    print(f"Wrote 4 models under {OUT}")


if __name__ == "__main__":
    main()
