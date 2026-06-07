#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "requests>=2.31"]
# ///
"""供給:建房許可、新開工 & 庫存 — FRED 无 key CSV。月频,回溯 1959/1960。每天可跑刷新。"""
from _common import fred, save


def main():
    df = fred([
        ("PERMIT", "building_permits_k"),    # 营建许可(千,年化)
        ("HOUST",  "housing_starts_k"),      # 新屋开工(千,年化)
        ("MSACSR", "months_supply_new"),     # 新房库存月数
    ])
    save(df, "housing_supply", "建房許可/開工/庫存")


if __name__ == "__main__":
    main()
