/** CSV 数据层:直接拉仓库 raw 文件(公开仓库自带 CDN),内存缓存。
 *  数据每天由 GitHub Actions 刷新提交 → 页面随时 fetch 都是最新,无需重新部署。 */

const DEFAULT_DATA_BASE = "https://raw.githubusercontent.com/riverfjs/notification/main/data";
const DATA_BASE = (import.meta.env.VITE_DATA_BASE || DEFAULT_DATA_BASE).replace(/\/$/, "");

export interface Table {
  /** ISO 日期字符串,升序 */
  dates: string[];
  /** 列名 → 数值数组(与 dates 对齐,缺测为 null) */
  cols: Record<string, (number | null)[]>;
}

const cache = new Map<string, Promise<Table>>();

/** name: "macro/fng" | "tickers/VIX" | "spot/XAUUSD" 等,相对 data/ 的路径(不带 .csv) */
export function loadCsv(name: string): Promise<Table> {
  let p = cache.get(name);
  if (!p) {
    p = fetchCsv(name);
    p.catch(() => cache.delete(name)); // 失败不缓存:网络抖动后重试可恢复
    cache.set(name, p);
  }
  return p;
}

async function fetchCsv(name: string): Promise<Table> {
  const res = await fetch(`${DATA_BASE}/${name}.csv`);
  if (!res.ok) throw new Error(`fetch ${name}.csv: HTTP ${res.status}`);
  return parseCsv(await res.text());
}

/** 解析:跳过 # 注释行;首列为日期,其余转 number(空/非数 → null)。 */
export function parseCsv(text: string): Table {
  const lines = text.split(/\r?\n/).filter((l) => l && !l.startsWith("#"));
  const header = lines[0].split(",").map((h) => h.trim());
  const names = header.slice(1);
  const dates: string[] = [];
  const cols: Record<string, (number | null)[]> = {};
  for (const n of names) cols[n] = [];
  for (let i = 1; i < lines.length; i++) {
    const cells = lines[i].split(",");
    const d = cells[0]?.slice(0, 10);
    if (!d) continue;
    dates.push(d);
    for (let j = 0; j < names.length; j++) {
      const v = cells[j + 1]?.trim();
      const f = v === undefined || v === "" ? NaN : Number(v); // 空白单元格 → null(Number(' ')===0 陷阱)
      cols[names[j]].push(Number.isFinite(f) ? f : null);
    }
  }
  return { dates, cols };
}

/** 取一列为 [date, value][](去 null) */
export function pairs(t: Table, col: string): [string, number][] {
  const out: [string, number][] = [];
  const c = t.cols[col];
  if (!c) throw new Error(`列不存在: ${col}(有 ${Object.keys(t.cols).join(",")})`);
  for (let i = 0; i < t.dates.length; i++) {
    const v = c[i];
    if (v !== null) out.push([t.dates[i], v]);
  }
  return out;
}
