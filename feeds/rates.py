#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "requests>=2.31"]
# ///
"""市場利率 & 政策利率 + 收益率曲线 — FRED 无 key CSV。日频,回溯 1962/1976/1982。每天可跑刷新。"""
from _common import fred, save


def main():
    df = fred([
        ("DGS3MO", "ust_3m"),       # 3个月国债收益率
        ("DGS2",   "ust_2y"),       # 2年
        ("DGS10",  "ust_10y"),      # 10年
        ("DFF",    "fed_funds_eff"),# 有效联邦基金利率(政策)
        ("T10Y2Y", "curve_10y_2y"), # 10年-2年期限利差(倒挂=衰退预警)
        ("T10Y3M", "curve_10y_3m"), # 10年-3月期限利差
    ])
    save(df, "rates", "市場&政策利率")


if __name__ == "__main__":
    main()
