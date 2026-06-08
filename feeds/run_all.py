#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "openpyxl>=3.1", "xlrd>=2.0",
#                 "yfinance>=0.2.40", "lxml>=5.0", "curl_cffi>=0.7"]
# ///
"""跑全部 30 个 feed,逐个容错,最后汇总。每天刷新一行 cron 即可(美股收盘后跑):
    uv run /home/river_fan/code/notification/feeds/run_all.py
单独跑某一个:uv run feeds/rates.py 等。输出:宏观 CSV 在 ../data/macro/,价格缓存在 ../data/tickers/ 和 ../data/spot/。
顺序有依赖:prices(价格缓存)与 spot_gold(现货金)在前,铜金/油金/breadth/sector 在后。"""
import importlib
import sys
import time
import traceback

MODULES = [
    "prices",                                                  # 价格缓存刷新(yfinance)
    "spot_gold", "spot_copper",                                # 现货金(LBMA)/铜(LME+HG拼接),供比率图
    "jobs_monthly", "claims_weekly", "personal_finance",
    "home_sales_prices", "vehicle_sales", "retail",
    "housing_supply", "mfg_orders_pmi", "wei",
    "us_inflation_releases", "us_growth_releases", "us_trade_orders", "michigan_sentiment",
    "copper_gold_ppi", "oil_gold_cpi", "inflation_monetary",
    "rates", "credit_spread",                                  # 14 FRED(官方 API)
    "ism_pmi", "naaim", "cot_sp500", "cot_nasdaq100",
    "cot_legacy",                                              # legacy 口径 COT(1986+,MacroMicro 定义)
    "aaii", "putcall", "putcall_cboe", "fng",                  # 9 下载(镜像/官方免费/CNN)
    "breadth", "breadth_official", "breadth_stocks",           # 行业宽度/官方$S5xx/时点成分自算
    "sector_strength",                                         # 4 宽度&板块
]


def main():
    ok, fail = [], []
    for name in MODULES:
        try:
            mod = importlib.import_module(name)
            mod.main()
            ok.append(name)
        except Exception as e:  # noqa: BLE001
            print(f"XX  {name:<20}失败: {str(e)[:150]}", file=sys.stderr)
            traceback.print_exc(limit=1)
            fail.append(name)
        time.sleep(1.0)
    print(f"\n=== 完成 {len(ok)}/{len(MODULES)} ===")
    if fail:
        print(f"失败: {fail}")
        sys.exit(1)                          # 非零退出:让 cron/GitHub Actions 能感知失败


if __name__ == "__main__":
    main()
