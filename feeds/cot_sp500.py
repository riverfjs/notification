#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "requests>=2.31"]
# ///
"""標普500 COT 指數 — CFTC「Traders in Financial Futures」(E-MINI S&P 500)。
免费 Socrata API(无需 token),周频回溯 2006。每天可跑刷新(周二报告周五公布)。
输出三类参与者净持仓 + 各自 0-100 的 COT 指数(净持仓 3 年滚动 Williams 指数 =(净−min)/(max−min)×100,
与 MacroMicro/网站口径一致)。lev_money=杠杆基金(对冲基金,投机盘)| asset_mgr=资管(真钱)| dealer=做市商(卖方)"""
from _common import cot_tff, save


def main():
    df = cot_tff("E-MINI S&P 500")
    save(df, "cot_sp500", "標普500 COT")


if __name__ == "__main__":
    main()
