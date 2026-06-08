import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardAction, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import type { SeriesSpec } from "../charts/types";
import { seriesData } from "../lib/seriesData";
import { last } from "../lib/transform";

export interface KpiSpec extends Pick<SeriesSpec, "csv" | "col" | "append" | "yoyMonths" | "scale"> {
  title: string;
  fmt?: "pct" | "num";
  digits?: number;
  compact?: boolean;
  /** 高位是好(绿)还是坏(红);undefined = 中性灰 */
  goodWhen?: "high" | "low";
  /** 额外说明,如阈值 */
  hint?: string;
}

/** shadcn dashboard-01 的 KPI 卡范式:Description=标签 / Title=大数字 /
 *  Action=涨跌 Badge / Footer=注脚。标题与注脚各锁一行截断,同行等高。 */
export function KpiCard({ spec, onClick }: { spec: KpiSpec; onClick?: () => void }) {
  const [v, setV] = useState<{ date: string; value: number; prev: number | null } | null>(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    let dead = false;
    seriesData(spec)
      .then((d) => !dead && setV(last(d)))
      .catch(() => !dead && setErr(true));
    return () => {
      dead = true;
    };
  }, [spec]);

  const d = spec.digits ?? 2;
  const delta = v && v.prev !== null ? v.value - v.prev : null;
  const fmtValue = (x: number) =>
    spec.compact
      ? x.toLocaleString("en-US", { notation: "compact", maximumFractionDigits: d })
      : x.toFixed(d);
  const deltaCls =
    delta === null
      ? "text-muted-foreground"
      : spec.goodWhen === undefined
        ? delta >= 0 ? "text-up" : "text-down"
        : (delta >= 0) === (spec.goodWhen === "high")
          ? "text-up"
          : "text-down";
  const valueCls =
    delta === null || Math.abs(delta) < 1e-12
      ? "text-muted-foreground"
      : deltaCls;

  return (
    <Card
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onClick?.()}
      title={`${spec.title}${spec.hint ? ` · ${spec.hint}` : ""}`}
      className="h-full gap-1.5 py-4 cursor-pointer hover:border-input transition-colors"
    >
      <CardHeader className="px-4 gap-1">
        <CardDescription className="text-xs truncate">{spec.title}</CardDescription>
        <CardTitle className="num text-2xl whitespace-nowrap">
          {err ? "—" : v ? fmtValue(v.value) : "…"}
          {spec.fmt === "pct" && !err && v ? <span className="text-sm">%</span> : null}
        </CardTitle>
        {delta !== null && (
          <CardAction>
            <Badge variant="outline" className={`num ${valueCls}`} title={`上一期变化: ${delta >= 0 ? "+" : ""}${delta.toFixed(d)}`}>
              {delta >= 0 ? "+" : ""}
              {fmtValue(delta)}
            </Badge>
          </CardAction>
        )}
      </CardHeader>
      <CardFooter className="px-4">
        <span className="num text-[10px] text-muted-foreground/60 truncate">
          {v?.date ?? ""}
          {spec.hint ? ` · ${spec.hint}` : ""}
        </span>
      </CardFooter>
    </Card>
  );
}
