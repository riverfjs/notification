#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["yfinance>=0.2.40", "pandas>=2.0", "numpy>=1.26", "lxml>=5.0"]
# ///
"""真·个股宽度(时点成分版)— % 收盘 > MA20/50/200,按「当日真实标普500成分」计算。

P13 升级:成分不再是「当前清单回溯套用」,而是 fja05680/sp500(GitHub,1996+ 历史成分)
的时点(point-in-time)成员掩码 —— 每天只统计当天确实在指数里的股票:
  1) Wikipedia 当前成分(yf_symbol 映射 + 历史文件之后的尾段成员)→ data/cache/sp500/sp500_members.csv
  2) fja05680/sp500 最新日期版 CSV(date,tickers;GitHub API 自动发现文件名)
     → data/cache/sp500/sp500_members_hist.csv(守门:行数不回退)
  3) yfinance 面板 = 当前成分(每次全量重拉)+ 历史成分中已退市者
     (只在 yfinance 真的有数据时并入;查过没有的记入 data/cache/sp500/sp500_px_unavail.txt 不再重试;
     已并入面板的死票后续 run 直接沿用旧列,不重拉)→ data/cache/sp500/sp500_px.csv(向后兼容:
     当前成分列仍在,只是多了死票列)
     ★ 价格口径 = auto_adjust=False 的 Close:拆股已重算、股息不复权(图表惯例)。
       官方 $S5xx 正是该口径 —— 实测股息复权价会把 MA 压低 → 宽度系统性高估 +2~3pp
       (2026-06-04: 复权 58.88 vs 官方 56.26;不复权 56.29,逐位对上)。
       P13 前的旧面板是复权口径,不兼容:换基重建,勿与旧列混用。
  4) 宽度 = 当日 [是成分 & MA 有效] 的股票中收盘>MA 的占比;无价数据的成分既不进分子也
     不进分母;n_ma* = 当日分母,n_members = 当日时点成分数(含无价者),覆盖率可审计。

★ 残余幸存者偏差 CAVEAT(数字化写进输出 CSV 首行):已退市且 yfinance 无价的旧成分
  (多为弱股)被剔除 → 仍轻微高估;对照官方 $S5TW/$S5FI/$S5TH(data/macro/
  breadth_official.csv,跑本脚本前先跑 feeds/breadth_official.py)逐日量化 BEFORE
  (旧·当前成分法)vs AFTER(时点成分法)偏差,run 时打印、均值写进 caveat。
  另:改名票(如 FB→META)在旧代码期间按旧票名记成分,yfinance 只认新票名 → 该窗口
  少数活票缺席(进不了分母,偏差为噪声非方向性)。

因果性:MA 用 rolling(过去 N 日);成分掩码用 ffill(只用已生效的成分表)。
幂等:每次全量重算、整文件覆盖;面板带覆盖率/日期守门(同 prices.py)。
cron:放在 breadth_official.py 之后、低频(收盘后一次)。

    uv run feeds/breadth_stocks.py              # 全量:清单 + 历史成分 + 面板 + 宽度
    uv run feeds/breadth_stocks.py --no-fetch   # 跳过下载,用已落地面板/成分重算
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time

import numpy as np
import pandas as pd

from _common import MACRO_DIR, SP500_CACHE_DIR, _get, save

MEMBERS_CSV = os.path.join(SP500_CACHE_DIR, "sp500_members.csv")
MEMBERS_HIST_CSV = os.path.join(SP500_CACHE_DIR, "sp500_members_hist.csv")
PANEL_CSV = os.path.join(SP500_CACHE_DIR, "sp500_px.csv")
UNAVAIL_TXT = os.path.join(SP500_CACHE_DIR, "sp500_px_unavail.txt")
OFFICIAL_CSV = os.path.join(MACRO_DIR, "breadth_official.csv")
WIKI = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
GH_API = "https://api.github.com/repos/fja05680/sp500/contents/"
START = "2000-01-01"
HIST_FROM = "1999-06-01"        # 成分并集起点:早于面板 2000-01 半年,保证 2000 年掩码正确
CHUNK = 50


def fetch_members() -> pd.DataFrame:
    """Wikipedia 当前成分表(id=constituents)→ DataFrame,落 data/cache/sp500/sp500_members.csv。"""
    html = _get(WIKI).text
    tables = pd.read_html(io.StringIO(html), attrs={"id": "constituents"})
    df = tables[0]
    df.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]
    if not (480 <= len(df) <= 520) or "symbol" not in df or "gics_sector" not in df:
        raise RuntimeError(f"Wikipedia 成分表异常: {len(df)} rows, cols={list(df.columns)[:8]}")
    df["symbol"] = df["symbol"].astype(str).str.strip()
    df["yf_symbol"] = df["symbol"].str.replace(".", "-", regex=False)  # BRK.B -> BRK-B
    df = df.sort_values("symbol").reset_index(drop=True)
    os.makedirs(SP500_CACHE_DIR, exist_ok=True)
    df.to_csv(MEMBERS_CSV, index=False)
    print(f"OK  sp500_members       {len(df)} 成分  {df['gics_sector'].nunique()} sectors -> {MEMBERS_CSV}")
    return df


def fetch_membership_history() -> pd.DataFrame:
    """fja05680/sp500 最新「S&P 500 Historical Components & Changes(MM-DD-YYYY).csv」
    (date,tickers,普通票名版;带 -YYYYMM 后缀的 PIT 票名版不适合 yfinance,不用)。
    GitHub API 自动发现最新文件名;守门:新行数 < 旧 → 拒绝覆盖;网络挂了用本地缓存。"""
    pat = re.compile(r"S&P 500 Historical Components & Changes\((\d{2})-(\d{2})-(\d{4})\)\.csv")
    try:
        listing = _get(GH_API).json()
        cands = [(f"{m.group(3)}-{m.group(1)}-{m.group(2)}", it["download_url"])
                 for it in listing if (m := pat.fullmatch(it["name"]))]
        if not cands:
            raise RuntimeError("repo 里没找到日期版成分 CSV")
        _, url = max(cands)
        raw = _get(url).text
        df = pd.read_csv(io.StringIO(raw))
        if list(df.columns) != ["date", "tickers"] or len(df) < 2000:
            raise RuntimeError(f"成分历史格式异常: cols={list(df.columns)}, rows={len(df)}")
        if os.path.exists(MEMBERS_HIST_CSV):
            old_n = sum(1 for _ in open(MEMBERS_HIST_CSV)) - 1
            if len(df) < old_n:
                raise RuntimeError(f"新成分历史 {len(df)} 行 < 旧 {old_n},拒绝覆盖")
        os.makedirs(SP500_CACHE_DIR, exist_ok=True)
        df.to_csv(MEMBERS_HIST_CSV, index=False)
        print(f"OK  sp500_members_hist  {len(df)} 事件行  {df['date'].iloc[0]}..{df['date'].iloc[-1]}"
              f" -> {MEMBERS_HIST_CSV}")
        return df
    except Exception as e:  # noqa: BLE001
        if os.path.exists(MEMBERS_HIST_CSV):
            print(f"  ! 成分历史拉取失败({str(e)[:80]}),改用本地缓存 {MEMBERS_HIST_CSV}")
            return pd.read_csv(MEMBERS_HIST_CSV)
        raise


def _load_unavail() -> set[str]:
    if not os.path.exists(UNAVAIL_TXT):
        return set()
    return {ln.strip() for ln in open(UNAVAIL_TXT) if ln.strip() and not ln.startswith("#")}


def _save_unavail(s: set[str]):
    os.makedirs(SP500_CACHE_DIR, exist_ok=True)
    with open(UNAVAIL_TXT, "w") as f:
        f.write("# ex-S&P500 tickers confirmed ABSENT from yfinance (skip re-trying).\n")
        f.write("# Delete a line to force a re-check on next breadth_stocks.py run.\n")
        f.write("\n".join(sorted(s)) + "\n")


def _yf_batches(pairs: list[tuple[str, str]], tag: str) -> tuple[pd.DataFrame, set[str]]:
    """yfinance 分批拉收盘(拆股调整、股息不复权,对齐官方 $S5xx 口径)。
    pairs=[(yf_symbol, 原始票名)];返回 (面板, 成功批次覆盖的原始票名集)。
    成功批次里没回数据的票 = yfinance 确认没有;整批失败的票不下结论(可能限流)。"""
    import yfinance as yf
    yf2sym = dict(pairs)
    syms = [p[0] for p in pairs]
    parts, attempted = [], set()
    nb = (len(syms) - 1) // CHUNK + 1
    for i in range(0, len(syms), CHUNK):
        batch = syms[i:i + CHUNK]
        cl = None
        for attempt in range(3):
            try:
                df = yf.download(batch, start=START, auto_adjust=False,
                                 progress=False, threads=True, group_by="column")
                if df is not None and not df.empty:
                    cl = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df[["Close"]]
                    if not isinstance(cl, pd.DataFrame):
                        cl = cl.to_frame(batch[0])
                    break
            except Exception as e:  # noqa: BLE001
                print(f"  ! {tag} batch {i // CHUNK + 1} attempt {attempt + 1}: {str(e)[:80]}")
            time.sleep(3 * (attempt + 1))
        if cl is None:
            print(f"  !! {tag} batch {i // CHUNK + 1} 失败,跳过 {len(batch)} tickers")
            continue
        attempted |= {yf2sym[s] for s in batch}
        cl = cl.dropna(axis=1, how="all")
        parts.append(cl)
        print(f"  {tag} batch {i // CHUNK + 1:>2}/{nb}: {cl.shape[1]}/{len(batch)} tickers, {len(cl)} rows")
        time.sleep(1.0)
    if not parts:
        return pd.DataFrame(), attempted
    px = pd.concat(parts, axis=1).sort_index()
    px = px.loc[:, ~px.columns.duplicated()]
    px.columns = [yf2sym.get(c, c) for c in px.columns]          # 还原 BRK-B -> BRK.B
    px.index = pd.to_datetime(px.index).tz_localize(None)
    px.index.name = "date"
    return px.dropna(how="all"), attempted


def fetch_panel(members: pd.DataFrame, hist_union: set[str]) -> pd.DataFrame:
    """面板 = 当前成分(全量重拉)+ 历史死票(yfinance 有才并入,一次性发现后沿用旧列)。"""
    old = pd.read_csv(PANEL_CSV, index_col=0, parse_dates=True) if os.path.exists(PANEL_CSV) else None
    cur_px, _ = _yf_batches(list(zip(members["yf_symbol"], members["symbol"])), "cur")
    cov = cur_px.shape[1] / len(members) * 100
    print(f"  panel(cur): {cur_px.shape[1]}/{len(members)} 成分有数据 ({cov:.1f}%)")
    if cov < 90:
        raise RuntimeError(f"当前成分覆盖率 {cov:.1f}% < 90%,拒绝覆盖旧面板")
    if old is not None and cur_px.index.max() < old.index.max():
        raise RuntimeError(f"新面板最新日 {cur_px.index.max().date()} 倒退于旧 {old.index.max().date()},拒绝覆盖")

    unavail = _load_unavail()
    have = set(cur_px.columns) | (set(old.columns) if old is not None else set())
    todo = sorted(hist_union - set(members["symbol"]) - have - unavail)
    if todo:
        print(f"  历史死票待查 {len(todo)}(已存面板 {len(have)} 列,已知 yfinance 无 {len(unavail)})")
        dead_px, attempted = _yf_batches([(s.replace(".", "-"), s) for s in todo], "dead")
        got = set(dead_px.columns)
        _save_unavail(unavail | (attempted - got))
        print(f"  死票结果: yfinance 有 {len(got)}/{len(todo)},无 {len(attempted - got)}(记入 unavail)")
        if not dead_px.empty:
            cur_px = cur_px.join(dead_px, how="outer")
    if old is not None:                                          # 旧列(含先前并入的死票)沿用
        carry = [c for c in old.columns if c not in cur_px.columns]
        if carry:
            cur_px = cur_px.join(old[carry], how="outer")
            print(f"  carry-over 旧列 {len(carry)}(退市/先前死票,不重拉)")
    px = cur_px.sort_index()
    os.makedirs(SP500_CACHE_DIR, exist_ok=True)
    px.to_csv(PANEL_CSV, float_format="%.4f")
    print(f"OK  sp500_px            {px.shape[1]} tickers, {len(px)} rows "
          f"{px.index[0].date()}..{px.index[-1].date()} -> {PANEL_CSV} "
          f"({os.path.getsize(PANEL_CSV) // 1048576} MB)")
    # 回读落地文件再计算:与 --no-fetch 路径逐位一致(4dp round-trip,幂等可审计)
    return pd.read_csv(PANEL_CSV, index_col=0, parse_dates=True)


def load_membership_events(hist: pd.DataFrame, wiki_members: set[str]) -> list[tuple[pd.Timestamp, frozenset]]:
    """历史成分事件行 + 尾段(历史文件最后日期之后用 Wikipedia 当前清单)。"""
    ev = [(pd.Timestamp(d), frozenset(t.strip() for t in str(row).split(",")))
          for d, row in zip(hist["date"], hist["tickers"])]
    ev.sort()
    if wiki_members:
        ev.append((ev[-1][0] + pd.Timedelta(days=1), frozenset(wiki_members)))
    return ev


def build_mask(events, px: pd.DataFrame) -> pd.DataFrame:
    """时点成员掩码(dates × panel tickers,bool):事件行 ffill 到每个交易日。"""
    cols = list(px.columns)
    colidx = {c: i for i, c in enumerate(cols)}
    rows = np.zeros((len(events), len(cols)), dtype=bool)
    for i, (_, s) in enumerate(events):
        for t in s:
            j = colidx.get(t)
            if j is not None:
                rows[i, j] = True
    m = pd.DataFrame(rows, index=[d for d, _ in events], columns=cols)
    m = m[~m.index.duplicated(keep="last")]
    return m.reindex(px.index, method="ffill").fillna(False).astype(bool)


def compute_breadth(px: pd.DataFrame, mask: pd.DataFrame | None) -> pd.DataFrame:
    """% 收盘 > MA20/50/200;分母 = 当日 [成分 & MA 有效] 数(无价成分不进分子分母)。
    ffill(limit=3) 补 yfinance 零星空洞(只用过去值,因果;死票最多多算 3 天,
    且掩码在其被剔出成分后即为 False)。mask=None → 旧·当前成分法(用于偏差对照)。"""
    px = px.ffill(limit=3)
    out = pd.DataFrame(index=px.index)
    for k in (20, 50, 200):
        ma = px.rolling(k).mean()                                # 因果:只用过去 k 日
        valid = ma.notna() if mask is None else (ma.notna() & mask)
        above = (px > ma).where(valid)                           # 非成分/MA 不足 -> NaN,不进分母
        out[f"pct_above_ma{k}"] = above.mean(axis=1) * 100.0
        out[f"n_ma{k}"] = valid.sum(axis=1).astype(int)          # 当日分母,便于审计
    if mask is not None:                                         # 当日时点成分数(含无价者),列序兼容旧 schema
        out["n_members"] = mask.sum(axis=1).astype(int)
    return out.dropna(subset=["pct_above_ma20"])


def report_bias(after: pd.DataFrame, before: pd.DataFrame) -> dict:
    """对照官方 $S5TW/$S5FI/$S5TH:BEFORE(旧·当前成分法)vs AFTER(时点成分法)。"""
    stats = {}
    if not os.path.exists(OFFICIAL_CSV):
        print("  ! 无 breadth_official.csv(先跑 feeds/breadth_official.py),跳过偏差报告")
        return stats
    off = pd.read_csv(OFFICIAL_CSV, comment="#", index_col=0, parse_dates=True)
    print("  偏差 vs 官方(computed − official, pp):")
    for k in (20, 50, 200):
        col = f"pct_above_ma{k}"
        j = pd.concat([before[col], after[col], off[col]], axis=1,
                      keys=["before", "after", "off"], sort=True).dropna()
        db, da = j["before"] - j["off"], j["after"] - j["off"]
        early = j.index < "2013-01-01"
        stats[k] = {"n": len(j), "b_mean": db.mean(), "a_mean": da.mean(),
                    "b_mae": db.abs().mean(), "a_mae": da.abs().mean(),
                    "b_mean_early": db[early].mean(), "a_mean_early": da[early].mean()}
        s = stats[k]
        print(f"    MA{k:>3} overlap {s['n']}d ({j.index[0].date()}..{j.index[-1].date()}): "
              f"mean BEFORE {s['b_mean']:+.2f} -> AFTER {s['a_mean']:+.2f} | "
              f"MAE {s['b_mae']:.2f} -> {s['a_mae']:.2f} | "
              f"early(<2013) mean {s['b_mean_early']:+.2f} -> {s['a_mean_early']:+.2f}")
    return stats


def make_caveat(stats: dict, hist_end: str) -> str:
    c = ("# CAVEAT residual survivorship bias: membership is POINT-IN-TIME (fja05680/sp500, "
         f"1996+; after {hist_end} = current Wikipedia list), but delisted ex-members missing "
         "from yfinance are excluded from numerator AND denominator (they skew to losers -> "
         "slight overstatement, worst pre-2013). Prices are split-adjusted but dividend-"
         "UNadjusted Close (chart convention = official $S5xx basis; dividend-adjusted MAs "
         "would overstate breadth +2-3pp). n_ma* = daily denominator, n_members = PIT members "
         "present in the panel universe (coverage = n_ma*/n_members; true index count ~500). "
         "Renamed tickers (e.g. FB->META) drop out of the pre-rename window (noise, not "
         "directional).")
    if 200 in stats:
        s2, s5, s0 = stats[200], stats[50], stats[20]
        c += (f" Bias vs official $S5TW/FI/TH on {s2['n']}d overlap (mean, pp): MA200 "
              f"{s2['b_mean']:+.2f}(current-members method) -> {s2['a_mean']:+.2f}(PIT); "
              f"MA50 {s5['b_mean']:+.2f} -> {s5['a_mean']:+.2f}; "
              f"MA20 {s0['b_mean']:+.2f} -> {s0['a_mean']:+.2f}; pre-2013 MA200 "
              f"{s2['b_mean_early']:+.2f} -> {s2['a_mean_early']:+.2f}.")
    return c + " Read with comment='#'."


def main():
    if "--no-fetch" in sys.argv and os.path.exists(PANEL_CSV):
        px = pd.read_csv(PANEL_CSV, index_col=0, parse_dates=True)
        members = pd.read_csv(MEMBERS_CSV)
        hist = pd.read_csv(MEMBERS_HIST_CSV)
    else:
        members = fetch_members()
        hist = fetch_membership_history()
        union = set()
        for row in hist.loc[hist["date"] >= HIST_FROM, "tickers"]:
            union |= {t.strip() for t in str(row).split(",")}
        px = fetch_panel(members, union)
    events = load_membership_events(hist, set(members["symbol"]))
    mask = build_mask(events, px)
    out = compute_breadth(px, mask)
    before = compute_breadth(px[[c for c in members["symbol"] if c in px.columns]], None)
    stats = report_bias(out, before)
    caveat = make_caveat(stats, str(hist["date"].iloc[-1]))
    path = save(out, "breadth_stocks", "個股寬度(% > MA)")
    with open(path) as f:                                        # caveat 注释写进 CSV 首行
        body = f.read()
    with open(path, "w") as f:
        f.write(caveat + "\n" + body)
    latest = out.iloc[-1]
    print(f"      latest {out.index[-1].date()}: >MA20 {latest['pct_above_ma20']:.1f}%  "
          f">MA50 {latest['pct_above_ma50']:.1f}%  >MA200 {latest['pct_above_ma200']:.1f}%  "
          f"(n={int(latest['n_ma200'])}/{int(latest['n_members'])})")


if __name__ == "__main__":
    main()
