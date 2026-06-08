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

import numpy as np
import pandas as pd

from _common import TICKER_DIR

# 文件名 -> yfinance 代码(指数需要 ^ 前缀;文件名不能带 ^)
SYMBOL_MAP = {"VIX": "^VIX", "VXO": "^VXO"}
# 非 yfinance 价格缓存,跳过:XAUUSD = 现货金,归 feeds/spot_gold.py 管;
# COPPER = 现货铜,归 feeds/spot_copper.py 管;FNG_long = 旧研究遗留,已归档到 data/legacy/。
SKIP = {"FNG_long", "XAUUSD", "COPPER"}
OHLCV = ["o", "h", "l", "c", "v"]
PRICE_COLS = ["o", "h", "l", "c"]
PRICE_NOISE_ABS = 1e-3


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


def stabilize_overlap(old: pd.DataFrame, new: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """Keep old overlap rows when yfinance only changed sub-cent float noise.

    yfinance adjusted prices can differ by ~1e-4 between identical full-history
    requests. Keeping equivalent overlap rows avoids false full-file Git diffs,
    while real split/dividend/revision changes still pass through.
    """
    out = new.copy()
    overlap = old.index.intersection(new.index)
    if overlap.empty:
        return out, 0, 0

    old_px = old.loc[overlap, PRICE_COLS].astype(float)
    new_px = new.loc[overlap, PRICE_COLS].astype(float)
    price_material = (new_px - old_px).abs().gt(PRICE_NOISE_ABS).any(axis=1)

    old_v = old.loc[overlap, "v"].fillna(-1).astype(np.int64)
    new_v = new.loc[overlap, "v"].fillna(-1).astype(np.int64)
    volume_material = old_v.ne(new_v)

    equivalent = overlap[~(price_material | volume_material)]
    if len(equivalent):
        out.loc[equivalent, OHLCV] = old.loc[equivalent, OHLCV]
    return out, len(equivalent), len(overlap) - len(equivalent)


def same_frame(a: pd.DataFrame, b: pd.DataFrame) -> bool:
    if not a.index.equals(b.index) or list(a.columns) != list(b.columns):
        return False
    return bool(np.array_equal(a[OHLCV].to_numpy(), b[OHLCV].to_numpy()))


def can_append_only(old: pd.DataFrame, stable: pd.DataFrame, material: int) -> pd.DataFrame:
    """Return strictly new trailing rows when old text can be preserved."""
    if material:
        return pd.DataFrame()
    if len(old.index.difference(stable.index)):
        return pd.DataFrame()
    new_rows = stable.loc[stable.index.difference(old.index)].sort_index()
    if new_rows.empty or new_rows.index.min() <= old.index.max():
        return pd.DataFrame()
    return new_rows


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
    stable, kept, material = stabilize_overlap(old, new)
    if same_frame(stable, old):
        print(f"  {ticker}: 无实质变化 {len(new)} rows {new.index[0].date()}..{new.index[-1].date()}"
              f"  (kept {kept} overlap rows)")
        return True
    append_rows = can_append_only(old, stable, material)
    if not append_rows.empty:
        append_rows.to_csv(path, mode="a", header=False)
        print(f"  {ticker}: append {len(append_rows)} rows {append_rows.index[0].date()}..{append_rows.index[-1].date()}"
              f"  (was {old_n} rows ..{old_last.date()}, kept {kept} overlap rows)")
        return True
    stable.to_csv(path)
    print(f"  {ticker}: {len(stable)} rows {stable.index[0].date()}..{stable.index[-1].date()}"
          f"  (was {old_n} rows ..{old_last.date()}, kept {kept} overlap rows, material {material})")
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
