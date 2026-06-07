#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26"]
# ///
"""COT legacy 口径(MacroMicro 定义)— CFTC「Legacy - Futures Only」(Socrata 6dca-aqww)。

补充 cot_sp500/cot_nasdaq100(TFF 口径,2006+)拿不到的深历史:legacy 报告只分
non-commercial(投机盘)/ commercial(套保盘)两类,但 S&P 500 大合约回溯到 1986。
每个市场三列(原始合约数,不做归一化):
  {m}_noncomm_net   = noncomm_long − noncomm_short
  {m}_comm_net      = comm_long − comm_short
  {m}_cot_index_mm  = noncomm_net − comm_net   (MacroMicro 的「COT 指数」定义)
外加 {m}_oi(总持仓量,核对用)。市场:
  sp500_big   S&P 500 STOCK INDEX(大合约 $250,1986-01..2021-09 退市)
  sp500_emini E-MINI S&P 500(1997-09+,续更)
  ndx_big     NASDAQ-100 STOCK INDEX(大合约,1996-04..2015-06 退市)
  ndx_mini    NASDAQ MINI(E-mini NASDAQ-100,1999-06+,续更)
数据集为全历史快照(非滚动窗口),整表覆写幂等,cron 安全。周二数据周五 15:30 ET 公布。
不改动现有 cot_sp500 / cot_nasdaq100。"""
import urllib.parse

import pandas as pd

from _common import _get, save

BASE = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"  # Legacy - Futures Only

# prefix -> (cftc_contract_market_code, 说明)。用 code 而非名称查询:
# "NASDAQ-100 STOCK INDEX" 这个名字同时挂在 209601(1986 年孤行)和 209741 下,code 才唯一。
MARKETS = {
    "sp500_big":   ("138741", "S&P 500 STOCK INDEX (big $250, 1986-2021)"),
    "sp500_emini": ("13874A", "E-MINI S&P 500 (1997+)"),
    "ndx_big":     ("209741", "NASDAQ-100 STOCK INDEX (big, 1996-2015)"),
    "ndx_mini":    ("209742", "NASDAQ MINI / E-mini NASDAQ-100 (1999+)"),
}


def fetch_legacy(code: str) -> pd.DataFrame:
    """One market's full legacy futures-only history (weekly, by report date)."""
    cols = ["report_date_as_yyyy_mm_dd", "open_interest_all",
            "noncomm_positions_long_all", "noncomm_positions_short_all",
            "comm_positions_long_all", "comm_positions_short_all"]
    q = (f"?cftc_contract_market_code={urllib.parse.quote(code)}"
         f"&$select={','.join(cols)}"
         f"&$order=report_date_as_yyyy_mm_dd&$limit=50000")
    df = pd.DataFrame(_get(BASE + q).json())
    if df.empty:
        raise RuntimeError(f"cot_legacy: no rows for market code '{code}'")
    df["date"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"]).dt.tz_localize(None)
    df = (df.drop(columns=["report_date_as_yyyy_mm_dd"])
            .drop_duplicates(subset="date", keep="last")   # 修正报告取最新
            .set_index("date").sort_index())
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    out = pd.DataFrame(index=df.index)
    out["oi"] = df["open_interest_all"]
    out["noncomm_net"] = df["noncomm_positions_long_all"] - df["noncomm_positions_short_all"]
    out["comm_net"] = df["comm_positions_long_all"] - df["comm_positions_short_all"]
    out["cot_index_mm"] = out["noncomm_net"] - out["comm_net"]   # MacroMicro 定义
    return out


def main():
    parts = []
    for prefix, (code, _desc) in MARKETS.items():
        part = fetch_legacy(code)
        parts.append(part.add_prefix(f"{prefix}_"))
    df = pd.concat(parts, axis=1, sort=True).sort_index()
    save(df, "cot_legacy", "COT legacy口径")


if __name__ == "__main__":
    main()
