#!/usr/bin/env python3
"""One-off: write manually consolidated f1/*.model.json and *.relationship.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "f1"
SCHEMA = "f1"
SOURCE = "local_postgres"


def mdl_type(pg: str) -> str:
    if pg in ("double precision", "float8"):
        return "double"
    if pg in ("bigint", "int8"):
        return "bigint"
    if pg == "date":
        return "date"
    return "text"


def phys_row(row: tuple) -> dict:
    name, alias, col, pg = row[:4]
    not_null = row[4] if len(row) > 4 else False
    return phys(name, alias, col, pg, not_null)


def phys(name: str, alias: str, col: str, pg: str, not_null: bool = False, desc: str | None = None) -> dict:
    c = {"name": name, "kind": "physical", "type": mdl_type(pg), "from": f"{alias}.{col}"}
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


def relationship(stem: str, from_model: str, from_col: str, to_model: str, to_col: str, desc: str) -> dict:
    return {
        "name": stem,
        "joinType": "many_to_one",
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
            "name": "circuit",
            "source": SOURCE,
            "description": "서킷 주제. circuits·circuits_ext를 join으로 구성.",
            "tables": [
                {"alias": "c", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "circuits"}},
                {
                    "alias": "ce",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "circuits_ext"},
                    "join": {"to": "c", "type": "left", "on": [{"left": "circuit_id", "right": "circuit_id"}]},
                },
            ],
            "primaryKey": "circuit_id",
            "columns": [
                phys("circuit_id", "c", "circuit_id", "bigint", True),
                phys("circuit_ref", "c", "circuit_ref", "text", True),
                phys("name", "c", "name", "text", True),
                phys("location", "c", "location", "text"),
                phys("country", "c", "country", "text"),
                phys("lat", "c", "lat", "double precision"),
                phys("lng", "c", "lng", "double precision"),
                phys("alt", "c", "alt", "bigint"),
                phys("url", "c", "url", "text", True),
                phys("last_race_year", "ce", "last_race_year", "text"),
                phys("number_of_races", "ce", "number_of_races", "text"),
            ],
        }
    )

    write_model(
        {
            "name": "driver",
            "source": SOURCE,
            "description": "드라이버 주제. drivers·drivers_ext를 join으로 구성.",
            "tables": [
                {"alias": "d", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "drivers"}},
                {
                    "alias": "de",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "drivers_ext"},
                    "join": {"to": "d", "type": "left", "on": [{"left": "driver_id", "right": "driver_id"}]},
                },
            ],
            "primaryKey": "driver_id",
            "columns": [
                phys("driver_id", "d", "driver_id", "bigint", True),
                phys("driver_ref", "d", "driver_ref", "text", True),
                phys("number", "d", "number", "bigint"),
                phys("code", "d", "code", "text"),
                phys("forename", "d", "forename", "text", True),
                phys("surname", "d", "surname", "text", True),
                phys("dob", "d", "dob", "date"),
                phys("nationality", "d", "nationality", "text"),
                phys("url", "d", "url", "text", True),
                phys("full_name", "de", "full_name", "text"),
            ],
        }
    )

    write_model(
        {
            "name": "constructor",
            "source": SOURCE,
            "description": "컨스트럭터 주제. constructors·ext·짧은 이름 lookup을 join으로 구성.",
            "tables": [
                {"alias": "c", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "constructors"}},
                {
                    "alias": "ce",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "constructors_ext"},
                    "join": {"to": "c", "type": "left", "on": [{"left": "constructor_id", "right": "constructor_id"}]},
                },
                {
                    "alias": "scn",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "short_constructor_names"},
                    "join": {"to": "c", "type": "left", "on": [{"left": "constructor_ref", "right": "constructor_ref"}]},
                },
            ],
            "primaryKey": "constructor_id",
            "columns": [
                phys("constructor_id", "c", "constructor_id", "bigint", True),
                phys("constructor_ref", "c", "constructor_ref", "text", True),
                phys("name", "c", "name", "text", True),
                phys("nationality", "c", "nationality", "text"),
                phys("url", "c", "url", "text", True),
                phys("short_name_ext", "ce", "short_name", "text"),
                phys("short_name_lookup", "scn", "short_name", "text"),
            ],
        }
    )

    write_model(
        {
            "name": "race",
            "source": SOURCE,
            "description": "레이스 주제. races·races_ext·GP 짧은 이름 lookup을 join으로 구성.",
            "tables": [
                {"alias": "r", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "races"}},
                {
                    "alias": "re",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "races_ext"},
                    "join": {"to": "r", "type": "left", "on": [{"left": "race_id", "right": "race_id"}]},
                },
                {
                    "alias": "sgp",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "short_grand_prix_names"},
                    "join": {"to": "r", "type": "left", "on": [{"left": "full_name", "right": "name"}]},
                },
            ],
            "primaryKey": "race_id",
            "columns": [
                phys("race_id", "r", "race_id", "bigint", True),
                phys("year", "r", "year", "bigint", True),
                phys("round", "r", "round", "bigint", True),
                phys("circuit_id", "r", "circuit_id", "bigint", True),
                phys("name", "r", "name", "text", True),
                phys("date", "r", "date", "date", True),
                phys("time", "r", "time", "text"),
                phys("url", "r", "url", "text"),
                phys("fp1_date", "r", "fp1_date", "text"),
                phys("fp1_time", "r", "fp1_time", "text"),
                phys("fp2_date", "r", "fp2_date", "text"),
                phys("fp2_time", "r", "fp2_time", "text"),
                phys("fp3_date", "r", "fp3_date", "text"),
                phys("fp3_time", "r", "fp3_time", "text"),
                phys("quali_date", "r", "quali_date", "text"),
                phys("quali_time", "r", "quali_time", "text"),
                phys("sprint_date", "r", "sprint_date", "text"),
                phys("sprint_time", "r", "sprint_time", "text"),
                phys("is_pit_data_available", "re", "is_pit_data_available", "text"),
                phys("short_name", "re", "short_name", "text"),
                phys("has_sprint", "re", "has_sprint", "text"),
                phys("max_points", "re", "max_points", "text"),
                phys("grand_prix_short_name", "sgp", "short_name", "text"),
                rel("circuit", "circuit", "race_to_circuit"),
                rel("season", "season", "race_to_season"),
            ],
        }
    )

    write_model(
        {
            "name": "season",
            "source": SOURCE,
            "description": "시즌(연도) 참조.",
            "tables": [{"alias": "s", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "seasons"}}],
            "primaryKey": "year",
            "columns": [
                phys("year", "s", "year", "bigint", True),
                phys("url", "s", "url", "text", True),
            ],
        }
    )

    write_model(
        {
            "name": "status",
            "source": SOURCE,
            "description": "결과·리타이어 상태 코드 참조.",
            "tables": [{"alias": "s", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "status"}}],
            "primaryKey": "status_id",
            "columns": [
                phys("status_id", "s", "status_id", "bigint", True),
                phys("status", "s", "status", "text", True),
            ],
        }
    )

    result_cols = [
        ("result_id", "m", "result_id", "bigint", True),
        ("race_id", "m", "race_id", "bigint", True),
        ("driver_id", "m", "driver_id", "bigint", True),
        ("constructor_id", "m", "constructor_id", "bigint", True),
        ("number", "m", "number", "bigint"),
        ("grid", "m", "grid", "bigint", True),
        ("position", "m", "position", "bigint"),
        ("position_text", "m", "position_text", "text", True),
        ("position_order", "m", "position_order", "bigint", True),
        ("points", "m", "points", "double precision", True),
        ("laps", "m", "laps", "bigint", True),
        ("time", "m", "time", "text"),
        ("milliseconds", "m", "milliseconds", "bigint"),
        ("fastest_lap", "m", "fastest_lap", "bigint"),
        ("rank", "m", "rank", "bigint"),
        ("fastest_lap_time", "m", "fastest_lap_time", "text"),
        ("fastest_lap_speed", "m", "fastest_lap_speed", "text"),
        ("status_id", "m", "status_id", "bigint", True),
    ]
    for topic, table, pk, desc in [
        ("result", "results", "result_id", "그랑프리 본 레이스 결과."),
        ("qualifying", "qualifying", "qualify_id", "예선 결과."),
        ("sprint_result", "sprint_results", "result_id", "스프린트 레이스 결과."),
    ]:
        if topic == "qualifying":
            cols = [
                phys("qualify_id", "m", "qualify_id", "bigint", True),
                phys("race_id", "m", "race_id", "bigint", True),
                phys("driver_id", "m", "driver_id", "bigint", True),
                phys("constructor_id", "m", "constructor_id", "bigint", True),
                phys("number", "m", "number", "bigint", True),
                phys("position", "m", "position", "bigint"),
                phys("q1", "m", "q1", "text"),
                phys("q2", "m", "q2", "text"),
                phys("q3", "m", "q3", "text"),
                rel("race", "race", f"{topic}_to_race"),
                rel("driver", "driver", f"{topic}_to_driver"),
                rel("constructor", "constructor", f"{topic}_to_constructor"),
            ]
        elif topic == "sprint_result":
            cols = [phys_row(r) for r in result_cols] + [
                rel("race", "race", f"{topic}_to_race"),
                rel("driver", "driver", f"{topic}_to_driver"),
                rel("constructor", "constructor", f"{topic}_to_constructor"),
                rel("status", "status", f"{topic}_to_status"),
            ]
        else:
            cols = [phys_row(r) for r in result_cols] + [
                rel("race", "race", f"{topic}_to_race"),
                rel("driver", "driver", f"{topic}_to_driver"),
                rel("constructor", "constructor", f"{topic}_to_constructor"),
                rel("status", "status", f"{topic}_to_status"),
            ]
        write_model(
            {
                "name": topic,
                "source": SOURCE,
                "description": desc,
                "tables": [{"alias": "m", "priority": 1, "tableReference": {"schema": SCHEMA, "table": table}}],
                "primaryKey": pk,
                "columns": cols,
            }
        )

    write_model(
        {
            "name": "lap",
            "source": SOURCE,
            "description": "랩 타임·위치·레이스별 랩 통계 주제. lap_times를 grain으로 ext·positions·stats를 join.",
            "tables": [
                {"alias": "lt", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "lap_times"}},
                {
                    "alias": "lte",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "lap_times_ext"},
                    "join": {
                        "to": "lt",
                        "type": "left",
                        "on": [
                            {"left": "race_id", "right": "race_id"},
                            {"left": "driver_id", "right": "driver_id"},
                            {"left": "lap", "right": "lap"},
                        ],
                    },
                },
                {
                    "alias": "lp",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "lap_positions"},
                    "join": {
                        "to": "lt",
                        "type": "left",
                        "on": [
                            {"left": "race_id", "right": "race_id"},
                            {"left": "driver_id", "right": "driver_id"},
                            {"left": "lap", "right": "lap"},
                        ],
                    },
                },
                {
                    "alias": "lts",
                    "priority": 4,
                    "tableReference": {"schema": SCHEMA, "table": "lap_time_stats"},
                    "join": {
                        "to": "lt",
                        "type": "left",
                        "on": [
                            {"left": "race_id", "right": "race_id"},
                            {"left": "driver_id", "right": "driver_id"},
                        ],
                    },
                },
            ],
            "primaryKey": "id",
            "columns": [
                calc("id", "race_id || ':' || driver_id || ':' || lap", desc="race·driver·lap 복합 키"),
                phys("race_id", "lt", "race_id", "bigint", True),
                phys("driver_id", "lt", "driver_id", "bigint", True),
                phys("lap", "lt", "lap", "bigint", True),
                phys("position", "lt", "position", "bigint"),
                phys("time", "lt", "time", "text"),
                phys("milliseconds", "lt", "milliseconds", "bigint"),
                phys("seconds", "lte", "seconds", "double precision"),
                phys("running_milliseconds", "lte", "running_milliseconds", "text"),
                phys("lap_position", "lp", "position", "bigint"),
                phys("lap_type", "lp", "lap_type", "text"),
                phys("avg_milliseconds", "lts", "avg_milliseconds", "text"),
                phys("avg_seconds", "lts", "avg_seconds", "text"),
                phys("stdev_milliseconds", "lts", "stdev_milliseconds", "text"),
                phys("stdev_seconds", "lts", "stdev_seconds", "text"),
                rel("race", "race", "lap_to_race"),
                rel("driver", "driver", "lap_to_driver"),
            ],
        }
    )

    write_model(
        {
            "name": "pit_stop",
            "source": SOURCE,
            "description": "피트스톱 이벤트(레이스·드라이버·스톱 순).",
            "tables": [{"alias": "ps", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "pit_stops"}}],
            "primaryKey": "id",
            "columns": [
                calc("id", "race_id || ':' || driver_id || ':' || stop", desc="race·driver·stop 복합 키"),
                phys("race_id", "ps", "race_id", "bigint", True),
                phys("driver_id", "ps", "driver_id", "bigint", True),
                phys("stop", "ps", "stop", "bigint", True),
                phys("lap", "ps", "lap", "bigint", True),
                phys("time", "ps", "time", "text", True),
                phys("duration", "ps", "duration", "text"),
                phys("milliseconds", "ps", "milliseconds", "bigint"),
                rel("race", "race", "pit_stop_to_race"),
                rel("driver", "driver", "pit_stop_to_driver"),
            ],
        }
    )

    write_model(
        {
            "name": "retirement",
            "source": SOURCE,
            "description": "리타이어·DNF 이벤트.",
            "tables": [{"alias": "r", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "retirements"}}],
            "primaryKey": "id",
            "columns": [
                calc(
                    "id",
                    "coalesce(race_id::text,'') || ':' || coalesce(driver_id::text,'') || ':' || coalesce(lap,'')",
                    desc="race·driver·lap 복합 키(물리 PK 없음)",
                ),
                phys("race_id", "r", "race_id", "bigint"),
                phys("driver_id", "r", "driver_id", "bigint"),
                phys("lap", "r", "lap", "text"),
                phys("position_order", "r", "position_order", "bigint"),
                phys("status_id", "r", "status_id", "bigint"),
                phys("retirement_type", "r", "retirement_type", "text"),
                rel("race", "race", "retirement_to_race"),
                rel("driver", "driver", "retirement_to_driver"),
                rel("status", "status", "retirement_to_status"),
            ],
        }
    )

    write_model(
        {
            "name": "drive",
            "source": SOURCE,
            "description": "시즌·드라이버·컨스트럭터 소속(드라이브) 구간.",
            "tables": [{"alias": "d", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "drives"}}],
            "primaryKey": "id",
            "columns": [
                calc(
                    "id",
                    "year || ':' || driver_id || ':' || constructor_id || ':' || first_round",
                    desc="시즌·드라이버·팀·시작 라운드 복합 키",
                ),
                phys("drive_id", "d", "drive_id", "text"),
                phys("year", "d", "year", "bigint"),
                phys("driver_id", "d", "driver_id", "bigint"),
                phys("constructor_id", "d", "constructor_id", "bigint"),
                phys("first_round", "d", "first_round", "bigint"),
                phys("last_round", "d", "last_round", "bigint"),
                phys("is_first_drive_of_season", "d", "is_first_drive_of_season", "text"),
                phys("is_final_drive_of_season", "d", "is_final_drive_of_season", "text"),
                rel("driver", "driver", "drive_to_driver"),
                rel("constructor", "constructor", "drive_to_constructor"),
                rel("season", "season", "drive_to_season"),
            ],
        }
    )

    write_model(
        {
            "name": "driver_standing",
            "source": SOURCE,
            "description": "드라이버 챔피언십 순위(레이스 시점). standings·ext를 join.",
            "tables": [
                {"alias": "ds", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "driver_standings"}},
                {
                    "alias": "dse",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "driver_standings_ext"},
                    "join": {
                        "to": "ds",
                        "type": "left",
                        "on": [{"left": "driver_standings_id", "right": "driver_standings_id"}],
                    },
                },
            ],
            "primaryKey": "driver_standings_id",
            "columns": [
                phys("driver_standings_id", "ds", "driver_standings_id", "bigint", True),
                phys("race_id", "ds", "race_id", "bigint", True),
                phys("driver_id", "ds", "driver_id", "bigint", True),
                phys("points", "ds", "points", "double precision", True),
                phys("position", "ds", "position", "bigint"),
                phys("position_text", "ds", "position_text", "text"),
                phys("wins", "ds", "wins", "bigint", True),
                rel("race", "race", "driver_standing_to_race"),
                rel("driver", "driver", "driver_standing_to_driver"),
            ],
        }
    )

    write_model(
        {
            "name": "constructor_standing",
            "source": SOURCE,
            "description": "컨스트럭터 챔피언십·레이스별 팀 점수. standings·results를 race·constructor로 join.",
            "tables": [
                {
                    "alias": "cs",
                    "priority": 1,
                    "tableReference": {"schema": SCHEMA, "table": "constructor_standings"},
                },
                {
                    "alias": "cr",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "constructor_results"},
                    "join": {
                        "to": "cs",
                        "type": "left",
                        "on": [
                            {"left": "race_id", "right": "race_id"},
                            {"left": "constructor_id", "right": "constructor_id"},
                        ],
                    },
                },
            ],
            "primaryKey": "constructor_standings_id",
            "columns": [
                phys("constructor_standings_id", "cs", "constructor_standings_id", "bigint", True),
                phys("race_id", "cs", "race_id", "bigint", True),
                phys("constructor_id", "cs", "constructor_id", "bigint", True),
                phys("standing_points", "cs", "points", "double precision", True),
                phys("standing_position", "cs", "position", "bigint"),
                phys("standing_position_text", "cs", "position_text", "text"),
                phys("standing_wins", "cs", "wins", "bigint", True),
                phys("constructor_results_id", "cr", "constructor_results_id", "bigint"),
                phys("race_result_points", "cr", "points", "double precision"),
                phys("race_result_status", "cr", "status", "text"),
                rel("race", "race", "constructor_standing_to_race"),
                rel("constructor", "constructor", "constructor_standing_to_constructor"),
            ],
        }
    )

    write_model(
        {
            "name": "livery",
            "source": SOURCE,
            "description": "팀 리버리(컬러) 기간별 lookup.",
            "tables": [{"alias": "l", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "liveries"}}],
            "primaryKey": "id",
            "columns": [
                calc("id", "constructor_ref || ':' || start_year || ':' || end_year"),
                phys("constructor_ref", "l", "constructor_ref", "text", True),
                phys("start_year", "l", "start_year", "bigint", True),
                phys("end_year", "l", "end_year", "bigint", True),
                phys("primary_hex_code", "l", "primary_hex_code", "text", True),
                rel("constructor", "constructor", "livery_to_constructor"),
            ],
        }
    )

    write_model(
        {
            "name": "team_driver_rank",
            "source": SOURCE,
            "description": "팀 내 드라이버 순위(시즌·팀·드라이버).",
            "tables": [
                {"alias": "t", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "team_driver_ranks"}}
            ],
            "primaryKey": "id",
            "columns": [
                calc("id", "year || ':' || constructor_id || ':' || driver_id"),
                phys("year", "t", "year", "bigint"),
                phys("constructor_id", "t", "constructor_id", "bigint"),
                phys("constructor_ref", "t", "constructor_ref", "text"),
                phys("driver_id", "t", "driver_id", "bigint"),
                phys("driver_ref", "t", "driver_ref", "text"),
                phys("team_driver_rank", "t", "team_driver_rank", "text"),
                rel("season", "season", "team_driver_rank_to_season"),
                rel("constructor", "constructor", "team_driver_rank_to_constructor"),
                rel("driver", "driver", "team_driver_rank_to_driver"),
            ],
        }
    )

    write_model(
        {
            "name": "tdr_override",
            "source": SOURCE,
            "description": "팀 드라이버 순위 수동 override(ref 기준).",
            "tables": [{"alias": "o", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "tdr_overrides"}}],
            "primaryKey": "id",
            "columns": [
                calc("id", "year || ':' || constructor_ref || ':' || driver_ref"),
                phys("year", "o", "year", "bigint", True),
                phys("constructor_ref", "o", "constructor_ref", "text", True),
                phys("driver_ref", "o", "driver_ref", "text", True),
                phys("team_driver_rank", "o", "team_driver_rank", "bigint"),
                rel("season", "season", "tdr_override_to_season"),
                rel("constructor", "constructor", "tdr_override_to_constructor"),
                rel("driver", "driver", "tdr_override_to_driver"),
            ],
        }
    )

    rels = [
        ("race_to_circuit", "race", "circuit_id", "circuit", "circuit_id", "race → circuit"),
        ("race_to_season", "race", "year", "season", "year", "race → season"),
        ("result_to_race", "result", "race_id", "race", "race_id", "result → race"),
        ("result_to_driver", "result", "driver_id", "driver", "driver_id", "result → driver"),
        ("result_to_constructor", "result", "constructor_id", "constructor", "constructor_id", "result → constructor"),
        ("result_to_status", "result", "status_id", "status", "status_id", "result → status"),
        ("qualifying_to_race", "qualifying", "race_id", "race", "race_id", "qualifying → race"),
        ("qualifying_to_driver", "qualifying", "driver_id", "driver", "driver_id", "qualifying → driver"),
        (
            "qualifying_to_constructor",
            "qualifying",
            "constructor_id",
            "constructor",
            "constructor_id",
            "qualifying → constructor",
        ),
        ("sprint_result_to_race", "sprint_result", "race_id", "race", "race_id", "sprint_result → race"),
        ("sprint_result_to_driver", "sprint_result", "driver_id", "driver", "driver_id", "sprint_result → driver"),
        (
            "sprint_result_to_constructor",
            "sprint_result",
            "constructor_id",
            "constructor",
            "constructor_id",
            "sprint_result → constructor",
        ),
        ("sprint_result_to_status", "sprint_result", "status_id", "status", "status_id", "sprint_result → status"),
        ("lap_to_race", "lap", "race_id", "race", "race_id", "lap → race"),
        ("lap_to_driver", "lap", "driver_id", "driver", "driver_id", "lap → driver"),
        ("pit_stop_to_race", "pit_stop", "race_id", "race", "race_id", "pit_stop → race"),
        ("pit_stop_to_driver", "pit_stop", "driver_id", "driver", "driver_id", "pit_stop → driver"),
        ("retirement_to_race", "retirement", "race_id", "race", "race_id", "retirement → race"),
        ("retirement_to_driver", "retirement", "driver_id", "driver", "driver_id", "retirement → driver"),
        ("retirement_to_status", "retirement", "status_id", "status", "status_id", "retirement → status"),
        ("drive_to_driver", "drive", "driver_id", "driver", "driver_id", "drive → driver"),
        ("drive_to_constructor", "drive", "constructor_id", "constructor", "constructor_id", "drive → constructor"),
        ("drive_to_season", "drive", "year", "season", "year", "drive → season"),
        ("driver_standing_to_race", "driver_standing", "race_id", "race", "race_id", "driver_standing → race"),
        ("driver_standing_to_driver", "driver_standing", "driver_id", "driver", "driver_id", "driver_standing → driver"),
        (
            "constructor_standing_to_race",
            "constructor_standing",
            "race_id",
            "race",
            "race_id",
            "constructor_standing → race",
        ),
        (
            "constructor_standing_to_constructor",
            "constructor_standing",
            "constructor_id",
            "constructor",
            "constructor_id",
            "constructor_standing → constructor",
        ),
        ("livery_to_constructor", "livery", "constructor_ref", "constructor", "constructor_ref", "livery → constructor"),
        ("team_driver_rank_to_season", "team_driver_rank", "year", "season", "year", "team_driver_rank → season"),
        (
            "team_driver_rank_to_constructor",
            "team_driver_rank",
            "constructor_id",
            "constructor",
            "constructor_id",
            "team_driver_rank → constructor",
        ),
        ("team_driver_rank_to_driver", "team_driver_rank", "driver_id", "driver", "driver_id", "team_driver_rank → driver"),
        ("tdr_override_to_season", "tdr_override", "year", "season", "year", "tdr_override → season"),
        (
            "tdr_override_to_constructor",
            "tdr_override",
            "constructor_ref",
            "constructor",
            "constructor_ref",
            "tdr_override → constructor",
        ),
        ("tdr_override_to_driver", "tdr_override", "driver_ref", "driver", "driver_ref", "tdr_override → driver"),
    ]
    for stem, fm, fc, tm, tc, desc in rels:
        write_rel(relationship(stem, fm, fc, tm, tc, desc))

    models = len(list(OUT.glob("*.model.json")))
    rels_n = len(list(OUT.glob("*.relationship.json")))
    print(f"wrote {models} models, {rels_n} relationships under {OUT}")


if __name__ == "__main__":
    main()
