#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26"]
# ///
"""University of Michigan Surveys of Consumers official public CSVs.

No FRED fallback: the official UMich CSVs are fresher than FRED's delayed UMCSENT.
"""
from __future__ import annotations

import csv
import io

import pandas as pd

from _common import _get, save

SENTIMENT_URL = "https://www.sca.isr.umich.edu/files/tbcics.csv"
COMPONENTS_URL = "https://www.sca.isr.umich.edu/files/tbciccice.csv"
INFLATION_URL = "https://www.sca.isr.umich.edu/files/tbcpx1px5.csv"


def _to_float(value: str) -> float | None:
    s = value.strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _date_from_row(row: list[str]) -> pd.Timestamp | None:
    if len(row) < 2 or not row[1].strip().isdigit():
        return None
    try:
        return pd.to_datetime(f"{row[0].strip()} {row[1].strip()}", format="%b %Y")
    except ValueError:
        try:
            return pd.to_datetime(f"{row[0].strip()} {row[1].strip()}")
        except ValueError:
            return None


def _read_columns(url: str, mapping: dict[int, str]) -> pd.DataFrame:
    text = _get(url, timeout=60).text
    rows = []
    for row in csv.reader(io.StringIO(text)):
        if not any(cell.strip() for cell in row):
            continue
        dt = _date_from_row(row)
        if dt is None:
            continue
        values = {"date": dt}
        for idx, col in mapping.items():
            values[col] = _to_float(row[idx]) if idx < len(row) else None
        rows.append(values)
    if not rows:
        raise RuntimeError(f"UMich CSV returned no observations: {url}")
    return pd.DataFrame(rows).set_index("date").sort_index()


def main():
    sentiment = _read_columns(SENTIMENT_URL, {4: "sentiment"})
    components = _read_columns(COMPONENTS_URL, {3: "current_conditions", 5: "expectations"})
    inflation = _read_columns(INFLATION_URL, {3: "inflation_1y", 5: "inflation_5y"})
    df = pd.concat([sentiment, components, inflation], axis=1).sort_index()
    save(df, "michigan_sentiment", "UMich消费者信心")


if __name__ == "__main__":
    main()
