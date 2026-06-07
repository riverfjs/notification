#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "requests>=2.31"]
# ///
"""每週經濟指數 WEI(Lewis-Mertens-Stock)— FRED 无 key CSV。周频,回溯 2008。每天可跑刷新。"""
from _common import fred, save


def main():
    df = fred([
        ("WEI", "weekly_economic_index"),   # 周度经济指数(≈实际GDP同比)
    ])
    save(df, "wei", "每週經濟指數")


if __name__ == "__main__":
    main()
