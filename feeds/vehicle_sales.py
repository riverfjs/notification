#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26"]
# ///
"""汽車銷售 — 官方 FRED API。月频,回溯 1976。每天可跑刷新。
口径对齐网站(MacroMicro「轻型车辆销售=乘用车+轻卡」):
  total = 全部车辆(含中重卡)| light_vehicle = 轻型车辆(网站头条)| 再拆 autos / light_trucks。
(注:旧版把 LAUTOSA 误标成"轻卡"——其实 LAUTOSA=乘用车;真轻卡是 LTRUCKSA。已修正。)"""
from _common import fred, save


def main():
    df = fred([
        ("TOTALSA",  "total_vehicle_sales_m"),   # 全部车辆(含中重卡,年化百万)
        ("ALTSALES", "light_vehicle_sales_m"),   # 轻型车辆=乘用车+轻卡(网站头条口径)
        ("LAUTOSA",  "autos_m"),                 # 乘用车(轿车)
        ("LTRUCKSA", "light_trucks_m"),          # 轻型卡车(含 SUV/皮卡)
    ])
    save(df, "vehicle_sales", "汽車銷售")


if __name__ == "__main__":
    main()
