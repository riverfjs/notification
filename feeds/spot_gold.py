#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26"]
# ///
"""现货金 XAU/USD — LBMA 官方免费 JSON(prices.lbma.org.uk,无 key)→ data/XAUUSD.csv。

源即基准本身:LBMA Gold Price PM 定盘($/盎司,1968-04+,即原 FRED GOLDAMGBD228NLBM
的上游;FRED 该系列已因 ICE 授权整条下架)。PM 缺的日期用 AM 定盘补
(AM 1968-01 起,且伦敦上午 cron 跑时当日只有 AM)。

为什么不用别的源(2026-06 实测):
  - Stooq /q/d/l/?s=xauusd 现要求 apikey + JS proof-of-work 验证,cron 不可用;
  - yfinance XAUUSD=X 已 404;GC=F 是 COMEX 期货且仅 2000-08+,只作人工核对参考。

落地 data/XAUUSD.csv(date,c),read_price("XAUUSD")["c"] 即现货金,
供 copper_gold_ppi / oil_gold_cpi 替换 GLD(GLD≈金/10.85 且随 0.4%/年费率漂移,仅 2004+)。
全量覆盖、幂等;带 prices.py 同款守门(新数据回退/缩水则保留旧文件)。每天可跑刷新。"""
from __future__ import annotations

import os

import pandas as pd

from _common import DATA_DIR, _get

LBMA = "https://prices.lbma.org.uk/json/gold_{fix}.json"
OUT = os.path.join(DATA_DIR, "XAUUSD.csv")
_BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
               "(KHTML, like Gecko) Version/17.0 Safari/605.1.15")
# 同一官方 URL 的头部阶梯:本机默认头即 200,但 GitHub Actions 等数据中心 IP 会被
# 边缘网关挑剔地 415(2026-06 实测)——依次换更"像 JSON 客户端/浏览器"的头重试。
_HEADER_LADDER = [
    None,                                                  # _common 默认 UA
    {"User-Agent": _BROWSER_UA, "Accept": "application/json",
     "Content-Type": "application/json"},
    {"User-Agent": _BROWSER_UA, "Accept": "application/json, text/plain, */*",
     "Accept-Language": "en-GB,en;q=0.9", "Accept-Encoding": "gzip",
     "Referer": "https://www.lbma.org.uk/prices-and-data/precious-metal-prices"},
]


def _fetch_json(url: str):
    last = None
    for h in _HEADER_LADDER:
        try:
            return _get(url, retries=2, headers=h).json()
        except Exception as e:  # noqa: BLE001
            last = e
    raise RuntimeError(f"LBMA 全部头部组合失败: {url}\n  last: {str(last)[:150]}")


def _fix_series(fix: str) -> pd.Series:
    """One LBMA fix ('pm'/'am') -> Series of USD/oz (v = [USD, GBP, EUR])."""
    rows = _fetch_json(LBMA.format(fix=fix))
    rec = [(r["d"], r["v"][0]) for r in rows if r.get("v") and r["v"][0]]
    s = pd.Series(dict(rec), name="c")
    s.index = pd.to_datetime(s.index)
    return pd.to_numeric(s, errors="coerce").dropna().sort_index()


def main():
    pm, am = _fix_series("pm"), _fix_series("am")
    gold = pm.combine_first(am)                       # PM 为准,缺日用 AM 补
    if len(gold) < 10_000 or not (100 < gold.iloc[-1] < 50_000):
        raise RuntimeError(f"LBMA 数据异常: {len(gold)} rows, last={gold.iloc[-1]}")
    df = gold.to_frame()
    df.index.name = "date"
    if os.path.exists(OUT):                           # 守门:防坏返回毁掉好缓存
        old = pd.read_csv(OUT, index_col=0, parse_dates=True)
        if df.index.max() < old.index.max() or len(df) < 0.95 * len(old):
            raise RuntimeError(f"新数据回退/缩水({len(df)} rows ..{df.index.max().date()} "
                               f"vs 旧 {len(old)} rows ..{old.index.max().date()}),保留旧文件")
    df.to_csv(OUT)
    print(f"OK  XAUUSD              现货金(LBMA)  {len(df):>6} rows  "
          f"{df.index.min().date()}..{df.index.max().date()}  last={df['c'].iloc[-1]:.2f} USD/oz")


if __name__ == "__main__":
    main()
