#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "curl_cffi>=0.7"]
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

import time

from curl_cffi import requests as _curl

from _common import DATA_DIR

LBMA = "https://prices.lbma.org.uk/json/gold_{fix}.json"
OUT = os.path.join(DATA_DIR, "XAUUSD.csv")


def _fetch_json(url: str) -> list[dict]:
    """LBMA 站点(prices.lbma.org.uk)前置 Imunify360 机器人防护,对数据中心 IP
    【间歇性】拦截 —— 实测(2026-06,GitHub runner)同一 curl_cffi 代码有时拿到干净
    JSON、有时收到 415 / Imunify360 错误体 / JS 质询页,翻转取决于该次 Azure 出口
    IP 的实时信誉。这【不是】固定的可逆 JS 谜题,而是 flaky 风控,故对策是韧性而非逆向:
    curl_cffi 仿 Chrome 指纹(IP 干净时即放行)+ 多次拉开间隔重试骑过短暂质询窗口;
    彻底失败交由 main() 软处理(保留已落地的全量历史,下次自愈)。响应须为 [{'d',…}] 数组。"""
    last: Exception | str | None = None
    for a in range(5):
        try:
            r = _curl.get(url, impersonate="chrome", timeout=40)
            r.raise_for_status()
            rows = r.json()
            if isinstance(rows, list) and rows and isinstance(rows[0], dict) and "d" in rows[0]:
                return rows
            last = f"HTTP 200 但非价格数组(疑似 Imunify360 质询): {str(rows)[:80]}"
        except Exception as e:  # noqa: BLE001
            last = e
        time.sleep(3.0 * (a + 1))                         # 3/6/9/12s:骑过短质询窗口
    raise RuntimeError(f"LBMA 抓取失败: {url}\n  last: {str(last)[:150]}")


def _fix_series(fix: str) -> pd.Series:
    """One LBMA fix ('pm'/'am') -> Series of USD/oz (v = [USD, GBP, EUR])."""
    rows = _fetch_json(LBMA.format(fix=fix))
    rec = [(r["d"], r["v"][0]) for r in rows if r.get("v") and r["v"][0]]
    s = pd.Series(dict(rec), name="c")
    s.index = pd.to_datetime(s.index)
    return pd.to_numeric(s, errors="coerce").dropna().sort_index()


def main():
    try:
        pm, am = _fix_series("pm"), _fix_series("am")
    except RuntimeError as e:
        # Imunify360 间歇拦截:已有全量历史就软失败(保留旧文件,下次自愈),不红整条管线;
        # 首次运行(无缓存)才硬失败 —— 没有历史可退。
        if os.path.exists(OUT):
            old = pd.read_csv(OUT, index_col=0, parse_dates=True)
            print(f"!   XAUUSD              LBMA 本次被拦,保留旧缓存 "
                  f"({len(old)} rows ..{old.index.max().date()});下次自愈 — {str(e)[:80]}")
            return
        raise
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
