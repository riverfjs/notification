import type { SeriesSpec } from "../charts/types";
import { loadCsv, pairs } from "./csv";
import { scale as scalePairs, stitch, yoy, type Pair } from "./transform";

type DataSeriesSpec = Pick<SeriesSpec, "csv" | "col" | "append" | "yoyMonths" | "scale">;

export async function seriesData(s: DataSeriesSpec): Promise<Pair[]> {
  let d = pairs(await loadCsv(s.csv), s.col);
  if (s.append) {
    const b = pairs(await loadCsv(s.append.csv), s.append.col);
    d = stitch(d, b, s.append.cut);
  }
  if (s.yoyMonths) d = yoy(d, s.yoyMonths);
  if (s.scale !== undefined) d = scalePairs(d, s.scale);
  return d;
}
