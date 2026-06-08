#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26"]
# ///
"""US inflation release data from official BLS and BEA sources.

No fallback: BLS CPI/PPI uses the BLS Public Data API, and PCE/Core PCE uses BEA
NIPA release TXT files. Derived MoM/YoY columns are computed locally from levels.
"""
from __future__ import annotations

import csv
import io
import json
import re
import time
import urllib.request
from datetime import date

import pandas as pd

from _common import UA, save

BLS_API = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BEA_NIPA_M = "https://apps.bea.gov/national/Release/TXT/NipaDataM.txt"

BLS_SERIES = {
    "CUSR0000SA0": "cpi_headline",
    "CUSR0000SA0L1E": "cpi_core",
    "WPSFD4": "ppi_headline",
    "WPSFD49104": "ppi_core",
    "WPSFD49116": "ppi_core_ex_food_energy_trade",
}

BEA_SERIES = {
    "DPCERG": "pce",
    "DPCCRG": "core_pce",
}


def _post_json(url: str, payload: dict, retries: int = 4) -> dict:
    body = json.dumps(payload).encode("utf-8")
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                data=body,
                headers={**UA, "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8", "replace"))
        except Exception as exc:  # noqa: BLE001
            last = str(exc)[:160]
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"BLS API failed after {retries}x: {last}")


def _get_text(url: str, retries: int = 4) -> str:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as resp:
                return resp.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001
            last = str(exc)[:160]
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"fetch failed after {retries}x: {url}\n  last: {last}")


def _to_float(value: str) -> float | None:
    s = value.replace(",", "").strip()
    if not s or s in {".", "-"}:
        return None
    return float(s)


def _with_changes(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        out[f"{col}_mom"] = out[col].pct_change() * 100.0
        out[f"{col}_yoy"] = out[col].pct_change(12) * 100.0
    return out


def fetch_bls() -> pd.DataFrame:
    end_year = date.today().year
    frames = []
    for start in range(2000, end_year + 1, 10):
        end = min(start + 9, end_year)
        data = _post_json(
            BLS_API,
            {
                "seriesid": list(BLS_SERIES),
                "startyear": str(start),
                "endyear": str(end),
            },
        )
        if data.get("status") != "REQUEST_SUCCEEDED":
            raise RuntimeError(f"BLS API status={data.get('status')} messages={data.get('message')}")
        for series in data.get("Results", {}).get("series", []):
            sid = series["seriesID"]
            name = BLS_SERIES[sid]
            rows = []
            for item in series.get("data", []):
                period = item.get("period", "")
                if not re.fullmatch(r"M\d{2}", period):
                    continue
                value = _to_float(item.get("value", ""))
                if value is None:
                    continue
                rows.append((pd.Timestamp(int(item["year"]), int(period[1:]), 1), value))
            if rows:
                frames.append(pd.DataFrame(rows, columns=["date", name]).set_index("date"))
        time.sleep(0.4)
    if not frames:
        raise RuntimeError("BLS API returned no CPI/PPI observations")
    wide = pd.concat(frames, axis=1, sort=True).sort_index()
    return wide.T.groupby(level=0).last().T.sort_index()


def fetch_bea_pce() -> pd.DataFrame:
    text = _get_text(BEA_NIPA_M)
    rows_by_col: dict[str, list[tuple[pd.Timestamp, float]]] = {v: [] for v in BEA_SERIES.values()}
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        code = row.get("%SeriesCode") or row.get("SeriesCode")
        col = BEA_SERIES.get(code or "")
        if not col:
            continue
        period = row.get("Period", "")
        match = re.fullmatch(r"(\d{4})M(\d{2})", period)
        value = _to_float(row.get("Value", ""))
        if not match or value is None:
            continue
        rows_by_col[col].append((pd.Timestamp(int(match[1]), int(match[2]), 1), value))

    frames = []
    for col, rows in rows_by_col.items():
        if not rows:
            raise RuntimeError(f"BEA NIPA monthly TXT missing {col}")
        frames.append(pd.DataFrame(rows, columns=["date", col]).set_index("date"))
    return pd.concat(frames, axis=1).sort_index()


def main():
    bls = fetch_bls()
    bea = fetch_bea_pce()
    df = pd.concat([bls, bea], axis=1, sort=True).sort_index()
    levels = list(BLS_SERIES.values()) + list(BEA_SERIES.values())
    df = _with_changes(df, levels)
    ordered = []
    for col in levels:
        ordered.extend([col, f"{col}_mom", f"{col}_yoy"])
    save(df[ordered], "us_inflation_releases", "US通胀发布")


if __name__ == "__main__":
    main()
