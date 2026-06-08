#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "requests>=2.31"]
# ///
"""ISM 製造業 PMI(best-effort 免费镜像拼接)— 月频,回溯 1948。每天可跑刷新。

ISM 自 2016 起收回授权:FRED 的 NAPM 已下架(API 报 series does not exist),
ismworld.org 新闻稿页被 Incapsula+reCAPTCHA 验证码墙挡住 stdlib 抓取 → 无法直抓官方。
本文件用 5 个可验证的免费镜像拼接出 1948-01 至今的完整 headline PMI:

  1) Wayback 固定快照的旧 Quandl ISM/MAN_PMI.csv(官方修订值)…… 1948-01..2016-12
  2) Wayback 固定快照的 MQL5 日历页(发布原值 as-released)……… 2017-01..2021-02
  3) MQL5 实时日历页(滚动 ~50 个月窗口,发布原值)……………… 当前续更主源
  4) DBnomics ISM/pmi(官方授权镜像,2020-05 起;其抓取 2025-09 后
     损坏出现 10-11 的脏值,用 [20,90] 合理区间过滤)……………… 桥接 2021-03..2022-03
  5) YCharts us_pmi 页 "Last Value / Latest Period"(MQL5 对最新一期
     有几天延迟,用它补最新月)…………………………………………… 最新月补丁

拼接规则:按上面优先级 combine_first(高优先级覆盖重叠日期),最后并入上次落地的
CSV —— 滚动窗口源(3)随时间前移也不会丢历史,且整体幂等、cron 安全。
两个 Wayback 快照是不可变归档 → 首次成功后缓存到 ../data/cache/ism_pmi_static.csv,
之后直接读缓存(web.archive.org 偶发 503 不再造成修订值/原值来回翻转)。
其余每个源独立 try/except:个别镜像当天挂掉不影响落地(历史从上次 CSV 延续)。

口径 caveat:1948..2016 段是 ISM 年度季节因子修订后的值;2017+ 段是发布当时的
原值(ISM 每年 1 月微调季节因子,两者可有 ±0.5 以内差异;ISM 极少大幅修订)。
"""
import os
import re

import pandas as pd

from _common import CACHE_DIR, _get, save

STATIC_CACHE = os.path.join(CACHE_DIR, "ism_pmi_static.csv")  # 不可变 Wayback 段的本地缓存

UA_BROWSER = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "*/*",
}
# Wayback 固定快照(id_ = 原始字节,无回放改写),URL 永久稳定
WAYBACK_QUANDL = ("https://web.archive.org/web/20170104101745id_/"
                  "https://www.quandl.com/api/v3/datasets/ISM/MAN_PMI.csv")
WAYBACK_MQL5 = ("https://web.archive.org/web/20210303114323id_/"
                "https://www.mql5.com/en/economic-calendar/united-states/ism-manufacturing-pmi")
MQL5_LIVE = "https://www.mql5.com/en/economic-calendar/united-states/ism-manufacturing-pmi"
DBNOMICS = "https://api.db.nomics.world/v22/series/ISM/pmi/pm?observations=1&format=json"
YCHARTS = "https://ycharts.com/indicators/us_pmi"

SANE_LO, SANE_HI = 20.0, 90.0   # 1948 年至今实际区间 [29.4, 77.5];滤掉镜像脏值(如 10-11)


def _sane(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce")
    return s.where((s >= SANE_LO) & (s <= SANE_HI)).dropna()


def _from_quandl_wayback() -> pd.Series:
    """旧 Quandl ISM/MAN_PMI 归档 CSV:Date,Index 两列,1948-01..2016-12(修订值)。"""
    from io import StringIO
    df = pd.read_csv(StringIO(_get(WAYBACK_QUANDL, headers=UA_BROWSER, timeout=90).text))
    s = pd.Series(df["Index"].values, index=pd.to_datetime(df["Date"]))
    return _sane(s)


def _parse_mql5(html: str) -> pd.Series:
    """MQL5 日历页内嵌的 history 表:Reference 月份 + Actual(发布原值,N/D=未发布)。"""
    rows = re.findall(
        r'event-table-history__period">([A-Z][a-z]{2} \d{4})</div>\s*'
        r'<div class="event-table-history__actual[^"]*">\s*<span[^>]*>\s*([^<]+?)\s*</span>',
        html)
    if not rows:
        raise RuntimeError("MQL5 history 表解析失败(页面结构变了?)")
    idx = pd.to_datetime([p for p, _ in rows], format="%b %Y")
    return _sane(pd.Series([a for _, a in rows], index=idx))


def _from_dbnomics() -> pd.Series:
    """DBnomics 的 ISM 官方镜像(2020-05 起;2025-09 后脏值靠 _sane 过滤)。"""
    doc = _get(DBNOMICS, timeout=60).json()["series"]["docs"][0]
    idx = pd.to_datetime(doc["period_start_day"])
    return _sane(pd.Series(doc["value"], index=idx))


def _from_ycharts() -> pd.Series:
    """YCharts 公开页的 'Last Value 54.00 Latest Period May 2026' → 单点最新月。"""
    txt = re.sub(r"<[^>]+>", " ", _get(YCHARTS, headers=UA_BROWSER, timeout=60).text)
    m = re.search(r"Last Value\s+([0-9.]+)\s+Latest Period\s+([A-Z][a-z]{2} \d{4})",
                  re.sub(r"\s+", " ", txt))
    if not m:
        raise RuntimeError("YCharts Last Value 解析失败")
    return _sane(pd.Series([float(m.group(1))],
                           index=pd.DatetimeIndex([pd.to_datetime(m.group(2), format="%b %Y")])))


def _static_history() -> pd.Series:
    """不可变段(Wayback Quandl 1948-2016 + Wayback MQL5 2017-2021-02):
    首次成功抓取后缓存到本地,之后直接读缓存 → 决定性 + 抗 archive.org 偶发 503。"""
    if os.path.exists(STATIC_CACHE):
        prev = pd.read_csv(STATIC_CACHE, index_col=0, parse_dates=True)
        return _sane(prev["ism_pmi"])
    quandl = _from_quandl_wayback()                       # 1948-01..2016-12(修订值)
    mql5_arch = _parse_mql5(_get(WAYBACK_MQL5, headers=UA_BROWSER, timeout=90).text)
    static = quandl.combine_first(mql5_arch).sort_index()
    if len(static) < 850 or static.index.min() > pd.Timestamp("1950-01-01"):
        raise RuntimeError(f"static 段异常:{len(static)} 点,起点 {static.index.min()}")
    df = static.to_frame("ism_pmi")
    df.index.name = "date"
    os.makedirs(CACHE_DIR, exist_ok=True)
    df.to_csv(STATIC_CACHE)
    return static


def main():
    try:
        merged = _static_history()
        print(f"      src static(2 wayback) {len(merged):>4} obs  "
              f"{merged.index.min().date()}..{merged.index.max().date()}")
    except Exception as e:  # noqa: BLE001 — 仅首跑且 wayback 挂时发生;靠上次 CSV 兜底
        print(f"      src static(2 wayback) FAIL: {str(e)[:90]}")
        merged = pd.Series(dtype=float)
    layers: list[tuple[str, object]] = [          # 续更源,优先级从高到低
        ("mql5_live",      lambda: _parse_mql5(_get(MQL5_LIVE, headers=UA_BROWSER,
                                                    timeout=60).text)),
        ("dbnomics",       _from_dbnomics),
        ("ycharts_latest", _from_ycharts),
    ]
    for name, fn in layers:
        try:
            s = fn()
            merged = merged.combine_first(s)
            print(f"      src {name:<15}{len(s):>4} obs  {s.index.min().date()}..{s.index.max().date()}")
        except Exception as e:  # noqa: BLE001 — 单源失败不致命,历史由上次 CSV 兜底
            print(f"      src {name:<15}FAIL: {str(e)[:90]}")
    try:  # 并入上次落地的 CSV(最低优先级):滚动窗口源前移后历史仍保留
        from _common import MACRO_DIR
        prev = pd.read_csv(os.path.join(MACRO_DIR, "ism_pmi.csv"), index_col=0, parse_dates=True)
        merged = merged.combine_first(_sane(prev["ism_pmi"]))
    except Exception:  # noqa: BLE001 — 首跑无文件
        pass
    if len(merged) < 300 or merged.index.min() > pd.Timestamp("1950-01-01"):
        raise RuntimeError(f"ISM 拼接结果异常:仅 {len(merged)} 点,起点 {merged.index.min()}")
    df = merged.sort_index().to_frame("ism_pmi")
    df.index.name = "date"
    save(df, "ism_pmi", "ISM製造業PMI")


if __name__ == "__main__":
    main()
