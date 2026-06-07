#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "requests>=2.31"]
# ///
"""製造業訂單 & 採購 — FRED 无 key CSV。月频,回溯 1992。每天可跑刷新。

注意:ISM 製造業 PMI 因授权 2016 后从 FRED 撤下,无免费可编程源。
这里用耐用品/制造业新订单 + 两个地区联储制造业指数(费城、纽约)作为 PMI 同类替代。"""
from _common import fred, save


def main():
    df = fred([
        ("DGORDER",            "durable_goods_orders"),   # 耐用品新订单
        ("AMTMNO",             "mfg_new_orders_total"),   # 制造业新订单总额
        ("GACDFSA066MSFRBPHI", "philly_fed_mfg"),         # 费城联储制造业现况(PMI 替代)
        ("GACDISA066MSFRBNY",  "ny_fed_mfg"),             # 纽约联储 Empire 制造业(PMI 替代)
    ])
    save(df, "mfg_orders_pmi", "製造業訂單&採購")


if __name__ == "__main__":
    main()
