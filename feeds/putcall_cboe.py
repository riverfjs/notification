#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26"]
# ///
"""期權 P/C 比(CBOE 聚合口径,2019-10-07+ 續作)— CBOE 每日市场统计页 `?dt=` 历史查询。
与 MacroMicro「CBOE Total/Equity Put/Call Ratio」同源同口径(芝加哥期权交易所官方聚合)。

衔接:免费归档 putcall.csv 止于 2019-10-04(老统计系统);本接口恰从 2019-10-07 起,
首尾相接、量级连续(equity 0.65→0.70),但无重叠段可逐位证同基 —— 拼长图时在
2019-10 处标注"统计系统切换"。

累积缓存:已检查过的日期(含假日 NaN 标记行)不再重抓;每日 cron 只新增 1-3 个请求。
首跑回填 2019-10-07 至今 ~1670 个交易日(每页 ~400KB、礼貌间隔,约 15-30 分钟),
每 100 天落盘一次,中断可续。"""
import os
import re
import time

import pandas as pd

from _common import MACRO_DIR, _get

URL = "https://www.cboe.com/markets/us/options/market-statistics/daily?dt={d}"
START = "2019-10-07"          # dt 接口最早可得(= 老归档冻结后的下一交易日,实测)
OUT = "putcall_cboe"
RATIOS = {                    # 列名 -> 页内字段名
    "total_pc":  "TOTAL PUT/CALL RATIO",
    "index_pc":  "INDEX PUT/CALL RATIO",
    "etp_pc":    "EXCHANGE TRADED PRODUCTS PUT/CALL RATIO",
    "equity_pc": "EQUITY PUT/CALL RATIO",
}
COLS = list(RATIOS) + ["call_volume", "put_volume"]


def fetch_day(ds: str) -> dict:
    """返回当日各比率;无数据(假日)返回全 NaN 标记行(缓存后不再重查)。"""
    html = _get(URL.format(d=ds), retries=3, pause=2.0, timeout=35).text
    row = {c: float("nan") for c in COLS}
    for col, name in RATIOS.items():
        m = re.search(re.escape(name) + r".{0,30}?([0-9]+\.[0-9]+)", html)
        if m:
            row[col] = float(m.group(1))
    m = re.search(r"SUM OF ALL PRODUCTS.{0,500}?VOLUME.{0,80}?([0-9][0-9,]{3,}).{0,40}?([0-9][0-9,]{3,})",
                  html, re.S)
    if m:
        row["call_volume"] = float(m.group(1).replace(",", ""))
        row["put_volume"] = float(m.group(2).replace(",", ""))
    return row


def main():
    os.makedirs(MACRO_DIR, exist_ok=True)
    path = os.path.join(MACRO_DIR, f"{OUT}.csv")
    old = (pd.read_csv(path, index_col=0, parse_dates=True)
           if os.path.exists(path) else pd.DataFrame(columns=COLS))
    have = set(old.index)
    todo = [d for d in pd.bdate_range(START, pd.Timestamp.today().normalize())
            if d not in have]

    def flush(rows):
        nonlocal old
        if rows:
            add = pd.DataFrame.from_dict(rows, orient="index")
            old = pd.concat([old, add])
            old = old[~old.index.duplicated(keep="last")].sort_index()
        old.index.name = "date"
        old.to_csv(path)         # 保留假日 NaN 标记行,不能用 save() 的 dropna

    pending = {}
    for i, d in enumerate(todo, 1):
        ds = d.strftime("%Y-%m-%d")
        try:
            pending[d] = fetch_day(ds)        # 假日=全 NaN 标记行,失败=不记(下轮重试)
        except Exception as e:  # noqa: BLE001
            print(f"  WARN {ds} 抓取失败,本轮跳过: {str(e)[:70]}")
        if i % 100 == 0:
            flush(pending)
            pending = {}
            print(f"  进度 {i}/{len(todo)}  已累计 {len(old)} 行")
        time.sleep(0.3)
    flush(pending)

    eff = old.dropna(subset=["total_pc"])
    print(f"OK  {OUT:<20}期權P/C(CBOE)  {len(eff)} 个交易日  "
          f"{eff.index.min().date()}..{eff.index.max().date()}  "
          f"最新 total={eff['total_pc'].iloc[-1]} equity={eff['equity_pc'].iloc[-1]}")


if __name__ == "__main__":
    main()
