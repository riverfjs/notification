import { useEffect, useMemo, useRef, useState } from "react";
import { Layers, Maximize2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardAction, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { ChartSpec, SeriesSpec } from "../charts/types";
import { baseOption, echarts, INK2, PALETTE, yAxis } from "../charts/theme";
import { loadCsv, pairs } from "../lib/csv";
import { stitch, yoy, scale as scalePairs, type Pair } from "../lib/transform";

const RANGES: { label: string; years: number | null }[] = [
  { label: "1Y", years: 1 },
  { label: "3Y", years: 3 },
  { label: "10Y", years: 10 },
  { label: "全部", years: null },
];

async function seriesData(s: SeriesSpec): Promise<Pair[]> {
  let d = pairs(await loadCsv(s.csv), s.col);
  if (s.append) {
    const b = pairs(await loadCsv(s.append.csv), s.append.col);
    d = stitch(d, b, s.append.cut);
  }
  if (s.yoyMonths) d = yoy(d, s.yoyMonths);
  if (s.scale !== undefined) d = scalePairs(d, s.scale);
  return d;
}

/** 对比视图的缩放联动:按【日期】对齐(echarts.connect 是按百分比,两图历史长度
 *  不同会错位)。同组任一图缩放 → 把它的 startValue/endValue 原样派发给其余图。 */
const syncGroups = new Map<string, Set<echarts.ECharts>>();
let syncing = false;

function joinSync(group: string, chart: echarts.ECharts) {
  let set = syncGroups.get(group);
  if (!set) syncGroups.set(group, (set = new Set()));
  set.add(chart);
  chart.on("dataZoom", () => {
    if (syncing) return;
    const dz = (chart.getOption() as { dataZoom?: { startValue?: number; endValue?: number }[] }).dataZoom?.[0];
    if (!dz || dz.startValue === undefined) return;
    syncing = true;
    try {
      for (const other of set!) {
        if (other !== chart && !other.isDisposed()) {
          other.dispatchAction({ type: "dataZoom", startValue: dz.startValue, endValue: dz.endValue });
        }
      }
    } finally {
      syncing = false;
    }
  });
}

export function ChartCard({
  spec,
  syncGroup,
  onFullscreen,
  compared,
  onCompare,
}: {
  spec: ChartSpec;
  /** 对比视图传同一个组名 → 缩放跨图按日期联动 */
  syncGroup?: string;
  onFullscreen?: () => void;
  compared?: boolean;
  onCompare?: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [err, setErr] = useState("");
  const [latest, setLatest] = useState<{ date: string; value: number } | null>(null);
  // number=最近 N 年 / null=全部 / "custom"=已被拖拽或同步缩放(无预设高亮)
  const [range, setRange] = useState<number | null | "custom">(spec.defaultYears ?? 10);
  const progZoom = useRef(false);   // 本图自己派发缩放时置位,避免误清高亮

  // 数据 + 渲染
  useEffect(() => {
    let dead = false;
    (async () => {
      try {
        const data = await Promise.all(spec.series.map(seriesData));
        if (dead || !ref.current) return;
        const chart = echarts.init(ref.current);
        chartRef.current = chart;
        if (syncGroup) joinSync(syncGroup, chart);
        // 用户拖拽 / 对比同步推来的缩放(非预设按钮)→ 清掉区间高亮(变 custom)
        chart.on("dataZoom", () => {
          if (!progZoom.current) setRange("custom");
        });

        const first = data[0];
        if (first.length) setLatest({ date: first[first.length - 1][0], value: first[first.length - 1][1] });

        const opt: Record<string, unknown> = {
          ...baseOption(),
          yAxis: [
            yAxis({ ...spec.y0, position: "left" }),
            ...(spec.y1 ? [yAxis({ ...spec.y1, position: "right" })] : []),
          ],
          series: spec.series.map((s, i) => ({
            type: "line",
            name: s.name,
            data: data[i],
            yAxisIndex: s.axis ?? 0,
            showSymbol: false,
            connectNulls: false,
            step: s.step ? "end" : undefined,
            lineStyle: { width: 1.4 },
            emphasis: { focus: "series" },
            areaStyle: s.area ? { opacity: 0.12 } : undefined,
            color: s.color ?? PALETTE[i % PALETTE.length],
            // 参考线挂在第一条系列上
            markLine:
              i === 0 && (spec.hLines?.length || spec.vLines?.length)
                ? {
                    symbol: "none",
                    silent: true,
                    label: { color: INK2, fontSize: 10, position: "insideEndTop" },
                    lineStyle: { color: "#575652", type: "dashed", width: 1 },
                    data: [
                      ...(spec.hLines ?? []).map((h) => ({ yAxis: h.value, label: { formatter: h.label ?? String(h.value) } })),
                      // 垂直参考线的标签沿线旋转,避免窄空间里汉字被逐字竖排挤压
                      ...(spec.vLines ?? []).map((v) => ({
                        xAxis: v.date,
                        label: { formatter: v.label ?? v.date, rotate: 90, position: "insideEndTop" as const, distance: 6 },
                      })),
                    ],
                  }
                : undefined,
          })),
          legend: {
            ...(baseOption().legend as object),
            selected: Object.fromEntries(spec.series.filter((s) => s.off).map((s) => [s.name, false])),
          },
        };
        chart.setOption(opt);
        setState("ready");
      } catch (e) {
        if (!dead) {
          setErr(String(e));
          setState("error");
        }
      }
    })();
    const onResize = () => chartRef.current?.resize();
    window.addEventListener("resize", onResize);
    return () => {
      dead = true;
      window.removeEventListener("resize", onResize);
      if (syncGroup && chartRef.current) syncGroups.get(syncGroup)?.delete(chartRef.current);
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, [spec, syncGroup]);

  // 区间切换(仅预设;custom 是缩放产生的结果状态,不回写视图)
  useEffect(() => {
    const c = chartRef.current;
    if (!c || state !== "ready" || range === "custom") return;
    progZoom.current = true;          // 本次派发是预设,别被 dataZoom 监听清掉高亮
    if (range === null) {
      c.dispatchAction({ type: "dataZoom", start: 0, end: 100 });
    } else {
      const end = latest ? new Date(latest.date).getTime() : Date.now();
      const start = end - range * 365.25 * 86400_000;
      c.dispatchAction({ type: "dataZoom", startValue: start, endValue: end });
    }
    requestAnimationFrame(() => (progZoom.current = false));
  }, [range, state, latest]);

  const latestText = useMemo(() => {
    if (!latest) return "";
    const v = latest.value;
    const s = Math.abs(v) >= 1000 ? v.toLocaleString("en-US", { maximumFractionDigits: 0 }) : v.toFixed(2);
    return `${s}${spec.y0?.fmt === "pct" ? "%" : ""}`;
  }, [latest, spec]);

  return (
    <Card className="h-full gap-2 py-4 hover:border-input transition-colors">
      <CardHeader className="px-4 gap-0.5">
        <CardTitle className="text-[15px] truncate" title={spec.title}>{spec.title}</CardTitle>
        <CardDescription className="text-xs truncate" title={spec.subtitle}>{spec.subtitle ?? " "}</CardDescription>
        <CardAction className="flex items-center gap-2 flex-wrap justify-end">
          {latest && (
            <Badge variant="outline" className="num text-primary hidden sm:inline-flex" title={`首列系列最新值 · ${latest.date}`}>
              {latestText}
              <span className="text-muted-foreground/60">{latest.date.slice(2)}</span>
            </Badge>
          )}
          <ToggleGroup
            type="single"
            size="sm"
            variant="outline"
            value={range === "custom" ? "" : String(range)}
            onValueChange={(v) => v && setRange(v === "null" ? null : Number(v))}
          >
            {RANGES.map((r) => (
              <ToggleGroupItem
                key={r.label}
                value={String(r.years)}
                aria-label={r.label}
                className="num px-2 text-[11px] h-7 data-[state=on]:bg-primary/15 data-[state=on]:text-primary"
              >
                {r.label}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
          {onCompare && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant={compared ? "default" : "outline"}
                  size="icon"
                  className="size-7"
                  onClick={onCompare}
                  aria-label={compared ? "移出对比" : "加入对比"}
                >
                  <Layers className="size-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>{compared ? "移出对比" : "加入对比"}</TooltipContent>
            </Tooltip>
          )}
          {onFullscreen && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="outline" size="icon" className="size-7" onClick={onFullscreen} aria-label="全屏查看">
                  <Maximize2 className="size-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>全屏查看</TooltipContent>
            </Tooltip>
          )}
        </CardAction>
      </CardHeader>
      <CardContent className="px-4 flex-1 min-h-0">
        <div className="relative h-full">
          <div ref={ref} className="absolute inset-0" />
          {state === "loading" && (
            <div className="absolute inset-0 flex items-center justify-center text-muted-foreground/60 text-sm num animate-pulse">loading…</div>
          )}
          {state === "error" && (
            <div className="absolute inset-0 flex items-center justify-center text-down text-xs px-6 text-center">{err}</div>
          )}
        </div>
      </CardContent>
      <CardFooter className="px-4">
        <p className="text-[11px] leading-snug text-muted-foreground/60 border-t pt-1.5 line-clamp-2 min-h-[2.1em] w-full" title={spec.note}>
          {spec.note ?? ""}
        </p>
      </CardFooter>
    </Card>
  );
}
