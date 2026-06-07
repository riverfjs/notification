#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26"]
# ///
"""官方个股宽度 — S&P 官方 $S5TH/$S5FI/$S5TW(% 成分股 > MA200/50/20)→ data/macro/breadth_official.csv。

源:Barchart 免费 EOD 代理 `proxies/timeseries/queryeod.ashx`(2026-06 实测可达,
全历史 2006-12-29+,~4900 行/series)。两步握手,纯 stdlib urllib:
  1) GET 任一报价页(/stocks/quotes/$S5TH)拿 Cookie(XSRF-TOKEN + laravel_*);
  2) GET queryeod.ashx?symbol=$S5TH... 带 Cookie + x-xsrf-token 头(无 cookie → 401)。
为什么不用别的源(2026-06 实测):investing.com 的 /api/financialdata/historical 与 tvc
chart API 均被 Cloudflare challenge 挡(403);仅其 search API 与页面 HTML 可达,页面
__NEXT_DATA__ 只嵌最近 ~21 行(留作人工核对:06-04=56.26、06-03=53.47,与本源逐位一致)。

列名对齐 breadth_stocks.csv 便于直接对照:
  pct_above_ma20 = $S5TW、pct_above_ma50 = $S5FI、pct_above_ma200 = $S5TH(官方口径,无幸存者偏差)。

累积缓存:Barchart 免费窗口将来若收窄,旧日期仍保留(new.combine_first(old)),只增不减;
带守门(行数塌方/值越界 [0,100] 则拒绝)。幂等、可 cron(每日收盘后)。
读取请用 pd.read_csv(..., comment="#")(首行为 # 注释)。

    uv run feeds/breadth_official.py
"""
from __future__ import annotations

import http.cookiejar
import io
import os
import time
import urllib.parse
import urllib.request

import pandas as pd

from _common import MACRO_DIR, save

BARCHART_UA = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "*/*",
}
PAGE = "https://www.barchart.com/stocks/quotes/$S5TH"
EOD = ("https://www.barchart.com/proxies/timeseries/queryeod.ashx"
       "?symbol={sym}&data=daily&maxrecords=20000&order=asc&dividends=false&backadjust=false")
SERIES = [("$S5TW", "pct_above_ma20"),   # S&P 500 stocks above 20-day MA
          ("$S5FI", "pct_above_ma50"),   # ... above 50-day MA
          ("$S5TH", "pct_above_ma200")]  # ... above 200-day MA
OUT = os.path.join(MACRO_DIR, "breadth_official.csv")
CAVEAT = ("# OFFICIAL S&P breadth via Barchart free EOD: pct_above_ma20=$S5TW, "
          "pct_above_ma50=$S5FI, pct_above_ma200=$S5TH. No survivorship bias (true index "
          "constituents). Accumulating cache: old dates kept if the free window ever shrinks. "
          "Read with comment='#'.")


def _barchart_session() -> tuple[urllib.request.OpenerDirector, str]:
    """报价页握手 → (带 CookieJar 的 opener, 解码后的 XSRF token)。"""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    req = urllib.request.Request(PAGE, headers=BARCHART_UA)
    with opener.open(req, timeout=40) as resp:
        resp.read(64)                                    # 只需 Set-Cookie,不必读全页
    tok = next((c.value for c in jar if c.name == "XSRF-TOKEN"), None)
    if not tok:
        raise RuntimeError("Barchart 握手失败:页面未返回 XSRF-TOKEN cookie")
    return opener, urllib.parse.unquote(tok)


def _fetch_eod(opener, xsrf: str, sym: str, retries: int = 3) -> pd.Series:
    """queryeod.ashx → close 序列(CSV: sym,date,o,h,l,close,vol,无表头)。"""
    url = EOD.format(sym=urllib.parse.quote(sym))
    h = dict(BARCHART_UA, **{"x-xsrf-token": xsrf, "Referer": PAGE})
    last = None
    for a in range(retries):
        try:
            with opener.open(urllib.request.Request(url, headers=h), timeout=60) as resp:
                raw = resp.read().decode("utf-8", "replace")
            df = pd.read_csv(io.StringIO(raw), header=None,
                             names=["sym", "date", "o", "h", "l", "c", "v"])
            if len(df) >= 100:
                s = pd.Series(pd.to_numeric(df["c"], errors="coerce").values,
                              index=pd.to_datetime(df["date"]), name=sym).dropna()
                return s[~s.index.duplicated(keep="last")].sort_index()
            last = f"only {len(df)} rows"
        except Exception as e:  # noqa: BLE001
            last = str(e)[:100]
        time.sleep(2.0 * (a + 1))
    raise RuntimeError(f"Barchart EOD 失败 {sym}: {last}")


def main():
    opener, xsrf = _barchart_session()
    cols = {}
    for sym, col in SERIES:
        s = _fetch_eod(opener, xsrf, sym)
        if not ((0 <= s.min()) and (s.max() <= 100)):
            raise RuntimeError(f"{sym} 值越界 [0,100]: min={s.min()} max={s.max()}")
        cols[col] = s
        print(f"  {sym} -> {col}: {len(s)} rows {s.index[0].date()}..{s.index[-1].date()}"
              f"  last={s.iloc[-1]:.2f}")
        time.sleep(1.0)
    new = pd.DataFrame(cols)
    new.index.name = "date"

    if os.path.exists(OUT):                              # 累积:旧日期永不丢
        old = pd.read_csv(OUT, comment="#", index_col=0, parse_dates=True)
        merged = new.combine_first(old)
        if len(merged) < len(old):
            raise RuntimeError(f"合并后行数 {len(merged)} < 旧 {len(old)},拒绝覆盖")
    else:
        merged = new

    path = save(merged, "breadth_official", "官方宽度($S5xx)")
    with open(path) as f:
        body = f.read()
    with open(path, "w") as f:
        f.write(CAVEAT + "\n" + body)
    tail = merged.dropna().tail(3)
    for d, r in tail.iterrows():
        print(f"      {d.date()}: >MA20 {r['pct_above_ma20']:.2f}  "
              f">MA50 {r['pct_above_ma50']:.2f}  >MA200 {r['pct_above_ma200']:.2f}")


if __name__ == "__main__":
    main()
