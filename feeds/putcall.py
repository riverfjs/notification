#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26"]
# ///
"""期权 Put/Call 比 — CBOE 免费日度归档(纯历史段,源已冻结)。

★ 冻结 CAVEAT(也写进输出 CSV 首行 # 注释,读取请用 pd.read_csv(..., comment="#")):
  CBOE 2019-10-04 之后停止免费发布每日 P/C 汇总,这批归档不会再更新;
  续更只能买 CBOE DataShop/LiveVol。本脚本幂等全量覆盖,cron 重跑安全(内容恒定)。

5 个归档文件(cdn.cboe.com 需浏览器 UA + Referer,否则 403):
  equitypc.csv         股票 P/C  2006-11-01..2019-10-04(注意 2012-06-11 起剔除 ETP,口径变更)
  indexpc.csv          指数 P/C  2006-11-01..2019-10-04
  totalpc.csv          全部 P/C  2006-11-01..2019-10-04
  equitypcarchive.csv  股票 P/C  2003-10-17..2012-06-07(旧档,OCC 清算量口径)
  indexpcarchive.csv   指数 P/C  2003-10-17..2012-06-07(旧档)
新旧档重叠期(2006-11..2012-06)数值不一致(equity 平均差 0.01、index 平均差 0.20,
统计口径不同)→ 不拼接,分列保留(*_archive),由下游自行选段。
列=CBOE 原始发布的 P/C Ratio(put/call),不重算;高 P/C=恐慌/对冲需求,低=贪婪。"""
import io

import pandas as pd

from _common import _get, save

CDN = "https://cdn.cboe.com/resources/options/volume_and_call_put_ratios/"
BROWSER = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
           "Accept": "*/*"}
FILES = [  # (文件, 输出列名)
    ("equitypc.csv",        "equity_pc"),
    ("indexpc.csv",         "index_pc"),
    ("totalpc.csv",         "total_pc"),
    ("equitypcarchive.csv", "equity_pc_archive"),
    ("indexpcarchive.csv",  "index_pc_archive"),
]
CAVEAT = ("# CAVEAT frozen source: CBOE stopped free daily put/call publication after"
          " 2019-10-04; this file is a static historical archive and will NOT extend."
          " equity_pc definition change 2012-06-11 (ETPs excluded after). *_archive cols"
          " = older 2003-2012 series on a different (OCC cleared) volume basis - do not"
          " splice. Read with comment='#'.")


def fetch_ratio(fname: str, col: str) -> pd.Series:
    """单个归档 → P/C Ratio 序列。文件头部有免责声明行(含 latin-1 特殊字节),
    先按行扫到真正表头(首格 DATE/Trade_date/Date)再解析;比率取末列(CBOE 原值)。"""
    txt = _get(CDN + fname, headers=BROWSER, referer="https://www.cboe.com/").content \
        .decode("latin-1")
    lines = txt.splitlines()
    hdr = next(i for i, l in enumerate(lines)
               if l.split(",")[0].strip().lower() in ("date", "trade_date"))
    df = pd.read_csv(io.StringIO("\n".join(lines[hdr:])))
    dates = pd.to_datetime(df.iloc[:, 0].astype(str).str.strip(), format="%m/%d/%Y",
                           errors="coerce")
    s = pd.to_numeric(df.iloc[:, -1], errors="coerce")
    s.index = pd.DatetimeIndex(dates, name="date")
    s = s[s.index.notna()].sort_index()
    s.name = col
    if len(s) < 1000:
        raise RuntimeError(f"putcall {fname}: 仅 {len(s)} 行,归档结构疑似变更")
    return s


def main():
    out = pd.concat([fetch_ratio(f, c) for f, c in FILES], axis=1, sort=True)
    path = save(out, "putcall", "期權P/C比(冻结)")
    with open(path) as f:                      # 冻结/口径 caveat 写进 CSV 首行
        body = f.read()
    with open(path, "w") as f:
        f.write(CAVEAT + "\n" + body)
    last = out["equity_pc"].dropna()
    print(f"      equity_pc {last.index[0].date()}..{last.index[-1].date()} "
          f"(FROZEN, last={last.iloc[-1]:.2f}); "
          f"index_pc last={out['index_pc'].dropna().iloc[-1]:.2f} @2019-10-04")


if __name__ == "__main__":
    main()
