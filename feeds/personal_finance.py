#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "requests>=2.31"]
# ///
"""個人財務狀況 — FRED 无 key CSV。月频,回溯 1959。每天可跑刷新。"""
from _common import fred, save


def main():
    df = fred([
        ("PI",      "personal_income"),          # 个人收入
        ("DSPIC96", "real_disposable_income"),   # 实际可支配收入
        ("PSAVERT", "personal_saving_rate_pct"), # 个人储蓄率(%)
    ])
    save(df, "personal_finance", "個人財務狀況")


if __name__ == "__main__":
    main()
