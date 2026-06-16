#!/usr/bin/env python3
"""Manually consolidated db-imdb metadata."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "db-imdb"
SCHEMA = "db-imdb"
SOURCE = "local_postgres"


def phys(name: str, alias: str, col: str, typ: str, not_null: bool = False) -> dict:
    c = {"name": name, "kind": "physical", "type": typ, "from": f"{alias}.{col}"}
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


def junction(
    name: str,
    desc: str,
    link_table: str,
    link_alias: str,
    dim_joins: list[tuple[str, str, str, list[dict]]],
    extra_cols: list[dict],
    rels_out: list[dict],
) -> None:
    """link + Movie + dimension table(s) with verified join keys."""
    tables = [
        {"alias": link_alias, "priority": 1, "tableReference": {"schema": SCHEMA, "table": link_table}},
        {
            "alias": "mv",
            "priority": 2,
            "tableReference": {"schema": SCHEMA, "table": "Movie"},
            "join": {"to": link_alias, "type": "left", "on": [{"left": "MID", "right": "MID"}]},
        },
    ]
    priority = 3
    columns = [
        phys("link_id", link_alias, "ID", "bigint"),
        phys("mid", link_alias, "MID", "text"),
        phys("movie_title", "mv", "title", "text"),
        phys("movie_year", "mv", "year", "text"),
        phys("movie_rating", "mv", "rating", "double"),
        phys("movie_num_votes", "mv", "num_votes", "bigint"),
    ] + extra_cols

    for dim_alias, dim_table, join_col, on_clause in dim_joins:
        tables.append(
            {
                "alias": dim_alias,
                "priority": priority,
                "tableReference": {"schema": SCHEMA, "table": dim_table},
                "join": {"to": link_alias, "type": "left", "on": on_clause},
            }
        )
        priority += 1

    columns.extend(rels_out)
    write_model(
        {
            "name": name,
            "source": SOURCE,
            "description": desc,
            "tables": tables,
            "primaryKey": "link_id",
            "columns": columns,
        }
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob("*.model.json"):
        p.unlink()
    for p in OUT.glob("*.relationship.json"):
        p.unlink()

    write_model(
        {
            "name": "movie",
            "source": SOURCE,
            "description": "영화 카탈로그.",
            "tables": [{"alias": "m", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "Movie"}}],
            "primaryKey": "mid",
            "columns": [
                phys("mid", "m", "MID", "text"),
                phys("title", "m", "title", "text"),
                phys("year", "m", "year", "text"),
                phys("rating", "m", "rating", "double"),
                phys("num_votes", "m", "num_votes", "bigint"),
            ],
        }
    )

    write_model(
        {
            "name": "person",
            "source": SOURCE,
            "description": "인물(배우·감독·제작) 카탈로그.",
            "tables": [{"alias": "p", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "Person"}}],
            "primaryKey": "pid",
            "columns": [
                phys("pid", "p", "PID", "text"),
                phys("name", "p", "Name", "text"),
                phys("gender", "p", "Gender", "text"),
            ],
        }
    )

    for ref_name, table, pk_col, id_field in [
        ("country", "Country", "cid", "CID"),
        ("genre", "Genre", "gid", "GID"),
        ("language", "Language", "language_id", "LAID"),
        ("location", "Location", "location_id", "LID"),
    ]:
        write_model(
            {
                "name": ref_name,
                "source": SOURCE,
                "description": f"{ref_name} 참조.",
                "tables": [{"alias": "r", "priority": 1, "tableReference": {"schema": SCHEMA, "table": table}}],
                "primaryKey": pk_col,
                "columns": [
                    phys(pk_col, "r", id_field, "bigint"),
                    phys("name", "r", "Name", "text"),
                ],
            }
        )

    junction(
        "cast",
        "출연(M_Cast)·영화·인물을 join으로 구성.",
        "M_Cast",
        "mc",
        [("pr", "Person", "pid", [{"left": "PID", "right": "PID"}])],
        [phys("pid", "mc", "PID", "text"), phys("person_name", "pr", "Name", "text"), phys("person_gender", "pr", "Gender", "text")],
        [rel("movie", "movie", "cast_to_movie"), rel("person", "person", "cast_to_person")],
    )

    junction(
        "movie_director",
        "감독(M_Director)·영화·인물을 join으로 구성.",
        "M_Director",
        "md",
        [("pr", "Person", "pid", [{"left": "PID", "right": "PID"}])],
        [phys("pid", "md", "PID", "text"), phys("director_name", "pr", "Name", "text")],
        [rel("movie", "movie", "movie_director_to_movie"), rel("person", "person", "movie_director_to_person")],
    )

    junction(
        "movie_producer",
        "제작(M_Producer)·영화·인물을 join으로 구성.",
        "M_Producer",
        "mp",
        [("pr", "Person", "pid", [{"left": "PID", "right": "PID"}])],
        [phys("pid", "mp", "PID", "text"), phys("producer_name", "pr", "Name", "text")],
        [rel("movie", "movie", "movie_producer_to_movie"), rel("person", "person", "movie_producer_to_person")],
    )

    junction(
        "movie_genre",
        "장르(M_Genre)·영화·Genre를 join으로 구성.",
        "M_Genre",
        "mg",
        [("g", "Genre", "gid", [{"left": "GID", "right": "GID"}])],
        [phys("gid", "mg", "GID", "bigint"), phys("genre_name", "g", "Name", "text")],
        [rel("movie", "movie", "movie_genre_to_movie"), rel("genre", "genre", "movie_genre_to_genre")],
    )

    junction(
        "movie_country",
        "국가(M_Country)·영화·Country를 join으로 구성.",
        "M_Country",
        "mco",
        [("c", "Country", "cid", [{"left": "CID", "right": "CID"}])],
        [phys("cid", "mco", "CID", "double"), phys("country_name", "c", "Name", "text")],
        [rel("movie", "movie", "movie_country_to_movie"), rel("country", "country", "movie_country_to_country")],
    )

    junction(
        "movie_language",
        "언어(M_Language)·영화·Language를 join으로 구성.",
        "M_Language",
        "mla",
        [("l", "Language", "language_id", [{"left": "LAID", "right": "LAID"}])],
        [phys("language_id", "mla", "LAID", "bigint"), phys("language_name", "l", "Name", "text")],
        [rel("movie", "movie", "movie_language_to_movie"), rel("language", "language", "movie_language_to_language")],
    )

    junction(
        "movie_location",
        "촬영지(M_Location)·영화·Location을 join으로 구성.",
        "M_Location",
        "ml",
        [("loc", "Location", "location_id", [{"left": "LID", "right": "LID"}])],
        [phys("location_id", "ml", "LID", "double"), phys("location_name", "loc", "Name", "text")],
        [rel("movie", "movie", "movie_location_to_movie"), rel("location", "location", "movie_location_to_location")],
    )

    rels = [
        ("cast_to_movie", "cast", "mid", "movie", "mid", "cast → movie"),
        ("cast_to_person", "cast", "pid", "person", "pid", "cast → person"),
        ("movie_director_to_movie", "movie_director", "mid", "movie", "mid", "movie_director → movie"),
        ("movie_director_to_person", "movie_director", "pid", "person", "pid", "movie_director → person"),
        ("movie_producer_to_movie", "movie_producer", "mid", "movie", "mid", "movie_producer → movie"),
        ("movie_producer_to_person", "movie_producer", "pid", "person", "pid", "movie_producer → person"),
        ("movie_genre_to_movie", "movie_genre", "mid", "movie", "mid", "movie_genre → movie"),
        ("movie_genre_to_genre", "movie_genre", "gid", "genre", "gid", "movie_genre → genre"),
        ("movie_country_to_movie", "movie_country", "mid", "movie", "mid", "movie_country → movie"),
        ("movie_country_to_country", "movie_country", "cid", "country", "cid", "movie_country → country"),
        ("movie_language_to_movie", "movie_language", "mid", "movie", "mid", "movie_language → movie"),
        ("movie_language_to_language", "movie_language", "language_id", "language", "language_id", "movie_language → language"),
        ("movie_location_to_movie", "movie_location", "mid", "movie", "mid", "movie_location → movie"),
        ("movie_location_to_location", "movie_location", "location_id", "location", "location_id", "movie_location → location"),
    ]
    for args in rels:
        write_rel(relationship(*args))

    print(f"wrote {len(list(OUT.glob('*.model.json')))} models, {len(list(OUT.glob('*.relationship.json')))} rels")


if __name__ == "__main__":
    main()
