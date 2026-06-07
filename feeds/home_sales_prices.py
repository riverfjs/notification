#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "requests>=2.31"]
# ///
"""房屋銷售 & 房價 — 官方 FRED API + 成屋销售镜像拼接。月频。每天可跑刷新。

成屋销售(NAR,SAAR):FRED 的 EXHOSLUSM495S 被 NAR 授权限制为「滚动 13 个月」窗口。
全历史 2013-01+ 来自 feeds/ehs_archive.csv,由 build_ehs_archive.py 构建,口径为
「单 vintage + 重订 seam」两段(P14,2026-06-07 调研定稿):
  - 2025-02 起 = 官方当前单一 vintage(FRED API 窗口 ∪ 2026-03-22 fredgraph 快照,
    同属 2026-02 年度重订后家族,重叠段与 API 逐位一致);唯一 seam 在 2025-01/02。
  - 2013-01..2025-01 = 各月最后可得修订值(Wayback FRED 快照 + DBnomics NAR git
    62 个 commit vintage 合并)。NAR 每年 2 月只重订最近 ~3 年的季调,实测跨重订
    修订幅度 mean 0.82%/max 2.81%(见 build_ehs_archive.py 的 revision audit),
    历史段与真·单一 vintage 的偏差有界且很小。真·单一 vintage 免费全史不存在(fredgraph 全史快照
    /ALFRED vintage 接口/DBnomics 当前序列三路线均实测排除,详见 build 脚本头注)。
本脚本每次运行用官方 API 的当前窗口覆盖/追加镜像(官方值视为最新 vintage 回写
ehs_archive.csv),窗口滚动也不会丢月份。

其余:新房销售 HSN1F(1963+)、Case-Shiller 全国房价指数 CSUSHPINSA(1987+),
深历史无授权限制。单位:两个销售列均为「千套、年化」。"""
import csv
import os
from datetime import date

import pandas as pd

from _common import HERE, fred, save

EHS_ARCHIVE = os.path.join(HERE, "ehs_archive.csv")


def existing_home_sales() -> pd.Series:
    """镜像 + 官方 API 拼接,顺手把 API 当前窗口回写进镜像(自续期)。单位:套(原始)。"""
    arch = {}
    if os.path.exists(EHS_ARCHIVE):
        with open(EHS_ARCHIVE) as f:
            for r in csv.DictReader(f):
                arch[r["date"]] = (r["existing_home_sales"], r["vintage"], r["source"])

    api = fred([("EXHOSLUSM495S", "ehs")])["ehs"].dropna()
    changed = False
    for ts, v in api.items():
        d = ts.strftime("%Y-%m-%d")
        if d not in arch or float(arch[d][0]) != float(v):
            arch[d] = (f"{v:.0f}", date.today().isoformat(), "fred_api")
            changed = True
    if changed and arch:
        with open(EHS_ARCHIVE, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["date", "existing_home_sales", "vintage", "source"])
            for d in sorted(arch):
                w.writerow([d, *arch[d]])

    s = pd.Series({pd.Timestamp(d): float(v[0]) for d, v in arch.items()}).sort_index()
    if s.empty:
        raise RuntimeError("成屋销售为空:feeds/ehs_archive.csv 缺失且 API 无数据"
                           "(先跑 build_ehs_archive.py 重建镜像)")
    return s


def main():
    df = fred([
        ("HSN1F",      "new_home_sales_k"),   # 新房销售(千,年化,1963+)
        ("CSUSHPINSA", "case_shiller_natl"),  # Case-Shiller 全国房价指数(1987+)
    ])
    # 成屋销售(NAR):镜像 2013+ ∪ 官方 API 滚动窗口,套 → 千套
    df["existing_home_sales_k"] = existing_home_sales() / 1000.0
    save(df, "home_sales_prices", "房屋銷售&房價")


if __name__ == "__main__":
    main()
