#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "requests>=2.31"]
# ///
"""零售 — FRED 无 key CSV。月频,回溯 1992。每天可跑刷新。"""
from _common import fred, save


def main():
    df = fred([
        ("RSAFS",   "retail_food_services"),     # 零售及餐饮销售总额
        ("RSFSXMV", "retail_ex_autos"),          # 零售(剔除汽车及零部件)
    ])
    save(df, "retail", "零售")


if __name__ == "__main__":
    main()
