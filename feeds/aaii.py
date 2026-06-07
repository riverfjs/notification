#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "xlrd>=2.0"]
# ///
"""散户情绪 — AAII Sentiment Survey(看多/中性/看空 %,周频,1987-07 至今)。

主源:AAII 官方历史 xls  https://www.aaii.com/files/surveys/sentiment.xls
  实测(2026-06)浏览器 UA + Referer 可直下、无会员墙,文件每周四随新一期更新,
  含 1987-06-26 起全历史 → 解析 SENTIMENT 表的 Reported Date / Bullish / Neutral / Bearish。
备援(主源 404/改版时自动切换,覆盖有缺口):
  1) GitHub 静态归档 psinopoli/AAII-Sentiment(1987-07-24..2024-06-27,即官方 xls 快照);
  2) 抓 aaii.com 公开 sent_results 页(只展示最近 ~22 周;页内日期无年份,按降序逐行推断;
     页面日期=调查截止周三,比 xls 的 Reported Date(周四)早 1 天,备援段直接用页面日期)。
列:bullish/neutral/bearish(%,0-100)+ bull_bear_spread(=bullish-bearish,同行计算、因果)。
索引=Reported Date。值为当周公布值,无前视;幂等全量覆盖,每天可跑刷新。"""
import io
import re

import pandas as pd

from _common import _get, save

XLS = "https://www.aaii.com/files/surveys/sentiment.xls"
PAGE = "https://www.aaii.com/sentimentsurvey/sent_results"
GH_ARCHIVE = ("https://raw.githubusercontent.com/psinopoli/AAII-Sentiment/"
              "main/AAII_SENTIMENT_CSV.csv")
BROWSER = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
           "Accept": "*/*"}


def from_official_xls() -> pd.DataFrame:
    """官方 sentiment.xls → 全历史。SENTIMENT 表无规整表头:首列混有标题/统计行,
    用「能解析成日期」过滤;1987-06/07 前两行只有 S&P 价无情绪值,dropna 掉。"""
    raw = _get(XLS, headers=BROWSER, referer=PAGE).content
    df = pd.read_excel(io.BytesIO(raw), sheet_name="SENTIMENT", header=None)
    dates = pd.to_datetime(df[0], errors="coerce", format="mixed")
    df = df[dates.notna()]
    out = pd.DataFrame(index=pd.DatetimeIndex(dates[dates.notna()], name="date"))
    for col, name in ((1, "bullish"), (2, "neutral"), (3, "bearish")):
        out[name] = pd.to_numeric(df[col], errors="coerce").to_numpy() * 100.0
    out = out.dropna(how="all")
    if len(out) < 1500:  # 全历史应有 ~2000 周;过少说明文件结构变了
        raise RuntimeError(f"AAII xls 解析仅 {len(out)} 行,结构疑似变更")
    return out


def from_archive_plus_page() -> pd.DataFrame:
    """备援:GitHub 归档(1987..2024-06)+ sent_results 页(最近 ~22 周)拼接。
    中间(2024-07..页面窗口起点)存在缺口,打印告警。"""
    arch = pd.read_csv(io.StringIO(_get(GH_ARCHIVE).text))
    arch["date"] = pd.to_datetime(arch["Date"], format="%m-%d-%y", errors="coerce")
    arch = arch.dropna(subset=["date"]).set_index("date").sort_index()
    out = pd.DataFrame({n: pd.to_numeric(arch[c], errors="coerce") * 100.0
                        for c, n in (("Bullish", "bullish"), ("Neutral", "neutral"),
                                     ("Bearish", "bearish"))})

    page = scrape_results_page()
    page = page[page.index > out.index.max()]
    if not page.empty:
        gap_w = (page.index.min() - out.index.max()).days // 7
        if gap_w > 2:
            print(f"WARN aaii 备援拼接缺口 ~{gap_w} 周 "
                  f"({out.index.max().date()} → {page.index.min().date()})")
        out = pd.concat([out, page]).sort_index()
    return out


def scrape_results_page() -> pd.DataFrame:
    """sent_results 页的历史小表:行如 <td>Jun 3</td><td>36.3% </td>...,无年份。
    行序=最新在上,从今年起逐行回推:出现「日期不降反升」即跨年,年份减一。"""
    html = _get(PAGE, headers=BROWSER).text
    rows = re.findall(
        r'<td align="left" class="tableTxt">([A-Z][a-z]{2}\s+\d{1,2})</td>\s*'
        r'<td[^>]*>([\d.]+)%\s*</td>\s*<td[^>]*>([\d.]+)%\s*</td>\s*<td[^>]*>([\d.]+)%\s*</td>',
        html)
    if not rows:
        raise RuntimeError("AAII sent_results 页未匹配到数据行(页面结构可能变了)")
    today = pd.Timestamp.today().normalize()
    year, prev, recs = today.year, None, []
    for mon_day, bu, ne, be in rows:                      # 自上而下 = 由新到旧
        d = pd.to_datetime(f"{mon_day} {year}", format="%b %d %Y")
        if d > today or (prev is not None and d >= prev):
            year -= 1
            d = pd.to_datetime(f"{mon_day} {year}", format="%b %d %Y")
        prev = d
        recs.append((d, float(bu), float(ne), float(be)))
    return (pd.DataFrame(recs, columns=["date", "bullish", "neutral", "bearish"])
            .set_index("date").sort_index())


def main():
    try:
        out = from_official_xls()
    except Exception as e:  # noqa: BLE001
        print(f"WARN aaii 官方 xls 失败({str(e)[:80]}),切备援 GitHub 归档+页面")
        out = from_archive_plus_page()
    out = out[~out.index.duplicated(keep="last")]
    out["bull_bear_spread"] = out["bullish"] - out["bearish"]
    save(out, "aaii", "散户情绪AAII")
    last = out.iloc[-1]
    print(f"      latest {out.index[-1].date()}: bull {last['bullish']:.1f}%  "
          f"neutral {last['neutral']:.1f}%  bear {last['bearish']:.1f}%  "
          f"spread {last['bull_bear_spread']:+.1f}pp")


if __name__ == "__main__":
    main()
