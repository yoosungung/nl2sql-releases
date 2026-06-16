#!/usr/bin/env python3
"""One-off: manually consolidated eu_soccer metadata."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "eu_soccer"
SCHEMA = "eu_soccer"
SOURCE = "local_postgres"


def mdl_type(pg: str) -> str:
    if pg in ("double precision", "float8"):
        return "double"
    if pg in ("bigint", "int8", "integer", "int4"):
        return "bigint"
    if pg in ("numeric", "decimal"):
        return "decimal"
    if pg == "date":
        return "date"
    return "text"


def sem_name(col: str) -> str:
    if col == col.lower() or not re.search(r"[A-Z]", col):
        return col
    s = re.sub(r"([A-Z])", r"_\1", col).lower().strip("_")
    return s


def phys(name: str, alias: str, col: str, pg: str, not_null: bool = False) -> dict:
    c = {"name": name, "kind": "physical", "type": mdl_type(pg), "from": f"{alias}.{col}"}
    if not_null:
        c["notNull"] = True
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


def fetch_columns(table: str) -> list[tuple[str, str, bool]]:
    url = os.environ.get("MCP_POSTGRES_URL")
    if not url:
        raise SystemExit("MCP_POSTGRES_URL not set")
    sql = f"""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_schema = '{SCHEMA}' AND table_name = '{table}'
    ORDER BY ordinal_position
    """
    out = subprocess.check_output(
        ["psql", url, "-t", "-A", "-F", "\t", "-c", sql],
        text=True,
    )
    rows = []
    for line in out.strip().splitlines():
        if not line.strip():
            continue
        col, dtype, nullable = line.split("\t")
        rows.append((col, dtype, nullable == "NO"))
    return rows


def cols_from_table(
    alias: str,
    table: str,
    rename: dict[str, str] | None = None,
    extra_not_null: set[str] | None = None,
) -> list[dict]:
    rename = rename or {}
    extra_not_null = extra_not_null or set()
    return [
        phys(rename.get(c, sem_name(c)), alias, c, t, nn or c in extra_not_null)
        for c, t, nn in fetch_columns(table)
    ]


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
            "name": "country",
            "source": SOURCE,
            "description": "국가 참조.",
            "tables": [
                {"alias": "c", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "Country"}}
            ],
            "primaryKey": "country_id",
            "columns": [
                phys("country_id", "c", "id", "bigint", True),
                phys("name", "c", "name", "text"),
            ],
        }
    )

    write_model(
        {
            "name": "league",
            "source": SOURCE,
            "description": "리그 주제. League·Country를 join으로 구성.",
            "tables": [
                {"alias": "l", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "League"}},
                {
                    "alias": "c",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "Country"},
                    "join": {"to": "l", "type": "left", "on": [{"left": "id", "right": "country_id"}]},
                },
            ],
            "primaryKey": "league_id",
            "columns": [
                phys("league_id", "l", "id", "bigint", True),
                phys("country_id", "l", "country_id", "bigint"),
                phys("league_name", "l", "name", "text"),
                phys("country_name", "c", "name", "text"),
                rel("country", "country", "league_to_country"),
            ],
        }
    )

    write_model(
        {
            "name": "team",
            "source": SOURCE,
            "description": "팀 주제. Team·시점별 Team_Attributes를 join으로 구성.",
            "tables": [
                {"alias": "t", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "Team"}},
                {
                    "alias": "ta",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "Team_Attributes"},
                    "join": {"to": "t", "type": "left", "on": [{"left": "team_api_id", "right": "team_api_id"}]},
                },
            ],
            "primaryKey": "team_id",
            "columns": [
                phys("team_id", "t", "id", "bigint", True),
                phys("team_api_id", "t", "team_api_id", "bigint"),
                phys("team_fifa_api_id", "t", "team_fifa_api_id", "bigint"),
                phys("team_long_name", "t", "team_long_name", "text"),
                phys("team_short_name", "t", "team_short_name", "text"),
                phys("team_attributes_id", "ta", "id", "bigint"),
                phys("attributes_date", "ta", "date", "text"),
                phys("build_up_play_speed", "ta", "buildUpPlaySpeed", "bigint"),
                phys("build_up_play_speed_class", "ta", "buildUpPlaySpeedClass", "text"),
                phys("build_up_play_dribbling", "ta", "buildUpPlayDribbling", "bigint"),
                phys("build_up_play_dribbling_class", "ta", "buildUpPlayDribblingClass", "text"),
                phys("build_up_play_passing", "ta", "buildUpPlayPassing", "bigint"),
                phys("build_up_play_passing_class", "ta", "buildUpPlayPassingClass", "text"),
                phys("build_up_play_positioning_class", "ta", "buildUpPlayPositioningClass", "text"),
                phys("chance_creation_passing", "ta", "chanceCreationPassing", "bigint"),
                phys("chance_creation_passing_class", "ta", "chanceCreationPassingClass", "text"),
                phys("chance_creation_crossing", "ta", "chanceCreationCrossing", "bigint"),
                phys("chance_creation_crossing_class", "ta", "chanceCreationCrossingClass", "text"),
                phys("chance_creation_shooting", "ta", "chanceCreationShooting", "bigint"),
                phys("chance_creation_shooting_class", "ta", "chanceCreationShootingClass", "text"),
                phys("chance_creation_positioning_class", "ta", "chanceCreationPositioningClass", "text"),
                phys("defence_pressure", "ta", "defencePressure", "bigint"),
                phys("defence_pressure_class", "ta", "defencePressureClass", "text"),
                phys("defence_aggression", "ta", "defenceAggression", "bigint"),
                phys("defence_aggression_class", "ta", "defenceAggressionClass", "text"),
                phys("defence_team_width", "ta", "defenceTeamWidth", "bigint"),
                phys("defence_team_width_class", "ta", "defenceTeamWidthClass", "text"),
                phys("defence_defender_line_class", "ta", "defenceDefenderLineClass", "text"),
            ],
        }
    )

    pa_cols = [
        ("player_attributes_id", "pa", "id", "bigint", True),
        ("player_fifa_api_id", "pa", "player_fifa_api_id", "bigint"),
        ("player_api_id", "pa", "player_api_id", "bigint"),
        ("attributes_date", "pa", "date", "text"),
        ("overall_rating", "pa", "overall_rating", "bigint"),
        ("potential", "pa", "potential", "bigint"),
        ("preferred_foot", "pa", "preferred_foot", "text"),
        ("attacking_work_rate", "pa", "attacking_work_rate", "text"),
        ("defensive_work_rate", "pa", "defensive_work_rate", "text"),
        ("crossing", "pa", "crossing", "bigint"),
        ("finishing", "pa", "finishing", "bigint"),
        ("heading_accuracy", "pa", "heading_accuracy", "bigint"),
        ("short_passing", "pa", "short_passing", "bigint"),
        ("volleys", "pa", "volleys", "bigint"),
        ("dribbling", "pa", "dribbling", "bigint"),
        ("curve", "pa", "curve", "bigint"),
        ("free_kick_accuracy", "pa", "free_kick_accuracy", "bigint"),
        ("long_passing", "pa", "long_passing", "bigint"),
        ("ball_control", "pa", "ball_control", "bigint"),
        ("acceleration", "pa", "acceleration", "bigint"),
        ("sprint_speed", "pa", "sprint_speed", "bigint"),
        ("agility", "pa", "agility", "bigint"),
        ("reactions", "pa", "reactions", "bigint"),
        ("balance", "pa", "balance", "bigint"),
        ("shot_power", "pa", "shot_power", "bigint"),
        ("jumping", "pa", "jumping", "bigint"),
        ("stamina", "pa", "stamina", "bigint"),
        ("strength", "pa", "strength", "bigint"),
        ("long_shots", "pa", "long_shots", "bigint"),
        ("aggression", "pa", "aggression", "bigint"),
        ("interceptions", "pa", "interceptions", "bigint"),
        ("positioning", "pa", "positioning", "bigint"),
        ("vision", "pa", "vision", "bigint"),
        ("penalties", "pa", "penalties", "bigint"),
        ("marking", "pa", "marking", "bigint"),
        ("standing_tackle", "pa", "standing_tackle", "bigint"),
        ("sliding_tackle", "pa", "sliding_tackle", "bigint"),
        ("gk_diving", "pa", "gk_diving", "bigint"),
        ("gk_handling", "pa", "gk_handling", "bigint"),
        ("gk_kicking", "pa", "gk_kicking", "bigint"),
        ("gk_positioning", "pa", "gk_positioning", "bigint"),
        ("gk_reflexes", "pa", "gk_reflexes", "bigint"),
        ("player_id", "p", "id", "bigint"),
        ("player_name", "p", "player_name", "text"),
        ("birthday", "p", "birthday", "text"),
        ("height", "p", "height", "bigint"),
        ("weight", "p", "weight", "bigint"),
    ]
    write_model(
        {
            "name": "player",
            "source": SOURCE,
            "description": "선수 주제. Player_Attributes·Player를 join으로 구성(능력치 시점 grain).",
            "tables": [
                {
                    "alias": "pa",
                    "priority": 1,
                    "tableReference": {"schema": SCHEMA, "table": "Player_Attributes"},
                },
                {
                    "alias": "p",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "Player"},
                    "join": {"to": "pa", "type": "left", "on": [{"left": "player_api_id", "right": "player_api_id"}]},
                },
            ],
            "primaryKey": "player_attributes_id",
            "columns": [phys(*r[:4], r[4] if len(r) > 4 else False) for r in pa_cols],
        }
    )

    match_cols = cols_from_table("m", "Match", rename={"id": "match_id"}, extra_not_null={"id"})
    match_cols.extend(
        [
            rel("league", "league", "match_to_league"),
            rel("country", "country", "match_to_country"),
            rel("home_team", "team", "match_to_home_team"),
            rel("away_team", "team", "match_to_away_team"),
        ]
    )
    write_model(
        {
            "name": "match",
            "source": SOURCE,
            "description": "경기 주제. Match(라인업·이벤트·배당) 단일 테이블.",
            "tables": [{"alias": "m", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "Match"}}],
            "primaryKey": "match_id",
            "columns": match_cols,
        }
    )

    rels = [
        ("league_to_country", "league", "country_id", "country", "country_id", "league → country"),
        ("match_to_league", "match", "league_id", "league", "league_id", "match → league"),
        ("match_to_country", "match", "country_id", "country", "country_id", "match → country"),
        ("match_to_home_team", "match", "home_team_api_id", "team", "team_api_id", "match → home team"),
        ("match_to_away_team", "match", "away_team_api_id", "team", "team_api_id", "match → away team"),
    ]
    for stem, fm, fc, tm, tc, desc in rels:
        write_rel(relationship(stem, fm, fc, tm, tc, desc))

    print(f"wrote {len(list(OUT.glob('*.model.json')))} models, {len(list(OUT.glob('*.relationship.json')))} rels")


if __name__ == "__main__":
    main()
