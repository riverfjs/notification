#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26"]
# ///
"""板塊強度 — 自算,免费。全部 11 个 GICS 行业 ETF(XLRE 2015-10+、XLC 2018-06+)
相对 SPY 的强弱。每个行业输出两组列(每天可跑刷新):
  {t}_rs63    63 日(约 3 月)相对收益 = 行业涨幅 − SPY 涨幅(>0=跑赢;上市前 NaN)
  {t}_rs_line 累计 RS 线 = 行业收盘/SPY 收盘,在该 ETF 首个有效交易日重基为 1.0
              (MacroMicro 同口径的 relative-strength line;>1=自上市以来累计跑赢)"""
import pandas as pd

from _common import read_price, save

SECTORS = ["XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"]
LB = 63  # 约 3 个月


def main():
    closes = {}
    for t in SECTORS + ["SPY"]:
        try:
            closes[t] = read_price(t)["c"]
        except FileNotFoundError:
            print(f"  (缺 {t}.csv,跳过)")
    px = pd.DataFrame(closes).sort_index().dropna(how="all")
    spy_ret = px["SPY"] / px["SPY"].shift(LB) - 1
    out = pd.DataFrame(index=px.index)
    for t in SECTORS:
        if t in px:
            out[f"{t}_rs63"] = (px[t] / px[t].shift(LB) - 1) - spy_ret
    for t in SECTORS:  # 累计 RS 线:行业/SPY,首个有效日重基 1.0(因果,与窗口无关)
        if t in px:
            ratio = px[t] / px["SPY"]
            out[f"{t}_rs_line"] = ratio / ratio.loc[ratio.first_valid_index()]
    save(out.dropna(how="all"), "sector_strength", "板塊強度(vs SPY)")


if __name__ == "__main__":
    main()
