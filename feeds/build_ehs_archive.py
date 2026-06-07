#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "numpy>=1.26"]
# ///
"""一次性构建/重建 成屋销售(NAR Existing Home Sales, SAAR)历史 → feeds/ehs_archive.csv

【P14 调研结论(2026-06-07,全部实测,找"单一 vintage 全史")】
免费源里不存在真·单一 vintage 全史,三条候选路线全部排除:
  ① Wayback 的 fredgraph.csv?id=EXHOSLUSM495S:全量 CDX 枚举只有 2 个 capture
     (20260322062917 / 20260409184228,同 digest),内容都是 13 个月窗口
     (2025-02..2026-02)。更关键:FRED 在 Wayback 可见年代从未有过全史 ——
     fred2 系列页 2013-11 快照显示 Date Range 自 1999-01 起,但该年代的数据文件
     (fred2/data .txt、downloaddata csv、viewdata、ALFRED 下载)无任何 capture;
     2016-12 起 /data/EXHOSLUSM495S.txt 的 Date Range 已是滚动窗
     (2017-05 快照:2013-01..2017-03;2019-01 快照:2017-11..2018-11 ≈13 个月)。
     所谓"被砍前全史快照"不存在,NAR 授权窗口早于 Wayback 数据覆盖。
  ② FRED vintage 接口:/fred/series/vintagedates 与 observations?vintage_dates=
     都返回 HTTP 400 "series does not exist in ALFRED"(realtime_* 此前也是 400)。
  ③ DBnomics NAR 当前序列(api.db.nomics.world v22 NAR/ehs/ehs_mo_us_sa):
     只有 13 个月(2023-07..2024-07),且 dataset 2024-08-23 后停更。
  (附:Quandl/FRED 镜像、ALFRED 下载、realtor.org 免费 xls 的 Wayback capture
   也逐一查过 = 无;Trading Economics guest key 已停用。)

【最终口径(本脚本产物)】两段 + 单一 seam:
  - 2025-02 起:官方当前 vintage —— 官方 FRED API 滚动窗口(运行日 vintage)
    ∪ 2026-03-22 的 fredgraph 快照(2025-02..2026-02,同属 2026-02 年度重订后
    家族,重叠段与 API 逐位一致)。单一 seam 在 2025-01/2025-02。
  - 2013-01..2025-01:各月「最后可得修订值」(由下列镜像合并,同月取 vintage
    最新者)。NAR 只在每年 2 月重订最近 ~3 年的季调数据,其余月份为终值;
    本脚本对跨 2 月重订的快照重叠段做量化(运行输出 revision audit,2026-06-07
    实测:跨重订 n=40 mean|Δ|=0.82% max=2.81%,未跨 n=118 mean=0.83% max=2.65%),
    即历史段与"今天的单一 vintage"的偏差有界且很小(<3%,均值 <1%)。

镜像源(同 P8):
  1. Wayback 上 fred.stlouisfed.org 的历史快照(/data/….txt、/data/… HTML、
     /graph/fredgraph.csv)
  2. DBnomics 的 NAR 抓取仓库 git.nomics.world(dbnomics-json-data/nar-json-data,
     ehs/ehs_mo_us_sa.tsv),62 个 commit(2018-10..2024-08)= 62 份 13 个月窗口

幂等/韧性:先从现有 feeds/ehs_archive.csv 播种(老月份/未来 API 月份不丢),
再叠加镜像与官方 API;wayback 间歇 503 时单源失败只 WARN 不中断。
ONE-OFF 构建脚本,不进 run_all.py;日常续更由 home_sales_prices.py 用官方
FRED API 窗口自动回写 feeds/ehs_archive.csv。
"""
import csv
import hashlib
import os
import re
import tempfile
import time
from datetime import date

from _common import HERE, _get, fred

ARCHIVE = os.path.join(HERE, "ehs_archive.csv")
CACHE = os.path.join(tempfile.gettempdir(), "ehs_archive_cache")  # wayback 限速,缓存助重跑

WB = "https://web.archive.org/web/{ts}if_/{url}"
FRED_TXT = "https://fred.stlouisfed.org/data/EXHOSLUSM495S.txt"
FRED_HTML = "https://fred.stlouisfed.org/data/EXHOSLUSM495S"
FRED_GRAPH = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=EXHOSLUSM495S"

# 全部已知含数据的 Wayback 快照(CDX api 枚举所得,collapse=digest)
TXT_SNAPS = [
    "20161202003617", "20170111220137", "20170218215357", "20170225061822",
    "20170323200300", "20170411190747", "20170518030741", "20170629062932",
    "20171124234936", "20190117033623", "20200701202402", "20200805142131",
    "20200911083600", "20201006052228", "20201023135651", "20201124124052",
    "20210204085611", "20210301134609", "20210401151402", "20210520202017",
    "20210907113806", "20211113152810", "20220706041130", "20230110142214",
    "20231204162720", "20231223121937", "20240228062000",
]
HTML_SNAPS = ["20241027010823", "20250425221322", "20250929234324",
              "20251030131156", "20251204233850"]
GRAPH_SNAPS = ["20260322062917"]   # 20260409184228 同 digest,跳过

# DBnomics 的 NAR 抓取仓库(GitLab project id 238)
GL = "https://git.nomics.world/api/v4/projects/238/repository"
TSV_PATH = "ehs%2Fehs_mo_us_sa.tsv"


def cached_get(url: str, retries: int = 6, pause: float = 5) -> str:
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest()[:24])
    if os.path.exists(p):
        with open(p) as f:
            return f.read()
    text = _get(url, retries=retries, pause=pause, timeout=60).text
    with open(p, "w") as f:
        f.write(text)
    return text


def wb_get(ts: str, url: str) -> str:
    return cached_get(WB.format(ts=ts, url=url))


def parse_rows(text: str) -> list[tuple[str, float]]:
    """提取 (YYYY-MM-01, value) 行;兼容 .txt 表格 / fredgraph CSV / 数据页 HTML。"""
    plain = re.sub(r"<[^>]+>", " ", text)
    rows = re.findall(r"(\d{4}-\d{2}-01)[\s,]+(\d{6,8})(?:\.0*)?\b", plain)
    return [(d, float(v)) for d, v in rows]


def crosses_february(v1: str, v2: str) -> bool:
    """两个 vintage 日期之间是否跨过任何一个「2 月末」(NAR 年度重订发布点)。"""
    y1, m1 = int(v1[:4]), int(v1[5:7])
    y2, m2 = int(v2[:4]), int(v2[5:7])
    # 重订随每年 2 月下旬的 1 月数据发布落地;近似按「跨过 3 月 1 日」判定
    return (y2 + (1 if m2 >= 3 else 0)) > (y1 + (1 if m1 >= 3 else 0))


def main():
    obs: dict[str, tuple[str, float, str]] = {}     # month -> (vintage, value, source)
    all_obs: dict[str, list[tuple[str, float]]] = {}  # month -> [(vintage, value)] 修订审计用

    def put(month: str, vintage: str, value: float, source: str, audit: bool = True):
        if audit:
            all_obs.setdefault(month, []).append((vintage, value))
        if month not in obs or vintage > obs[month][0]:
            obs[month] = (vintage, value, source)

    # --- 0) 播种:现有 archive(韧性 —— 单源 503 / API 窗口滚动也不丢月份)---
    if os.path.exists(ARCHIVE):
        with open(ARCHIVE) as f:
            n = 0
            for r in csv.DictReader(f):
                put(r["date"], r["vintage"], float(r["existing_home_sales"]),
                    r["source"], audit=False)
                n += 1
        print(f"seed from existing archive: {n} rows")

    # --- 1) Wayback FRED 快照 ---
    for ts, url, src in (
        [(t, FRED_TXT, "fred_wayback_txt") for t in TXT_SNAPS]
        + [(t, FRED_HTML, "fred_wayback_html") for t in HTML_SNAPS]
        + [(t, FRED_GRAPH, "fred_wayback_graph") for t in GRAPH_SNAPS]
    ):
        vintage = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
        try:
            rows = parse_rows(wb_get(ts, url))
        except RuntimeError as e:
            print(f"WARN wayback {ts}: {str(e).splitlines()[-1].strip()}")
            continue
        if not rows:
            print(f"WARN wayback {ts}: 0 rows")
            continue
        for d, v in rows:
            put(d, vintage, v, src)
        print(f"wayback {vintage}  {rows[0][0]}..{rows[-1][0]}  ({len(rows)} rows)")
        time.sleep(1)

    # --- 2) DBnomics NAR git 全部 commit(每个 = 一份 NAR 13 个月窗口 vintage)---
    import json
    try:
        commits = json.loads(cached_get(f"{GL}/commits?path=ehs/ehs_mo_us_sa.tsv&per_page=100"))
    except RuntimeError as e:
        print(f"WARN nar git commits: {str(e).splitlines()[-1].strip()}")
        commits = []
    print(f"nar git: {len(commits)} commits")
    for c in commits:
        vintage = c["committed_date"][:10]
        try:
            tsv = cached_get(f"{GL}/files/{TSV_PATH}/raw?ref={c['id']}", retries=2, pause=2)
        except RuntimeError as e:   # 个别早期 commit 是旧目录布局,文件 404
            print(f"WARN nar git {vintage}: {str(e).splitlines()[-1].strip()}")
            continue
        n = 0
        for line in tsv.splitlines()[1:]:
            parts = line.split("\t")
            if len(parts) >= 2 and re.match(r"^\d{4}-\d{2}$", parts[0]):
                put(parts[0] + "-01", vintage, float(parts[1]), "nar_dbnomics_git")
                n += 1
        print(f"nar git {vintage}  ({n} rows)")
        time.sleep(0.4)

    # --- 3) 官方 FRED API 当前窗口 = 当前 vintage,整段统一标 fred_api ---
    today = date.today().isoformat()
    api = fred([("EXHOSLUSM495S", "ehs")])["ehs"].dropna()
    for ts_, v in api.items():
        put(ts_.strftime("%Y-%m-%d"), today, float(v), "fred_api")
    print(f"fred api window  {api.index.min().date()}..{api.index.max().date()}  "
          f"({len(api)} rows)  vintage={today}")

    # --- 4) revision audit:量化「最后可得修订值」与单一 vintage 的偏差 ---
    same = diff_feb = diff_nofeb = 0
    feb_deltas, nofeb_deltas = [], []
    for m, lst in all_obs.items():
        lst = sorted(set(lst))
        for (v1, x1), (v2, x2) in zip(lst, lst[1:]):
            if x1 == x2:
                same += 1
                continue
            d = abs(x2 - x1) / x1 * 100
            if crosses_february(v1, v2):
                diff_feb += 1
                feb_deltas.append((d, m, v1, v2, x1, x2))
            else:
                diff_nofeb += 1
                nofeb_deltas.append((d, m, v1, v2, x1, x2))
    print("\nrevision audit (相邻 vintage 重叠对):")
    print(f"  值不变: {same}   跨2月重订且变: {diff_feb}   未跨重订且变: {diff_nofeb}")
    for tag, ds in (("跨2月重订", feb_deltas), ("未跨重订(初值→修订)", nofeb_deltas)):
        if ds:
            ds.sort(reverse=True)
            mean = sum(x[0] for x in ds) / len(ds)
            d, m, v1, v2, x1, x2 = ds[0]
            print(f"  {tag}: n={len(ds)}  mean|Δ|={mean:.2f}%  "
                  f"max|Δ|={d:.2f}% ({m}: {x1:.0f}@{v1} -> {x2:.0f}@{v2})")

    # --- 5) 写出 ---
    months = sorted(obs)
    gaps = []
    for a, b in zip(months, months[1:]):
        if (int(b[:4]) * 12 + int(b[5:7])) - (int(a[:4]) * 12 + int(a[5:7])) != 1:
            gaps.append((a, b))
    print(f"\nspan {months[0]}..{months[-1]}  n={len(months)}  gaps={gaps or 'NONE'}")
    seg = sum(1 for a, b in zip(months, months[1:]) if obs[a][0] != obs[b][0]) + 1
    cur = [m for m in months if obs[m][0] >= "2026-03-22" or obs[m][2] == "fred_api"]
    print(f"vintage segments={seg};当前 vintage 段(2026-02 重订后)= "
          f"{cur[0] if cur else '-'}..{cur[-1] if cur else '-'}  ({len(cur)} 个月)")

    with open(ARCHIVE, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "existing_home_sales", "vintage", "source"])
        for m in months:
            vintage, value, source = obs[m]
            w.writerow([m, f"{value:.0f}", vintage, source])
    print(f"wrote {ARCHIVE}  ({len(months)} rows)")


if __name__ == "__main__":
    main()
