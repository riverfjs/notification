"""Shared helpers for the feeds/ fetchers (the ONLY shared module).

Every chart has its own runnable file in this folder; they all call into here so the
fetch/cache logic lives in ONE place. Each fetcher overwrites its CSV with the FULL
series on every run, so it is idempotent and safe to cron daily.

FRED data goes through the OFFICIAL FRED API (api.stlouisfed.org) with an API key — no
fallback, no scraping. Outputs go to ../data/macro/<name>.csv ; the price cache (for
breadth/sector) is ../data/.
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request

import numpy as np
import pandas as pd

UA = {"User-Agent": "feeds-macro-etl/1.0 (personal research)", "Accept": "*/*"}
HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(HERE, "..", "data"))        # existing price cache
MACRO_DIR = os.path.join(DATA_DIR, "macro")                          # our output
FRED_API = "https://api.stlouisfed.org/fred/series/observations"


class _Resp:
    """Tiny response wrapper exposing .text/.content/.json()."""

    def __init__(self, content: bytes):
        self.content = content

    @property
    def text(self) -> str:
        return self.content.decode("utf-8", "replace")

    def json(self):
        return json.loads(self.content)


def _get(url: str, retries: int = 4, pause: float = 1.5, timeout: int = 40,
         headers: dict | None = None, referer: str | None = None) -> _Resp:
    """Plain stdlib-urllib GET with simple retry. Used for the non-FRED sources
    (CFTC Socrata, NAAIM). No transport fallback."""
    h = dict(headers or UA)
    if referer:
        h["Referer"] = referer
    last = None
    for a in range(retries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":   # 客户端声明了
                    import gzip                                      # Accept-Encoding 时
                    data = gzip.decompress(data)
            if data:
                return _Resp(data)
            last = "empty body"
        except Exception as e:  # noqa: BLE001
            last = str(e)[:100]
        time.sleep(pause * (a + 1))
    raise RuntimeError(f"fetch failed after {retries}x: {url}\n  last: {last}")


def _fred_key() -> str:
    k = os.environ.get("FRED_API_KEY")
    if k:
        return k.strip()
    p = os.path.join(HERE, ".fred_api_key")
    if os.path.exists(p):
        with open(p) as f:
            return f.read().strip()
    raise RuntimeError("缺少 FRED API key:设环境变量 FRED_API_KEY 或写入 feeds/.fred_api_key")


def fred(series: list[tuple[str, str]], retries: int = 4, polite: float = 0.4) -> pd.DataFrame:
    """Fetch FRED series via the OFFICIAL API (JSON) and outer-join on date.
    series = [(series_id, friendly_column_name), ...]. Missing values ('.') -> NaN.
    Pure API, no fallback."""
    key = _fred_key()
    frames = []
    for sid, name in series:
        q = urllib.parse.urlencode({"series_id": sid, "api_key": key, "file_type": "json"})
        last = None
        for a in range(retries):
            try:
                req = urllib.request.Request(f"{FRED_API}?{q}", headers=UA)
                with urllib.request.urlopen(req, timeout=40) as resp:
                    obs = json.loads(resp.read())["observations"]
                break
            except Exception as e:  # noqa: BLE001
                last = str(e)[:100]
                time.sleep(1.5 * (a + 1))
        else:
            raise RuntimeError(f"FRED API 失败 {sid}: {last}")
        s = pd.DataFrame(obs)
        s["date"] = pd.to_datetime(s["date"])
        s[name] = pd.to_numeric(s["value"], errors="coerce")   # '.' -> NaN
        frames.append(s.set_index("date")[[name]])
        time.sleep(polite)
    return pd.concat(frames, axis=1).sort_index()


def cot_tff(contract_name: str, lookback_weeks: int = 156) -> pd.DataFrame:
    """CFTC 'Traders in Financial Futures' (futures-only) via the no-token Socrata API.
    Returns weekly net positions for the 3 reportable groups plus a 0-100 COT INDEX
    (Williams-style trailing percentile of net position) for each.
      lev_money = Leveraged Funds (hedge funds / CTAs = speculative)
      asset_mgr = Asset Managers (institutional 'real money')
      dealer    = Dealers / intermediaries (sell-side)
    """
    base = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
    cols = ["report_date_as_yyyy_mm_dd", "open_interest_all",
            "dealer_positions_long_all", "dealer_positions_short_all",
            "asset_mgr_positions_long", "asset_mgr_positions_short",
            "lev_money_positions_long", "lev_money_positions_short"]
    q = (f"?contract_market_name={urllib.parse.quote(contract_name)}"
         f"&$select={','.join(cols)}"
         f"&$order=report_date_as_yyyy_mm_dd&$limit=50000")
    df = pd.DataFrame(_get(base + q).json())
    if df.empty:
        raise RuntimeError(f"COT: no rows for contract '{contract_name}'")
    df["date"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"]).dt.tz_localize(None)
    df = df.set_index("date").drop(columns=["report_date_as_yyyy_mm_dd"]).sort_index()
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    out = pd.DataFrame(index=df.index)
    out["open_interest"] = df["open_interest_all"]
    groups = {"lev_money": "lev_money_positions", "asset_mgr": "asset_mgr_positions",
              "dealer": "dealer_positions"}
    for g, pref in groups.items():
        lo = df[f"{pref}_long_all"] if f"{pref}_long_all" in df else df[f"{pref}_long"]
        sh = df[f"{pref}_short_all"] if f"{pref}_short_all" in df else df[f"{pref}_short"]
        net = lo - sh
        out[f"{g}_net"] = net
        out[f"{g}_cot_index"] = williams_index(net, lookback_weeks)  # 0-100 Williams (max-min)
    return out


def williams_index(s: pd.Series, window: int) -> pd.Series:
    """Canonical Williams 'COT index' = (x - min)/(max - min)*100 over the trailing
    window, 0-100 (causal). This is the conventional COT-index normalization used by
    MacroMicro / TheMarketMemo, so values line up with the website."""
    mp = max(20, window // 4)
    lo = s.rolling(window, min_periods=mp).min()
    hi = s.rolling(window, min_periods=mp).max()
    rng = (hi - lo).where(lambda r: r != 0)
    return (s - lo) / rng * 100.0


def read_price(ticker: str) -> pd.DataFrame:
    """Read an existing OHLCV price cache CSV from ../data/<ticker>.csv."""
    return pd.read_csv(os.path.join(DATA_DIR, f"{ticker}.csv"), index_col=0, parse_dates=True)


def save(df: pd.DataFrame, name: str, label: str = "") -> str:
    """Write df to ../data/macro/<name>.csv and print a one-line landing summary."""
    os.makedirs(MACRO_DIR, exist_ok=True)
    df = df.dropna(how="all").sort_index()
    path = os.path.join(MACRO_DIR, f"{name}.csv")
    df.to_csv(path)
    first, last, n = df.index.min(), df.index.max(), len(df)
    cov = " | ".join(f"{c}:{int(df[c].notna().sum())}" for c in df.columns)
    print(f"OK  {name:<20}{label:<16}{n:>6} rows  {first.date()}..{last.date()}")
    print(f"      cols(non-null)  {cov}")
    return path
