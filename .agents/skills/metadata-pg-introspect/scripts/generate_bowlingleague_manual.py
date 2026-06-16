#!/usr/bin/env python3
"""Manually consolidated bowlingleague metadata."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "bowlingleague"
SCHEMA = "bowlingleague"
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
            "name": "team",
            "source": SOURCE,
            "description": "팀 참조.",
            "tables": [{"alias": "t", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "Teams"}}],
            "primaryKey": "team_id",
            "columns": [
                phys("team_id", "t", "TeamID", "bigint", True),
                phys("team_name", "t", "TeamName", "text", True),
                phys("captain_id", "t", "CaptainID", "bigint"),
            ],
        }
    )

    write_model(
        {
            "name": "bowler",
            "source": SOURCE,
            "description": "볼러 주제. Bowlers·Teams·WA 우편 lookup을 join으로 구성.",
            "tables": [
                {"alias": "b", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "Bowlers"}},
                {
                    "alias": "t",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "Teams"},
                    "join": {"to": "b", "type": "left", "on": [{"left": "TeamID", "right": "TeamID"}]},
                },
                {
                    "alias": "z",
                    "priority": 3,
                    "tableReference": {"schema": SCHEMA, "table": "WAZips"},
                    "join": {"to": "b", "type": "left", "on": [{"left": "ZIP", "right": "BowlerZip"}]},
                },
            ],
            "primaryKey": "bowler_id",
            "columns": [
                phys("bowler_id", "b", "BowlerID", "bigint", True),
                phys("bowler_last_name", "b", "BowlerLastName", "text"),
                phys("bowler_first_name", "b", "BowlerFirstName", "text"),
                phys("bowler_middle_init", "b", "BowlerMiddleInit", "text"),
                phys("bowler_address", "b", "BowlerAddress", "text"),
                phys("bowler_city", "b", "BowlerCity", "text"),
                phys("bowler_state", "b", "BowlerState", "text"),
                phys("bowler_zip", "b", "BowlerZip", "text"),
                phys("bowler_phone_number", "b", "BowlerPhoneNumber", "text"),
                phys("team_id", "b", "TeamID", "bigint"),
                phys("bowler_total_pins", "b", "BowlerTotalPins", "bigint"),
                phys("bowler_games_bowled", "b", "BowlerGamesBowled", "bigint"),
                phys("bowler_current_average", "b", "BowlerCurrentAverage", "smallint"),
                phys("bowler_current_hcp", "b", "BowlerCurrentHcp", "smallint"),
                phys("team_name", "t", "TeamName", "text"),
                phys("zip_city", "z", "City", "text"),
                phys("zip_state", "z", "State", "text"),
                rel("team", "team", "bowler_to_team"),
            ],
        }
    )

    write_model(
        {
            "name": "tournament",
            "source": SOURCE,
            "description": "토너먼트(현행) 참조.",
            "tables": [{"alias": "t", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "Tournaments"}}],
            "primaryKey": "tourney_id",
            "columns": [
                phys("tourney_id", "t", "TourneyID", "bigint", True),
                phys("tourney_date", "t", "TourneyDate", "date"),
                phys("tourney_location", "t", "TourneyLocation", "text"),
            ],
        }
    )

    write_model(
        {
            "name": "tournament_archive",
            "source": SOURCE,
            "description": "토너먼트(아카이브) 참조.",
            "tables": [
                {"alias": "t", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "Tournaments_Archive"}}
            ],
            "primaryKey": "tourney_id",
            "columns": [
                phys("tourney_id", "t", "TourneyID", "bigint", True),
                phys("tourney_date", "t", "TourneyDate", "date"),
                phys("tourney_location", "t", "TourneyLocation", "text"),
            ],
        }
    )

    def tourney_match_model(name: str, tm_table: str, mg_table: str, desc: str, tourney_model: str) -> None:
        write_model(
            {
                "name": name,
                "source": SOURCE,
                "description": desc,
                "tables": [
                    {"alias": "mg", "priority": 1, "tableReference": {"schema": SCHEMA, "table": mg_table}},
                    {
                        "alias": "tm",
                        "priority": 2,
                        "tableReference": {"schema": SCHEMA, "table": tm_table},
                        "join": {"to": "mg", "type": "left", "on": [{"left": "MatchID", "right": "MatchID"}]},
                    },
                ],
                "primaryKey": "game_id",
                "columns": [
                    calc("game_id", "match_id || ':' || game_number", desc="MatchID·GameNumber 복합 키"),
                    phys("match_id", "mg", "MatchID", "bigint", True),
                    phys("game_number", "mg", "GameNumber", "smallint", True),
                    phys("tourney_id", "tm", "TourneyID", "bigint"),
                    phys("lanes", "tm", "Lanes", "text"),
                    phys("odd_lane_team_id", "tm", "OddLaneTeamID", "bigint"),
                    phys("even_lane_team_id", "tm", "EvenLaneTeamID", "bigint"),
                    phys("winning_team_id", "mg", "WinningTeamID", "bigint"),
                    rel("tournament", tourney_model, f"{name}_to_{tourney_model}"),
                    rel("odd_team", "team", f"{name}_to_odd_team"),
                    rel("even_team", "team", f"{name}_to_even_team"),
                    rel("winning_team", "team", f"{name}_to_winning_team"),
                ],
            }
        )

    tourney_match_model(
        "tourney_match",
        "Tourney_Matches",
        "Match_Games",
        "대회 매치·게임 주제(현행). Tourney_Matches·Match_Games를 join으로 구성.",
        "tournament",
    )
    tourney_match_model(
        "tourney_match_archive",
        "Tourney_Matches_Archive",
        "Match_Games_Archive",
        "대회 매치·게임 주제(아카이브).",
        "tournament_archive",
    )

    def bowler_score_model(name: str, table: str, desc: str, tm_model: str) -> None:
        write_model(
            {
                "name": name,
                "source": SOURCE,
                "description": desc,
                "tables": [{"alias": "bs", "priority": 1, "tableReference": {"schema": SCHEMA, "table": table}}],
                "primaryKey": "id",
                "columns": [
                    calc(
                        "id",
                        "match_id || ':' || game_number || ':' || bowler_id",
                        desc="match·game·bowler 복합 키",
                    ),
                    calc("game_id", "match_id || ':' || game_number", desc="tourney_match.game_id 조인용"),
                    phys("match_id", "bs", "MatchID", "bigint", True),
                    phys("game_number", "bs", "GameNumber", "smallint", True),
                    phys("bowler_id", "bs", "BowlerID", "bigint", True),
                    phys("raw_score", "bs", "RawScore", "smallint"),
                    phys("handi_cap_score", "bs", "HandiCapScore", "smallint"),
                    phys("won_game", "bs", "WonGame", "boolean", True),
                    rel("bowler", "bowler", f"{name}_to_bowler"),
                    rel("tourney_match", tm_model, f"{name}_to_{tm_model}"),
                ],
            }
        )

    bowler_score_model(
        "bowler_score",
        "Bowler_Scores",
        "볼러 점수(현행).",
        "tourney_match",
    )
    bowler_score_model(
        "bowler_score_archive",
        "Bowler_Scores_Archive",
        "볼러 점수(아카이브).",
        "tourney_match_archive",
    )

    rels = [
        ("bowler_to_team", "bowler", "team_id", "team", "team_id", "bowler → team"),
        ("tourney_match_to_tournament", "tourney_match", "tourney_id", "tournament", "tourney_id", "tourney_match → tournament"),
        (
            "tourney_match_to_odd_team",
            "tourney_match",
            "odd_lane_team_id",
            "team",
            "team_id",
            "tourney_match → odd lane team",
        ),
        (
            "tourney_match_to_even_team",
            "tourney_match",
            "even_lane_team_id",
            "team",
            "team_id",
            "tourney_match → even lane team",
        ),
        (
            "tourney_match_to_winning_team",
            "tourney_match",
            "winning_team_id",
            "team",
            "team_id",
            "tourney_match → winning team",
        ),
        (
            "tourney_match_archive_to_tournament_archive",
            "tourney_match_archive",
            "tourney_id",
            "tournament_archive",
            "tourney_id",
            "tourney_match_archive → tournament_archive",
        ),
        (
            "tourney_match_archive_to_odd_team",
            "tourney_match_archive",
            "odd_lane_team_id",
            "team",
            "team_id",
            "tourney_match_archive → odd lane team",
        ),
        (
            "tourney_match_archive_to_even_team",
            "tourney_match_archive",
            "even_lane_team_id",
            "team",
            "team_id",
            "tourney_match_archive → even lane team",
        ),
        (
            "tourney_match_archive_to_winning_team",
            "tourney_match_archive",
            "winning_team_id",
            "team",
            "team_id",
            "tourney_match_archive → winning team",
        ),
        ("bowler_score_to_bowler", "bowler_score", "bowler_id", "bowler", "bowler_id", "bowler_score → bowler"),
        (
            "bowler_score_to_tourney_match",
            "bowler_score",
            "game_id",
            "tourney_match",
            "game_id",
            "bowler_score → tourney_match",
        ),
        (
            "bowler_score_archive_to_bowler",
            "bowler_score_archive",
            "bowler_id",
            "bowler",
            "bowler_id",
            "bowler_score_archive → bowler",
        ),
        (
            "bowler_score_archive_to_tourney_match_archive",
            "bowler_score_archive",
            "game_id",
            "tourney_match_archive",
            "game_id",
            "bowler_score_archive → tourney_match_archive",
        ),
    ]
    for args in rels:
        write_rel(relationship(*args))

    print(f"wrote {len(list(OUT.glob('*.model.json')))} models, {len(list(OUT.glob('*.relationship.json')))} rels")


if __name__ == "__main__":
    main()
