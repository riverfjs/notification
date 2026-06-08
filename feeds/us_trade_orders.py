#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "curl_cffi>=0.7"]
# ///
"""US trade and durable-goods release data from the official Census EITS API.

No fallback. Census Data API calls require CENSUS_API_KEY. Transport uses curl_cffi
with a browser TLS profile because the Census API is unstable from this network
with plain urllib/curl TLS handshakes.
"""
from __future__ import annotations

import os
import time
from datetime import date

import pandas as pd
from curl_cffi import requests

from _common import save

BASE = "https://api.census.gov/data/timeseries/eits"
COMMON = "program_code,cell_value,time_slot_id,time_slot_date,time_slot_name,data_type_code,seasonally_adj,category_code"

TARGETS = [
    {
        "dataset": "ftd",
        "column": "trade_balance_goods_services",
        "data_type_code": "BAL",
        "category_code": "BOPGS",
        "seasonally_adj": "yes",
    },
    {
        "dataset": "advm3",
        "column": "durable_ex_transport_orders",
        "data_type_code": "NO",
        "category_code": "34S",
        "seasonally_adj": "yes",
    },
    {
        "dataset": "advm3",
        "column": "durable_ex_transport_orders_mom",
        "data_type_code": "MPCNO",
        "category_code": "34S",
        "seasonally_adj": "yes",
    },
]


def _census_key() -> str:
    key = os.environ.get("CENSUS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("缺少 Census API key: 设置环境变量 CENSUS_API_KEY")
    return key


def _to_float(value: str) -> float | None:
    s = value.replace(",", "").strip()
    if not s or s == ".":
        return None
    return float(s)


def fetch_target(session: requests.Session, target: dict[str, str], start_year: int) -> pd.Series:
    params = {
        "get": COMMON,
        "time": f"from {start_year}",
        "for": "us:*",
        "data_type_code": target["data_type_code"],
        "seasonally_adj": target["seasonally_adj"],
        "category_code": target["category_code"],
        "key": _census_key(),
    }
    url = f"{BASE}/{target['dataset']}"
    last = None
    for attempt in range(4):
        try:
            resp = session.get(
                url,
                params=params,
                impersonate="chrome120",
                timeout=(20, 60),
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            rows = resp.json()
            break
        except Exception as exc:  # noqa: BLE001
            last = str(exc)[:220]
            time.sleep(1.5 * (attempt + 1))
    else:
        raise RuntimeError(f"Census EITS failed {target['dataset']}:{target['column']}: {last}")

    header = rows[0]
    records = [dict(zip(header, row)) for row in rows[1:]]
    values: list[tuple[pd.Timestamp, float]] = []
    for row in records:
        value = _to_float(row.get("cell_value", ""))
        if value is None:
            continue
        values.append((pd.Timestamp(row["time"] + "-01"), value))
    if not values:
        raise RuntimeError(f"Census EITS returned no rows for {target['column']}")
    return pd.Series(dict(values), name=target["column"]).sort_index()


def main():
    start_year = max(2015, date.today().year - 10)
    session = requests.Session()
    series = [fetch_target(session, target, start_year) for target in TARGETS]
    df = pd.concat(series, axis=1).sort_index()
    save(df, "us_trade_orders", "US贸易&订单")


if __name__ == "__main__":
    main()
