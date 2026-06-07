#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "requests>=2.31"]
# ///
"""納斯達克100 COT 指數 — CFTC TFF(E-mini Nasdaq-100,CFTC 名「NASDAQ MINI」)。
免费 Socrata,周频回溯 2006。每天可跑刷新。字段/口径同 cot_sp500(COT 指数为 Williams max-min)。"""
from _common import cot_tff, save


def main():
    df = cot_tff("NASDAQ MINI")
    save(df, "cot_nasdaq100", "納指100 COT")


if __name__ == "__main__":
    main()
