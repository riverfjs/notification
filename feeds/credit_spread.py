#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26", "requests>=2.31"]
# ///
"""信用利差 + VIX(原图为「信用利差, VIX & S&P500」)— 官方 FRED API。日频,回溯 1986/1990。
每天可跑刷新。信用利差急扩 = risk-off 的核心 regime 信号。

高收益(HY)腿(P2 升级):
- BAMLH0A0HYM2(ICE BofA US HY OAS)被 FRED 授权砍到只剩最近 3 年(现 2023-06-05 起)。
  完整 1996-12-31+ 历史来自 Wayback Machine 存档的官方 fredgraph.csv 快照(2025-11-04 存档,
  截断之前抓取)。首跑下载后缓存到 data/macro/hy_oas_mirror.csv(冻结历史,之后离线复用)。
  每次运行都把镜像与官方 API 的重叠段逐位核对:全对才拼成 hy_oas_full,否则降级为 API 段并告警。
  (实测 2026-06:重叠 633 个交易日 0 处不一致;2008-12-15=21.82 全时段最高、2020-03-23=10.87,
  与公开记录完全一致。)
- hy_stress:用本仓库已有的 data/HYG.csv(2007-04+)/ data/TLT.csv 复权收盘构造的 HY 压力代理 =
  HYG/TLT 比值相对其过去 252 个交易日最高点的回撤(%)。纯历史滚动,无前视。
  实测与 baa_10y_spread 相关 0.76、与真 HY OAS 相关 0.75;2008-12-17 回撤 47%、2020-03-23 回撤
  40% 为样本两大极值,方向正确(压力越大值越高)。

注意:Moody's Baa/Aaa 对国债利差(深历史、无授权限制)继续保留,覆盖 2000/2008。"""
import pandas as pd

from _common import _get, fred, read_price, save

# Wayback 存档的官方 FRED CSV(2025-11-04 快照,含 1996-12-31..2025-11-03 完整历史)
MIRROR_URL = ("https://web.archive.org/web/20251104204105id_/"
              "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2")
MIRROR_CACHE = "hy_oas_mirror"  # data/macro/hy_oas_mirror.csv


def _load_mirror() -> pd.Series | None:
    """读本地镜像缓存;没有则从 Wayback 拉一次并落盘(gzip 由 zlib 解,失败返回 None)。"""
    import gzip
    import os

    from _common import MACRO_DIR
    path = os.path.join(MACRO_DIR, f"{MIRROR_CACHE}.csv")
    if os.path.exists(path):
        s = pd.read_csv(path, index_col=0, parse_dates=True)["hy_oas"]
        return s.dropna()
    try:
        raw = _get(MIRROR_URL, retries=3, pause=3.0, timeout=60).content
        if raw[:2] == b"\x1f\x8b":  # archive.org 常回 gzip 原文
            raw = gzip.decompress(raw)
        from io import StringIO
        df = pd.read_csv(StringIO(raw.decode("utf-8")))
        df.columns = ["date", "hy_oas"]
        df["date"] = pd.to_datetime(df["date"])
        s = df.set_index("date")["hy_oas"]
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < 7000 or s.index.min() > pd.Timestamp("1997-01-15"):
            print(f"WARN hy mirror looks wrong ({len(s)} rows from {s.index.min()}), skip")
            return None
        os.makedirs(MACRO_DIR, exist_ok=True)
        s.rename("hy_oas").to_csv(path)
        print(f"      hy mirror cached -> {path} ({len(s)} rows "
              f"{s.index.min().date()}..{s.index.max().date()})")
        return s
    except Exception as e:  # noqa: BLE001
        print(f"WARN hy mirror fetch failed ({str(e)[:80]}), hy_oas_full = API segment only")
        return None


def _hy_oas_full() -> pd.Series:
    """官方 API 段(2023-06+)+ 镜像历史段(1996-12-31+),重叠段逐位核对后拼接。"""
    api = fred([("BAMLH0A0HYM2", "hy_oas")])["hy_oas"].dropna()
    mirror = _load_mirror()
    if mirror is None:
        return api
    common = api.index.intersection(mirror.index)
    mism = (api.loc[common] - mirror.loc[common]).abs() > 1e-9
    if mism.any():
        bad = common[mism]
        print(f"WARN hy mirror/API mismatch on {len(bad)} dates (first {bad[0].date()}), "
              "NOT stitching — hy_oas_full = API segment only")
        return api
    print(f"      hy mirror validated: {len(common)} overlap dates exact-match API")
    return pd.concat([mirror[mirror.index < api.index.min()], api]).sort_index()


def _hy_stress() -> pd.DataFrame:
    """HYG/TLT 复权收盘比值 + 其对过去 252 日最高点的回撤(%)。因果(纯 trailing)。"""
    hyg = read_price("HYG")["c"]
    tlt = read_price("TLT")["c"]
    px = pd.concat({"hyg": hyg, "tlt": tlt}, axis=1, sort=True).dropna()
    out = pd.DataFrame(index=px.index)
    out["hyg_tlt_ratio"] = px["hyg"] / px["tlt"]
    trail_max = out["hyg_tlt_ratio"].rolling(252, min_periods=63).max()
    out["hy_stress"] = 100.0 * (1.0 - out["hyg_tlt_ratio"] / trail_max)
    return out


def main():
    df = fred([
        ("BAA10Y", "baa_10y_spread"),  # Moody's Baa 公司债 − 10年国债(信用压力,1986+)
        ("AAA10Y", "aaa_10y_spread"),  # Moody's Aaa − 10年国债(高等级利差,1983+)
        ("VIXCLS", "vix"),             # VIX 收盘(1990+)
    ])
    df["baa_aaa_quality"] = df["baa_10y_spread"] - df["aaa_10y_spread"]  # 质量利差 Baa−Aaa
    df = pd.concat([df, _hy_oas_full().rename("hy_oas_full"), _hy_stress()],
                   axis=1, sort=True)
    save(df, "credit_spread", "信用利差&VIX")


if __name__ == "__main__":
    main()
