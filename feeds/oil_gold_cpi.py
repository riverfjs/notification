#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "requests>=2.31"]
# ///
"""油金比 & CPI — WTI(FRED 日频,1986+)、CPI(FRED 月频);金价用真现货 XAU/USD
(data/spot/XAUUSD.csv,LBMA PM 定盘 1968+,由 feeds/spot_gold.py 维护;先跑 spot_gold 再跑本脚本)。
油金比 = 油($/桶)/ 金($/盎司),真实"一盎司金换多少桶油"的倒数口径(不再是 GLD 的 /10.85 失真);
与 CPI(消费通胀)对照。比率覆盖 1986+。每天可跑刷新。"""
from _common import fred, read_price, save


def main():
    df = fred([
        ("DCOILWTICO", "wti_usd_bbl"),     # WTI 原油($/桶,日,1986+)
        ("CPIAUCSL",   "cpi_all_urban"),   # CPI 全部城市消费者(月)
    ])
    gold = read_price("XAUUSD")["c"]                      # 现货金 LBMA PM 定盘($/盎司)
    df["gold_usd_oz"] = gold.reindex(df.index, method="ffill")
    df["oil_gold_ratio"] = df["wti_usd_bbl"] / df["gold_usd_oz"]
    save(df, "oil_gold_cpi", "油金比&CPI")


if __name__ == "__main__":
    main()
