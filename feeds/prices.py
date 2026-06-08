#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["yfinance>=0.2.40", "pandas>=2.0", "numpy>=1.26"]
# ///
"""价格缓存刷新 — 把 data/tickers/ 下所有已有 ticker 的 CSV(date,o,h,l,c,v)用 yfinance 全量重拉。

口径与 research/data.py(已归档)的 fetch 完全一致:auto_adjust=True(分红+拆股复权)、列
o/h/l/c/v。但彼有缓存就跳过,本脚本是「刷新」:每次全量 re-download 并整文件覆盖 —— 复权价会随
每次新分红回溯漂移,增量 append 会留下新旧两套复权口径混在一个文件里,所以必须全量。

幂等、cron 安全:仅当新数据「非空 + 最新日期不倒退 + 行数不缩水(≥95%)」时才覆盖,
任何一条不满足就保留旧文件并告警(防止 yfinance 偶发空返回毁掉好缓存,如已停更的 ^VXO)。

cron 顺序:prices → run_all(breadth / sector_strength 读这些价格缓存,必须先刷价再算指标;
建议在美股收盘后跑,盘中跑会带入当日未完成的 bar,下一次运行会自动覆盖修正)。

    uv run feeds/prices.py            # 刷新 data/tickers/ 下全部 ticker
    uv run feeds/prices.py SPY XLK    # 只刷指定 ticker
"""
from __future__ import annotations

import os
import sys
import time

import pandas as pd

from _common import TICKER_DIR

# 文件名 -> yfinance 代码(指数需要 ^ 前缀;文件名不能带 ^)
SYMBOL_MAP = {"VIX": "^VIX", "VXO": "^VXO"}
# 非 yfinance 价格缓存,跳过:XAUUSD = 现货金,归 feeds/spot_gold.py 管;
# COPPER = 现货铜,归 feeds/spot_copper.py 管;FNG_long = 旧研究遗留,已归档到 data/legacy/。
SKIP = {"FNG_long", "XAUUSD", "COPPER"}
OHLCV = ["o", "h", "l", "c", "v"]


def discover() -> list[str]:
    """data/tickers/ 下所有 schema 为 date,o,h,l,c,v 的 ticker 文件(后续新增自动纳入)。"""
    os.makedirs(TICKER_DIR, exist_ok=True)
    out = []
    for fn in sorted(os.listdir(TICKER_DIR)):
        if not fn.endswith(".csv"):
            continue
        t = fn[:-4]
        if t in SKIP:
            continue
        with open(os.path.join(TICKER_DIR, fn)) as f:
            header = f.readline().strip().lower().split(",")
        if header == ["date"] + OHLCV:   # 双保险:非 OHLCV schema 一律不碰
            out.append(t)
    return out


def download(symbol: str) -> pd.DataFrame:
    """同 data.py:auto_adjust 全历史日线,列重命名为 o/h/l/c/v。"""
    import yfinance as yf
    df = yf.download(symbol, start="1900-01-01", progress=False, auto_adjust=True)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)              # (Price, Ticker) -> Price
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.columns = OHLCV
    df.index.name = "date"
    return df.sort_index()


def refresh(ticker: str) -> bool:
    if ticker in SKIP:
        print(f"  ! {ticker}: 非 yfinance/ticker 缓存,跳过")
        return False
    path = os.path.join(TICKER_DIR, f"{ticker}.csv")
    if not os.path.exists(path):
        print(f"  ! {ticker}: 未找到 {path},跳过")
        return False
    old = pd.read_csv(path, index_col=0, parse_dates=True)
    old_last, old_n = old.index.max(), len(old)
    try:
        new = download(SYMBOL_MAP.get(ticker, ticker))
    except Exception as e:  # noqa: BLE001
        print(f"  ! {ticker}: 下载失败,保留旧缓存 ({str(e)[:90]})")
        return False
    if new.empty:
        print(f"  ! {ticker}: yfinance 返回空,保留旧缓存 (..{old_last.date()})")
        return False
    if new.index.max() < old_last:
        print(f"  ! {ticker}: 新数据最新日 {new.index.max().date()} < 旧 {old_last.date()},保留旧缓存")
        return False
    if len(new) < 0.95 * old_n:
        print(f"  ! {ticker}: 新数据仅 {len(new)} 行 < 旧 {old_n} 的 95%,疑似截断,保留旧缓存")
        return False
    new.to_csv(path)
    print(f"  {ticker}: {len(new)} rows {new.index[0].date()}..{new.index[-1].date()}"
          f"  (was {old_n} rows ..{old_last.date()})")
    return True


def main():
    tickers = sys.argv[1:] or discover()
    ok, fail = 0, []
    for t in tickers:
        if refresh(t):
            ok += 1
        else:
            fail.append(t)
        time.sleep(0.5)                                          # 对 yahoo 礼貌限速
    print(f"\n=== prices: 刷新 {ok}/{len(tickers)} ===")
    if fail:
        print(f"未刷新(保留旧缓存): {fail}")


if __name__ == "__main__":
    main()
