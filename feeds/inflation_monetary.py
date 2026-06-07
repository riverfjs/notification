#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "requests>=2.31"]
# ///
"""通貨膨脹 & 貨幣政策預期 — FRED 官方 API。日频。每天可跑刷新。
盈亏平衡通胀 = 市场隐含通胀预期(2003+);fed_funds_target = 联邦基金目标利率,
由 DFEDTAR(单点目标,1982-09-27..2008-12-15)与 DFEDTARU(目标区间上限,
2008-12-16+)拼接成单列 — 2008-12-16 起 Fed 改公布目标区间,旧序列停更,
两段在 2008-12-15(1.00)→ 2008-12-16(0.25)处无缝衔接(当天即降息 75bp)。"""
import pandas as pd

from _common import fred, save

SEAM = pd.Timestamp("2008-12-16")  # DFEDTARU(目标区间上限)起点;DFEDTAR 终于前一天


def main():
    raw = fred([
        ("T5YIE",    "breakeven_5y"),   # 5年盈亏平衡通胀
        ("T10YIE",   "breakeven_10y"),  # 10年盈亏平衡通胀
        ("T5YIFR",   "fwd_5y5y_infl"),  # 5年/5年远期通胀预期
        ("DFEDTAR",  "_tar_point"),     # 联邦基金单点目标(1982-09-27..2008-12-15,已停更)
        ("DFEDTARU", "_tar_upper"),     # 联邦基金目标区间上限(2008-12-16+)
    ])
    # 拼接:严格按日期切换,SEAM 前用旧单点目标,SEAM 起用区间上限(因果、无重叠)
    raw["fed_funds_target"] = pd.concat([
        raw.loc[raw.index < SEAM, "_tar_point"],
        raw.loc[raw.index >= SEAM, "_tar_upper"],
    ])
    df = raw.drop(columns=["_tar_point", "_tar_upper"])
    save(df, "inflation_monetary", "通膨&貨幣預期")


if __name__ == "__main__":
    main()
