#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "openpyxl>=3.1"]
# ///
"""投資經理人調查 — NAAIM Exposure Index。免费 xlsx(自 2006 设立至今,周频)。
下载链接里带日期每周变,所以先抓页面、正则取当前 xlsx 链接,再下载解析。每天可跑刷新。
列:naaim_mean=头条暴露指数(=官方公布值);most_bullish/most_bearish=源表「最看多/最看空」
单一受访者的极值杠杆暴露(+200/−200),不是 %看多看空。源表 2006-07 自带 2 个重复行,这里去重。"""
import io
import re

import pandas as pd

from _common import _get, save

PAGE = "https://www.naaim.org/programs/naaim-exposure-index/"


def main():
    html = _get(PAGE).text
    links = re.findall(r'https?://[^"\'\s]*?(?:USE[_-]Data|Exposure)[^"\'\s]*?\.xlsx', html, re.I)
    if not links:
        raise RuntimeError("NAAIM: 页面未找到 xlsx 链接(结构可能变了)")
    raw = _get(links[0]).content
    x = pd.read_excel(io.BytesIO(raw), engine="openpyxl")
    x.columns = [str(c).strip() for c in x.columns]
    dcol = next(c for c in x.columns if "date" in c.lower())
    x[dcol] = pd.to_datetime(x[dcol], errors="coerce")
    x = x.dropna(subset=[dcol]).set_index(dcol).sort_index()

    out = pd.DataFrame(index=x.index)
    mcol = next((c for c in x.columns if any(k in c.lower() for k in ("mean", "average", "number"))), None)
    out["naaim_mean"] = pd.to_numeric(x[mcol], errors="coerce") if mcol else float("nan")
    for label, key in (("most_bullish", "bull"), ("most_bearish", "bear")):
        c = next((c for c in x.columns if key in c.lower()), None)
        if c is not None:
            out[label] = pd.to_numeric(x[c], errors="coerce")
    out = out[~out.index.duplicated(keep="last")].dropna(how="all")  # 源表自带重复行,去重
    save(out, "naaim", "投資經理人調查")


if __name__ == "__main__":
    main()
