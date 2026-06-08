#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "requests>=2.31"]
# ///
"""銅金比 & PPI — 月频腿:铜/PPI 来自 FRED(IMF 月频);日频腿(P10,MacroMicro 同口径):
COMEX 铜期货 data/spot/COPPER.csv($/公吨,feeds/spot_copper.py 维护,2000-08+)。
金价统一用真现货 XAU/USD(data/spot/XAUUSD.csv,LBMA PM 定盘 1968+,feeds/spot_gold.py 维护;
先跑 spot_gold、spot_copper 再跑本脚本)。
铜金比 = 铜($/公吨)/ 金($/盎司),真实"吨铜值多少盎司金"口径(不再是 GLD 的 /10.85 失真):
  copper_usd_mt / copper_gold_ratio        月频(IMF,1992+,滞后 1-2 月)— 保留原列
  copper_fut_usd_mt / copper_gold_ratio_daily  日频(HG=F×2204.62,2000-08+)— MacroMicro 的日频口径
混频文件:月频列只在月初行有值,日频列只在交易日行有值,按列各自 dropna 后使用。
与 PPI(生产者通胀)对照;经典工业需求/再通胀温度计。每天可跑刷新。"""
from _common import fred, read_price, save


def main():
    df = fred([
        ("PCOPPUSDM", "copper_usd_mt"),    # 全球铜价($/公吨,月,1992+)
        ("PPIACO",    "ppi_all_commod"),   # PPI 全部商品(月)
    ])
    gold = read_price("XAUUSD")["c"]                      # 现货金 LBMA PM 定盘($/盎司)
    df["gold_usd_oz"] = gold.reindex(df.index, method="ffill")
    df["copper_gold_ratio"] = df["copper_usd_mt"] / df["gold_usd_oz"]
    # 日频腿(P10):铜期货 $/公吨 ÷ 当日(或最近一日)现货金 —— ffill 只用历史,因果安全
    copper_d = read_price("COPPER")["c"]                  # COMEX HG=F×2204.62($/公吨,日)
    daily = copper_d.to_frame("copper_fut_usd_mt")
    daily["copper_gold_ratio_daily"] = copper_d / gold.reindex(copper_d.index, method="ffill")
    save(df.join(daily, how="outer"), "copper_gold_ppi", "銅金比&PPI")


if __name__ == "__main__":
    main()
