#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "requests>=2.31"]
# ///
"""初請失業金(周频)— FRED 官方 API。ICSA 1967+,周度(周六截止)。
月频非农/失业率拆到 jobs_monthly.py(取代旧 jobs_employment.py 的混频文件)。每天可跑刷新。"""
from _common import fred, save


def main():
    df = fred([
        ("ICSA", "initial_claims_weekly"),  # 初请失业金人数(周,SA)
    ])
    save(df, "claims_weekly", "初請失業金(周)")


if __name__ == "__main__":
    main()
