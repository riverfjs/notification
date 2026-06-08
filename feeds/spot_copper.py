#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["yfinance>=0.2.40", "pandas>=2.0", "numpy>=1.26", "lxml>=5.0"]
# ///
"""日频铜价($/公吨)→ data/spot/COPPER.csv(date,c,与 data/spot/XAUUSD.csv 同 schema)。

口径(2026-06 实测对齐 MacroMicro):
  2008-01+  LME 铜 Cash-Settlement(官方结算价,$/公吨)— Westmetall 免费年度归档页
            westmetall.com/en/markdaten.php?action=table&field=LME_Cu_cash&year=YYYY
            (2008 之前年份页为空;结算价 T+1 发布,日频缓 1 个交易日)
  2000-08..2007-12  COMEX 铜期货连续合约 HG=F(yfinance,$/磅)×2204.62=$/公吨,
            补 LME 归档前的历史腿。

为什么不全用 HG=F:2024 起美国铜关税预期把 COMEX 拉出对 LME 的持续溢价
(2025 中位 +5.3%,2026-06-04 实测 +3.5%),铜金比会系统性高 ~0.1;
MacroMicro 的日频铜金比用的是 LME(2026-06-04:LME 13872/金 4496.95=3.085≈其 3.07)。
两腿在 2008 接缝处实测溢价中位 0.06%(2008-2023 全程 ±1% 内),原值拼接、无缩放。

落地 data/spot/COPPER.csv(date,c),read_price("COPPER")["c"] 即日频铜价($/公吨),
供 copper_gold_ppi.py 的日频铜金比。全量覆盖、幂等(年度页是完整静态归档,每次重拉
2008..今全部年份,~19 个小页);带 prices.py 同款守门(新数据回退/缩水保留旧文件)。
注意:列只有 c(非 OHLCV),prices.py 的 discover() 按 header 自动跳过本文件。"""
from __future__ import annotations

import io
import os
import time
from datetime import date

import pandas as pd

from _common import SPOT_DIR, _get

LB_PER_MT = 2204.62                                   # 磅/公吨
LME_FIRST_YEAR = 2008                                 # Westmetall LME_Cu_cash 归档起点
WM = ("https://www.westmetall.com/en/markdaten.php"
      "?action=table&field=LME_Cu_cash&year={y}")
WM_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36", "Accept": "*/*"}
OUT = os.path.join(SPOT_DIR, "COPPER.csv")


def _lme_year(year: int) -> pd.Series:
    """Westmetall 一个年份页 -> LME Cash-Settlement Series($/公吨)。"""
    html = _get(WM.format(y=year), headers=WM_UA).text
    for t in pd.read_html(io.StringIO(html)):
        if not any("Cash-Settlement" in str(c) for c in t.columns):
            continue
        t = t[t.iloc[:, 0] != "date"]                 # 表内重复表头行
        idx = pd.to_datetime(t.iloc[:, 0], format="%d. %B %Y", errors="coerce")
        val = pd.to_numeric(t.iloc[:, 1], errors="coerce")
        return pd.Series(val.values, index=idx.values).dropna()
    return pd.Series(dtype=float)


def lme_cash() -> pd.Series:
    parts = []
    for y in range(LME_FIRST_YEAR, date.today().year + 1):
        parts.append(_lme_year(y))
        time.sleep(0.3)
    s = pd.concat(parts).sort_index()
    return s[~s.index.duplicated(keep="last")]


def hg_futures() -> pd.Series:
    """yfinance HG=F 全历史日线收盘($/磅)× 2204.62 = $/公吨(2000-08+)。"""
    import yfinance as yf
    df = yf.download("HG=F", start="1900-01-01", progress=False, auto_adjust=True)
    if df is None or df.empty:
        raise RuntimeError("yfinance HG=F 返回空")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)   # (Price, Ticker) -> Price
    s = pd.to_numeric(df["Close"], errors="coerce").dropna() * LB_PER_MT
    s.index = pd.to_datetime(s.index).tz_localize(None)
    return s.sort_index()


def main():
    lme = lme_cash()
    if len(lme) < 4_000 or not (1_000 < lme.iloc[-1] < 100_000):
        raise RuntimeError(f"LME 数据异常: {len(lme)} rows, last={lme.iloc[-1]}")
    seam = lme.index.min()                            # 2008-01-02
    try:
        pre = hg_futures()[lambda s: s.index < seam]
    except Exception as e:  # noqa: BLE001            # HG 腿失败:用旧缓存里的 seam 前历史
        if not os.path.exists(OUT):
            raise
        cached = pd.read_csv(OUT, index_col=0, parse_dates=True)["c"]
        pre = cached[cached.index < seam]
        print(f"  ! HG=F 拉取失败,seam 前历史沿用旧缓存 {len(pre)} 行 ({str(e)[:80]})")
    df = pd.concat([pre, lme]).sort_index().to_frame("c")
    df.index.name = "date"
    if os.path.exists(OUT):                           # 守门:防坏返回毁掉好缓存
        old = pd.read_csv(OUT, index_col=0, parse_dates=True)
        if df.index.max() < old.index.max() or len(df) < 0.95 * len(old):
            raise RuntimeError(f"新数据回退/缩水({len(df)} rows ..{df.index.max().date()} "
                               f"vs 旧 {len(old)} rows ..{old.index.max().date()}),保留旧文件")
    os.makedirs(SPOT_DIR, exist_ok=True)
    df.to_csv(OUT)
    print(f"OK  COPPER              铜 LME+HG 拼接 {len(df):>6} rows  "
          f"{df.index.min().date()}..{df.index.max().date()}  "
          f"last={df['c'].iloc[-1]:.2f} USD/mt  (LME 段 {seam.date()}+,{len(lme)} 行)")


if __name__ == "__main__":
    main()
