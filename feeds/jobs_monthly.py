#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "requests>=2.31"]
# ///
"""就業(月频)— FRED 官方 API。非农 PAYEMS + 失业率 UNRATE,同属每月就业报告(Employment
Situation),日期天然对齐;裁到两列同时有值的区间(1948-01+),整文件无 NaN,可整行使用。
周频初请失业金拆到 claims_weekly.py(取代旧 jobs_employment.py 的混频文件)。每天可跑刷新。"""
from _common import fred, save


def main():
    df = fred([
        ("PAYEMS", "nonfarm_payrolls_k"),     # 非农就业人数(千)
        ("UNRATE", "unemployment_rate_pct"),  # 失业率(%)
    ])
    # PAYEMS 1939+ / UNRATE 1948+:取交集起点,保证两列 100% 非空(月频内无洞)
    df = df.dropna()
    save(df, "jobs_monthly", "就業(月)")


if __name__ == "__main__":
    main()
