#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26"]
# ///
"""PCR — 输入美股 ticker,输出其期权 Put/Call 数据(Longbridge CLI)。

用法:
  uv run pcr/pcr.py NVDA                # 实时快照 + 近10日 + 分位判读
  uv run pcr/pcr.py SPY QQQ AAPL        # 多标的
  uv run pcr/pcr.py NVDA --days 30      # 历史显示行数
  uv run pcr/pcr.py NVDA --csv          # 同时累积保存 pcr/data/NVDA.csv(源窗口~420日滚动,缓存越攒越长)

口径:单标的期权链汇总(该 ticker 自己的期权),P/C(量)=当日 put/call 成交量比,
P/C(OI)=未平仓比。判读为反向逻辑:高分位≈避险情绪极端(恐慌区确认器,配合左侧分批),
低分位≈自满(只停止追高,不作卖出信号)。依赖:longbridge CLI 已 `auth login`。"""
import argparse
import json
import os
import shutil
import subprocess

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def lb_bin() -> str:
    p = shutil.which("longbridge") or os.path.expanduser("~/.local/bin/longbridge")
    if not os.path.exists(p):
        raise SystemExit("longbridge CLI 未找到(需安装并 `longbridge auth login`)")
    return p


def _run_json(args: list[str]):
    out = subprocess.run([lb_bin(), *args, "--format", "json"],
                         capture_output=True, text=True, timeout=90)
    if out.returncode != 0 or not out.stdout.strip():
        raise RuntimeError(f"longbridge {' '.join(args)} 失败: {out.stderr.strip()[:120]}")
    obj, _ = json.JSONDecoder().raw_decode(out.stdout)   # 尾部可能跟升级提示文本
    return obj


def snapshot(sym: str) -> dict:
    o = _run_json(["option", "volume", f"{sym}.US"])
    c, p = float(o["c"]), float(o["p"])
    return {"call": c, "put": p, "pc": p / c if c else float("nan")}


def daily(sym: str, count: int = 1000) -> pd.DataFrame:
    o = _run_json(["option", "volume", "daily", f"{sym}.US", "--count", str(count)])
    df = pd.DataFrame(o["stats"])
    ts = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="s", utc=True)
    df["date"] = ts.dt.tz_convert("America/New_York").dt.normalize().dt.tz_localize(None)
    df = df.set_index("date").sort_index()        # 先设索引再取列,避免按旧索引对齐成 NaN
    out = pd.DataFrame({
        "call_vol": pd.to_numeric(df["total_call_volume"]),
        "put_vol":  pd.to_numeric(df["total_put_volume"]),
        "pc_vol":   pd.to_numeric(df["put_call_volume_ratio"]),
        "pc_oi":    pd.to_numeric(df["put_call_open_interest_ratio"]),
        "total_oi": pd.to_numeric(df["total_open_interest"]),
    })
    out.index.name = "date"
    return out


def save_csv(sym: str, new: pd.DataFrame) -> str:
    """累积合并(源窗口滚动,旧日期保留、重叠用新值)。"""
    os.makedirs(DATA, exist_ok=True)
    path = os.path.join(DATA, f"{sym}.csv")
    if os.path.exists(path):
        old = pd.read_csv(path, index_col=0, parse_dates=True)
        new = pd.concat([old, new])
        new = new[~new.index.duplicated(keep="last")].sort_index()
    new.to_csv(path)
    return path


def report(sym: str, days: int, count: int, csv: bool):
    d = daily(sym, count)
    last = d.iloc[-1]
    pct252 = float((d["pc_vol"].tail(252) <= last["pc_vol"]).mean() * 100)
    print(f"\n=== {sym}.US 期權 Put/Call ===")
    try:
        s = snapshot(sym)
        print(f"实时快照   call {s['call']:>12,.0f}   put {s['put']:>12,.0f}   P/C={s['pc']:.3f}")
    except Exception as e:  # noqa: BLE001  盘前/接口波动不致命
        print(f"实时快照   (不可用: {str(e)[:60]})")
    print(f"日频历史   {len(d)} 天  {d.index[0].date()} .. {d.index[-1].date()}")
    print(f"最新收盘日 {d.index[-1].date()}: P/C(量)={last['pc_vol']:.3f}  "
          f"P/C(OI)={last['pc_oi']:.3f}  在近252日分位 {pct252:.0f}%")
    tag = ("⚠️ 恐慌尖峰区(反向:左侧分批确认器)" if pct252 >= 90 else
           "⚠️ 自满区(只停止追高,不卖)" if pct252 <= 10 else "中性区")
    print(f"判读       {tag}")
    print(d.tail(days).to_string(
        formatters={"call_vol": "{:,.0f}".format, "put_vol": "{:,.0f}".format,
                    "total_oi": "{:,.0f}".format,
                    "pc_vol": "{:.3f}".format, "pc_oi": "{:.3f}".format}))
    if csv:
        print(f"已保存 -> {save_csv(sym, d)}")


def main():
    ap = argparse.ArgumentParser(description="美股单标的期权 Put/Call(Longbridge)")
    ap.add_argument("tickers", nargs="+", help="如 NVDA SPY QQQ(可带或不带 .US)")
    ap.add_argument("--days", type=int, default=10, help="显示最近 N 天(默认 10)")
    ap.add_argument("--count", type=int, default=1000, help="拉取深度(默认 1000=源上限)")
    ap.add_argument("--csv", action="store_true", help="累积保存到 pcr/data/<SYM>.csv")
    a = ap.parse_args()
    for t in a.tickers:
        sym = t.upper().removesuffix(".US")
        try:
            report(sym, a.days, a.count, a.csv)
        except Exception as e:  # noqa: BLE001
            print(f"\n=== {sym}.US ===\n失败: {str(e)[:150]}")


if __name__ == "__main__":
    main()
