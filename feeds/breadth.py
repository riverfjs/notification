#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26"]
# ///
"""標普500市場寬度 — 自算,不依赖任何付费源(逐股 $SPXA200R 见 feeds/breadth_stocks.py)。
用 11 个 GICS 行业 SPDR(标普的一个划分,无幸存者偏差;9 个原始 SPDR 回溯 1998,
XLRE 2015-10+、XLC 2018-06+)算「行业层」宽度:有几成行业收盘价在自己的 MA20/50/200 上方。
分母 = 当日有有效 MA 的行业数(早年自动只算存在的行业)。粗但深、干净、可每天跑。
他网站的规则:>50%=牛/<50%=熊(用 200日);≥85% 偏顶,≤15% 偏底。"""
import pandas as pd

from _common import read_price, save

SECTORS = ["XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"]


def main():
    closes = {}
    for t in SECTORS:
        try:
            closes[t] = read_price(t)["c"]
        except FileNotFoundError:
            print(f"  (缺 {t}.csv,跳过)")
    px = pd.DataFrame(closes).sort_index().dropna(how="all")
    out = pd.DataFrame(index=px.index)
    for k in (20, 50, 200):
        ma = px.rolling(k).mean()
        above = (px > ma).where(ma.notna())     # MA 不足时置 NaN,避免误判为「在下方」
        out[f"breadth{k}"] = above.mean(axis=1) * 100.0
    out["regime_bull"] = (out["breadth200"] > 50).astype("Int64")  # 牛熊线
    save(out.dropna(subset=["breadth50"]), "breadth", "標普500市場寬度")


if __name__ == "__main__":
    main()
