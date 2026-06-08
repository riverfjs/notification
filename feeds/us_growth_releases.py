#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26"]
# ///
"""US growth release data from official BEA NIPA TXT files.

No fallback: real GDP QoQ SAAR comes from BEA's official NIPA release TXT.
"""
from __future__ import annotations

import csv
import io
import re
import time
import urllib.request

import pandas as pd

from _common import UA, save

BEA_NIPA_Q = "https://apps.bea.gov/national/Release/TXT/NipaDataQ.txt"
SERIES = {"A191RL": "real_gdp_qoq_saar"}


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
    if not s or s == ".":
        return None
    return float(s)


def main():
    text = _get_text(BEA_NIPA_Q)
    rows_by_col: dict[str, list[tuple[pd.Timestamp, float]]] = {v: [] for v in SERIES.values()}
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        code = row.get("%SeriesCode") or row.get("SeriesCode")
        col = SERIES.get(code or "")
        if not col:
            continue
        period = row.get("Period", "")
        match = re.fullmatch(r"(\d{4})Q([1-4])", period)
        value = _to_float(row.get("Value", ""))
        if not match or value is None:
            continue
        month = (int(match[2]) - 1) * 3 + 1
        rows_by_col[col].append((pd.Timestamp(int(match[1]), month, 1), value))

    frames = []
    for col, rows in rows_by_col.items():
        if not rows:
            raise RuntimeError(f"BEA NIPA quarterly TXT missing {col}")
        frames.append(pd.DataFrame(rows, columns=["date", col]).set_index("date"))
    save(pd.concat(frames, axis=1).sort_index(), "us_growth_releases", "US增长发布")


if __name__ == "__main__":
    main()
