#!/usr/bin/env python3
"""Manually consolidated delivery_center metadata."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "delivery_center"
SCHEMA = "delivery_center"
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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob("*.model.json"):
        p.unlink()
    for p in OUT.glob("*.relationship.json"):
        p.unlink()

    dec = "decimal(10,2)"

    write_model(
        {
            "name": "channel",
            "source": SOURCE,
            "description": "주문 채널 참조.",
            "tables": [{"alias": "c", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "channels"}}],
            "primaryKey": "channel_id",
            "columns": [
                phys("channel_id", "c", "channel_id", "bigint", True),
                phys("channel_name", "c", "channel_name", "text"),
                phys("channel_type", "c", "channel_type", "text"),
            ],
        }
    )

    write_model(
        {
            "name": "hub",
            "source": SOURCE,
            "description": "배송 허브(물류 거점) 참조.",
            "tables": [{"alias": "h", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "hubs"}}],
            "primaryKey": "hub_id",
            "columns": [
                phys("hub_id", "h", "hub_id", "bigint", True),
                phys("hub_name", "h", "hub_name", "text"),
                phys("hub_city", "h", "hub_city", "text"),
                phys("hub_state", "h", "hub_state", "text"),
                phys("hub_latitude", "h", "hub_latitude", dec),
                phys("hub_longitude", "h", "hub_longitude", dec),
            ],
        }
    )

    write_model(
        {
            "name": "store",
            "source": SOURCE,
            "description": "매장 주제. stores·hub를 join으로 구성.",
            "tables": [
                {"alias": "s", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "stores"}},
                {
                    "alias": "h",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "hubs"},
                    "join": {"to": "s", "type": "left", "on": [{"left": "hub_id", "right": "hub_id"}]},
                },
            ],
            "primaryKey": "store_id",
            "columns": [
                phys("store_id", "s", "store_id", "bigint", True),
                phys("hub_id", "s", "hub_id", "bigint"),
                phys("store_name", "s", "store_name", "text"),
                phys("store_segment", "s", "store_segment", "text"),
                phys("store_plan_price", "s", "store_plan_price", dec),
                phys("store_latitude", "s", "store_latitude", dec),
                phys("store_longitude", "s", "store_longitude", dec),
                phys("hub_name", "h", "hub_name", "text"),
                phys("hub_city", "h", "hub_city", "text"),
                phys("hub_state", "h", "hub_state", "text"),
                rel("hub", "hub", "store_to_hub"),
            ],
        }
    )

    write_model(
        {
            "name": "driver",
            "source": SOURCE,
            "description": "배달 드라이버 참조.",
            "tables": [{"alias": "d", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "drivers"}}],
            "primaryKey": "driver_id",
            "columns": [
                phys("driver_id", "d", "driver_id", "bigint", True),
                phys("driver_modal", "d", "driver_modal", "text"),
                phys("driver_type", "d", "driver_type", "text"),
            ],
        }
    )

    write_model(
        {
            "name": "order",
            "source": SOURCE,
            "description": "주문 fact. 금액·타임라인·운영 지표.",
            "tables": [{"alias": "o", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "orders"}}],
            "primaryKey": "order_id",
            "columns": [
                phys("order_id", "o", "order_id", "bigint", True),
                phys("store_id", "o", "store_id", "bigint"),
                phys("channel_id", "o", "channel_id", "bigint"),
                phys("payment_order_id", "o", "payment_order_id", "bigint"),
                phys("delivery_order_id", "o", "delivery_order_id", "bigint"),
                phys("order_status", "o", "order_status", "text"),
                phys("order_amount", "o", "order_amount", dec),
                phys("order_delivery_fee", "o", "order_delivery_fee", dec),
                phys("order_delivery_cost", "o", "order_delivery_cost", dec),
                phys("order_created_hour", "o", "order_created_hour", "bigint"),
                phys("order_created_minute", "o", "order_created_minute", "bigint"),
                phys("order_created_day", "o", "order_created_day", "bigint"),
                phys("order_created_month", "o", "order_created_month", "bigint"),
                phys("order_created_year", "o", "order_created_year", "bigint"),
                phys("order_moment_created", "o", "order_moment_created", "timestamp"),
                phys("order_moment_accepted", "o", "order_moment_accepted", "timestamp"),
                phys("order_moment_ready", "o", "order_moment_ready", "timestamp"),
                phys("order_moment_collected", "o", "order_moment_collected", "timestamp"),
                phys("order_moment_in_expedition", "o", "order_moment_in_expedition", "timestamp"),
                phys("order_moment_delivering", "o", "order_moment_delivering", "timestamp"),
                phys("order_moment_delivered", "o", "order_moment_delivered", "timestamp"),
                phys("order_moment_finished", "o", "order_moment_finished", "timestamp"),
                phys("order_metric_collected_time", "o", "order_metric_collected_time", dec),
                phys("order_metric_paused_time", "o", "order_metric_paused_time", dec),
                phys("order_metric_production_time", "o", "order_metric_production_time", dec),
                phys("order_metric_walking_time", "o", "order_metric_walking_time", dec),
                phys("order_metric_expediton_speed_time", "o", "order_metric_expediton_speed_time", dec),
                phys("order_metric_transit_time", "o", "order_metric_transit_time", dec),
                phys("order_metric_cycle_time", "o", "order_metric_cycle_time", dec),
                rel("store", "store", "order_to_store"),
                rel("channel", "channel", "order_to_channel"),
            ],
        }
    )

    write_model(
        {
            "name": "payment",
            "source": SOURCE,
            "description": "결제 fact(주문당 1건 이상 가능).",
            "tables": [{"alias": "p", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "payments"}}],
            "primaryKey": "payment_id",
            "columns": [
                phys("payment_id", "p", "payment_id", "bigint", True),
                phys("payment_order_id", "p", "payment_order_id", "bigint"),
                phys("payment_amount", "p", "payment_amount", dec),
                phys("payment_fee", "p", "payment_fee", dec),
                phys("payment_method", "p", "payment_method", "text"),
                phys("payment_status", "p", "payment_status", "text"),
                rel("order", "order", "payment_to_order"),
            ],
        }
    )

    write_model(
        {
            "name": "delivery",
            "source": SOURCE,
            "description": "배달 실행 fact. deliveries·driver를 join으로 구성.",
            "tables": [
                {"alias": "d", "priority": 1, "tableReference": {"schema": SCHEMA, "table": "deliveries"}},
                {
                    "alias": "dr",
                    "priority": 2,
                    "tableReference": {"schema": SCHEMA, "table": "drivers"},
                    "join": {"to": "d", "type": "left", "on": [{"left": "driver_id", "right": "driver_id"}]},
                },
            ],
            "primaryKey": "delivery_id",
            "columns": [
                phys("delivery_id", "d", "delivery_id", "bigint", True),
                phys("delivery_order_id", "d", "delivery_order_id", "bigint"),
                phys("driver_id", "d", "driver_id", "bigint"),
                phys("delivery_distance_meters", "d", "delivery_distance_meters", dec),
                phys("delivery_status", "d", "delivery_status", "text"),
                phys("driver_modal", "dr", "driver_modal", "text"),
                phys("driver_type", "dr", "driver_type", "text"),
                rel("order", "order", "delivery_to_order"),
                rel("driver", "driver", "delivery_to_driver"),
            ],
        }
    )

    rels = [
        ("store_to_hub", "store", "hub_id", "hub", "hub_id", "store → hub"),
        ("order_to_store", "order", "store_id", "store", "store_id", "order → store"),
        ("order_to_channel", "order", "channel_id", "channel", "channel_id", "order → channel"),
        ("payment_to_order", "payment", "payment_order_id", "order", "order_id", "payment → order"),
        ("delivery_to_order", "delivery", "delivery_order_id", "order", "order_id", "delivery → order"),
        ("delivery_to_driver", "delivery", "driver_id", "driver", "driver_id", "delivery → driver"),
    ]
    for args in rels:
        write_rel(relationship(*args))

    print(f"wrote {len(list(OUT.glob('*.model.json')))} models, {len(list(OUT.glob('*.relationship.json')))} rels")


if __name__ == "__main__":
    main()
