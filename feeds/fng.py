#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26"]
# ///
"""CNN Fear & Greed — 官方 dataviz API,主指数 + 7 个分量原始值 + 2 条配套均线。日频。

API:https://production.dataviz.cnn.io/index/fearandgreed/graphdata/{start}
需要浏览器 UA + Origin/Referer,否则被拒。带起始日一次回全量(现行口径最早 2020-09-21);
历史点时间戳恰为 UTC 午夜(= 交易日标签,直接取日期),仅最后 1 个为盘中实时点
(转 America/New_York 取日期,避免美盘时段抓取时 UTC 日期超前一天)。

列与 CNN 七分量的对应(y 为分量的原始指标值,不是 0-100 打分):
  fng / fng_rating       主指数 0-100 与档位(extreme fear..extreme greed)
  momentum_spx(_ma125)   动量:S&P500 收盘 与 125 日均线
  strength_52w           强度:NYSE 创 52 周新高−新低 占比(%)
  breadth_mcclellan      宽度:McClellan 成交量加总指标
  putcall_5d             期权:CBOE 总 put/call 5 日均
  vix / vix_ma50         波动:VIX 与 50 日均线
  junk_spread            垃圾债需求:垃圾债-投资级利差(%,越低越贪婪)
  safehaven_diff         避险需求:股 − 债 20 日回报差(%,越高越贪婪)

增量机制:CNN 会回溯微调最近几日的值 → 每次全量拉取(~1MB)后与已有 CSV 按「日期重叠
新值覆盖、旧行永不删除」累积合并 —— API 日后即使截窗也不丢史;缓存误删也能全量自愈重建。

⚠ API 头几个月的回填值很脏(对抗核对 2026-06-07,与当年网页实时发布值比对发现):
2020-09~2021-01 有 88 天差异,模式为成段 50.0 占位 + 异常回填(如 2020-10-26 给 2.7,
差 40+);2021-01-29 之后干净。**用作信号建议从 2021-02 起算。**API 起点实测在 2020 夏
(start=2020-06-01 报错,2020-09-01 可用,多出的天仍是 50.0 占位,无信息量)。"""
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from _common import MACRO_DIR, _get, save

URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/2020-09-19"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
                  "(KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://edition.cnn.com",
}
SERIES = {                                   # API key -> CSV 列名
    "fear_and_greed_historical": "fng",
    "market_momentum_sp500":     "momentum_spx",
    "market_momentum_sp125":     "momentum_spx_ma125",
    "stock_price_strength":      "strength_52w",
    "stock_price_breadth":       "breadth_mcclellan",
    "put_call_options":          "putcall_5d",
    "market_volatility_vix":     "vix",
    "market_volatility_vix_50":  "vix_ma50",
    "junk_bond_demand":          "junk_spread",
    "safe_haven_demand":         "safehaven_diff",
}
ET = ZoneInfo("America/New_York")


def to_date(x_ms: float):
    if x_ms % 86_400_000 == 0:               # 历史点:恰为 UTC 午夜 = 交易日标签
        return datetime.fromtimestamp(x_ms / 1000, timezone.utc).date()
    return datetime.fromtimestamp(x_ms / 1000, timezone.utc).astimezone(ET).date()


def main():
    j = _get(URL, headers=HEADERS,
             referer="https://edition.cnn.com/markets/fear-and-greed").json()
    cols = {}
    for key, col in SERIES.items():
        s = {}
        for p in j[key]["data"]:             # 同日「实时点」自然覆盖「午夜点」(dict 后写胜)
            s[to_date(p["x"])] = p["y"]
        cols[col] = pd.Series(s)
    df = pd.DataFrame(cols)
    df["fng_rating"] = pd.Series(            # 档位只随主指数存一列
        {to_date(p["x"]): p.get("rating") for p in j["fear_and_greed_historical"]["data"]})
    df.index = pd.to_datetime(df.index)
    df.index.name = "date"

    path = os.path.join(MACRO_DIR, "fng.csv")
    if os.path.exists(path):                 # 累积合并:重叠日期取新值(CNN 回溯微调)
        old = pd.read_csv(path, index_col=0, parse_dates=True)
        df = pd.concat([old, df])
        df = df[~df.index.duplicated(keep="last")]
    save(df, "fng", "CNN恐惧贪婪")


if __name__ == "__main__":
    main()
