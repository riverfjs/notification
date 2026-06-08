import { GROUPS } from "../charts/groups";
import type { AxisSpec, ChartSpec, SeriesSpec } from "../charts/types";
import { KpiCard, type KpiSpec } from "../components/KpiCard";

type Kpi = KpiSpec & { nav: string };

const OVERRIDES: Record<string, Partial<KpiSpec>> = {
  "macro/fng:fng": { title: "CNN Fear & Greed", digits: 0, goodWhen: "high", hint: "≤25 恐慌 / ≥75 贪婪" },
  "tickers/VIX:c": { title: "VIX", goodWhen: "low", hint: ">30 高波动" },
  "macro/breadth_official:pct_above_ma200": { title: "标普500 > MA200", digits: 1, goodWhen: "high", hint: "≤15 washout / ≥85 过热" },
  "macro/putcall_cboe:equity_pc": { title: "股票 Put/Call", goodWhen: "low", hint: ">1 恐慌 / <0.5 自满" },
  "macro/credit_spread:hy_oas_full": { title: "高收益债 OAS", fmt: "pct", goodWhen: "low", hint: ">6% 信用承压" },
  "macro/rates:curve_10y_2y": { title: "10Y−2Y 期限利差", fmt: "pct", goodWhen: "high", hint: "<0 倒挂" },
  "macro/jobs_monthly:unemployment_rate_pct": { title: "失业率", fmt: "pct", digits: 1, goodWhen: "low" },
  "macro/claims_weekly:initial_claims_weekly": { title: "初请失业金", scale: 0.001, digits: 0, goodWhen: "low", hint: "千人/周" },
  "macro/ism_pmi:ism_pmi": { title: "ISM 制造业 PMI", digits: 1, goodWhen: "high", hint: "50 荣枯线" },
  "macro/naaim:naaim_mean": { title: "NAAIM 平均仓位", digits: 0, hint: "≤20 防御 / ≥90 拥挤" },
  "macro/aaii:bull_bear_spread": { title: "AAII 多空差", digits: 1, goodWhen: "high", hint: "百分点,≤−20 极端看空" },
  "macro/copper_gold_ppi:copper_gold_ratio_daily": { title: "铜金比(日)", digits: 2, goodWhen: "high", hint: "升=再通胀 risk-on" },
};

function axisFor(chart: ChartSpec, series: SeriesSpec): AxisSpec | undefined {
  return series.axis === 1 ? chart.y1 : chart.y0;
}

function fmtFor(chart: ChartSpec, series: SeriesSpec): "pct" | "num" | undefined {
  if (series.yoyMonths) return "pct";
  return axisFor(chart, series)?.fmt;
}

function compactFor(series: SeriesSpec): boolean {
  return /cot|_net$|_oi$|cot_index_mm/.test(series.col);
}

function toKpi(chart: ChartSpec, series: SeriesSpec, groupId: string): Kpi {
  const key = `${series.csv}:${series.col}`;
  const override = OVERRIDES[key] ?? {};
  const compact = compactFor(series);
  return {
    title: series.name,
    fmt: fmtFor(chart, series),
    digits: compact ? 0 : series.yoyMonths || fmtFor(chart, series) === "pct" ? 1 : undefined,
    compact,
    hint: chart.title,
    ...series,
    ...override,
    nav: `${groupId}/${chart.id}`,
  };
}

function KpiSection({ label, items, onNav }: { label: string; items: Kpi[]; onNav: (p: string) => void }) {
  return (
    <section className="space-y-2">
      <div className="text-[11px] tracking-widest text-muted-foreground/60 num uppercase">{label}</div>
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6 gap-3">
        {items.map((k, i) => (
          <div key={`${k.nav}:${k.csv}:${k.col}:${i}`} style={{ animationDelay: `${(i % 12) * 35}ms` }} className="rise h-full">
            <KpiCard spec={k} onClick={() => onNav(k.nav)} />
          </div>
        ))}
      </div>
    </section>
  );
}

export function Overview({ onNav }: { onNav: (path: string) => void }) {
  return (
    <div className="max-w-[1800px] space-y-6">
      {GROUPS.map((group) => (
        <KpiSection
          key={group.id}
          label={group.title}
          items={group.charts.flatMap((chart) => chart.series.map((series) => toKpi(chart, series, group.id)))}
          onNav={onNav}
        />
      ))}
    </div>
  );
}
