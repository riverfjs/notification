import { GROUPS } from "../charts/groups";
import type { AxisSpec, ChartSpec, SeriesSpec } from "../charts/types";
import { KpiCard, type KpiSpec } from "../components/KpiCard";

type Kpi = KpiSpec & { nav: string };
type KpiKey = `${string}:${string}`;

const OVERRIDES: Record<string, Partial<KpiSpec>> = {
  "macro/fng:fng": { title: "CNN Fear & Greed", digits: 0, goodWhen: "high", hint: "≤25 恐慌 / ≥75 贪婪" },
  "tickers/VIX:c": { title: "VIX", goodWhen: "low", hint: ">30 高波动" },
  "macro/breadth_official:pct_above_ma200": { title: "标普500 > MA200", digits: 1, goodWhen: "high", hint: "≤15 washout / ≥85 过热" },
  "macro/putcall_cboe:equity_pc": { title: "股票 Put/Call", goodWhen: "low", hint: ">1 恐慌 / <0.5 自满" },
  "macro/credit_spread:hy_oas_full": { title: "高收益债 OAS", fmt: "pct", goodWhen: "low", hint: ">6% 信用承压" },
  "macro/credit_spread:baa_10y_spread": { title: "Baa 利差", fmt: "pct", digits: 2, goodWhen: "low" },
  "macro/credit_spread:hy_stress": { title: "HY 压力", digits: 2, goodWhen: "low" },
  "macro/rates:curve_10y_2y": { title: "10Y−2Y 期限利差", fmt: "pct", goodWhen: "high", hint: "<0 倒挂" },
  "macro/jobs_monthly:unemployment_rate_pct": { title: "失业率", fmt: "pct", digits: 1, goodWhen: "low" },
  "macro/jobs_monthly:nonfarm_payrolls_k": { title: "非农就业", digits: 0, hint: "千人" },
  "macro/claims_weekly:initial_claims_weekly": { title: "初请失业金", scale: 0.001, digits: 0, goodWhen: "low", hint: "千人/周" },
  "macro/ism_pmi:ism_pmi": { title: "ISM 制造业 PMI", digits: 1, goodWhen: "high", hint: "50 荣枯线" },
  "macro/naaim:naaim_mean": { title: "NAAIM 平均仓位", digits: 0, hint: "≤20 防御 / ≥90 拥挤" },
  "macro/aaii:bull_bear_spread": { title: "AAII 多空差", digits: 1, goodWhen: "high", hint: "百分点,≤−20 极端看空" },
  "macro/copper_gold_ppi:copper_gold_ratio_daily": { title: "铜金比(日)", digits: 2, goodWhen: "high", hint: "升=再通胀 risk-on" },
  "macro/us_inflation_releases:cpi_headline_mom": { title: "CPI MoM", fmt: "pct", digits: 1 },
  "macro/us_inflation_releases:cpi_core_mom": { title: "核心 CPI MoM", fmt: "pct", digits: 1 },
  "macro/us_inflation_releases:cpi_headline_yoy": { title: "CPI YoY", fmt: "pct", digits: 1 },
  "macro/us_inflation_releases:cpi_core_yoy": { title: "核心 CPI YoY", fmt: "pct", digits: 1 },
  "macro/us_inflation_releases:pce_yoy": { title: "PCE YoY", fmt: "pct", digits: 1 },
  "macro/us_inflation_releases:core_pce_yoy": { title: "核心 PCE YoY", fmt: "pct", digits: 1 },
  "macro/us_growth_releases:real_gdp_qoq_saar": { title: "实际 GDP QoQ", fmt: "pct", digits: 1 },
  "macro/us_trade_orders:trade_balance_goods_services": { title: "贸易差额", scale: 0.001, digits: 1, hint: "$B" },
  "macro/us_trade_orders:durable_ex_transport_orders": { title: "耐用品订单(剔除运输)", scale: 0.001, digits: 1, hint: "$B" },
  "macro/us_trade_orders:durable_ex_transport_orders_mom": { title: "耐用品订单 MoM", fmt: "pct", digits: 1 },
  "macro/michigan_sentiment:sentiment": { title: "UMich 消费者信心", digits: 1, goodWhen: "high" },
  "macro/michigan_sentiment:inflation_1y": { title: "UMich 1年通胀预期", fmt: "pct", digits: 1 },
  "macro/michigan_sentiment:inflation_5y": { title: "UMich 5年通胀预期", fmt: "pct", digits: 1 },
  "macro/inflation_monetary:breakeven_5y": { title: "5Y 盈亏平衡", fmt: "pct", digits: 2 },
  "macro/inflation_monetary:fed_funds_target": { title: "联储目标利率", fmt: "pct", digits: 2 },
  "macro/wei:weekly_economic_index": { title: "WEI", digits: 2, goodWhen: "high" },
  "macro/retail:retail_food_services": { title: "零售 YoY", fmt: "pct", digits: 1, goodWhen: "high" },
  "macro/home_sales_prices:existing_home_sales_k": { title: "成屋销售", digits: 0, hint: "千套年化" },
  "macro/cot_legacy:sp500_emini_cot_index_mm": { title: "标普 E-mini COT", compact: true, digits: 0 },
  "macro/sector_strength:XLK_rs_line": { title: "科技相对 SPY", digits: 2, goodWhen: "high" },
  "macro/breadth_official:pct_above_ma50": { title: "标普500 > MA50", digits: 1, fmt: "pct", goodWhen: "high" },
  "macro/breadth_official:pct_above_ma20": { title: "标普500 > MA20", digits: 1, fmt: "pct", goodWhen: "high" },
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
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-3">
        {items.map((k, i) => (
          <div key={`${k.nav}:${k.csv}:${k.col}:${i}`} style={{ animationDelay: `${(i % 12) * 35}ms` }} className="rise h-full">
            <KpiCard spec={k} onClick={() => onNav(k.nav)} />
          </div>
        ))}
      </div>
    </section>
  );
}

const CORE_KEYS: KpiKey[] = [
  "macro/fng:fng",
  "tickers/VIX:c",
  "macro/breadth_official:pct_above_ma200",
  "macro/naaim:naaim_mean",
  "macro/rates:curve_10y_2y",
  "macro/credit_spread:hy_oas_full",
  "macro/us_inflation_releases:core_pce_yoy",
  "macro/us_growth_releases:real_gdp_qoq_saar",
  "macro/ism_pmi:ism_pmi",
  "macro/jobs_monthly:unemployment_rate_pct",
];

const OVERVIEW_SECTIONS: { label: string; keys: KpiKey[] }[] = [
  {
    label: "市场风险",
    keys: [
      "macro/putcall_cboe:equity_pc",
      "macro/credit_spread:baa_10y_spread",
      "macro/credit_spread:hy_stress",
    ],
  },
  {
    label: "通胀政策",
    keys: [
      "macro/us_inflation_releases:cpi_headline_yoy",
      "macro/us_inflation_releases:cpi_core_yoy",
      "macro/us_inflation_releases:pce_yoy",
      "macro/inflation_monetary:breakeven_5y",
      "macro/inflation_monetary:fed_funds_target",
    ],
  },
  {
    label: "增长就业",
    keys: [
      "macro/jobs_monthly:nonfarm_payrolls_k",
      "macro/claims_weekly:initial_claims_weekly",
      "macro/wei:weekly_economic_index",
      "macro/us_trade_orders:trade_balance_goods_services",
    ],
  },
  {
    label: "消费地产",
    keys: [
      "macro/retail:retail_food_services",
      "macro/michigan_sentiment:sentiment",
      "macro/michigan_sentiment:inflation_1y",
      "macro/home_sales_prices:existing_home_sales_k",
      "macro/us_trade_orders:durable_ex_transport_orders_mom",
    ],
  },
  {
    label: "广度仓位",
    keys: [
      "macro/breadth_official:pct_above_ma20",
      "macro/breadth_official:pct_above_ma50",
      "macro/aaii:bull_bear_spread",
      "macro/cot_legacy:sp500_emini_cot_index_mm",
      "macro/sector_strength:XLK_rs_line",
    ],
  },
];

function allKpis(): Map<KpiKey, Kpi> {
  const items = GROUPS.flatMap((group) =>
    group.charts.flatMap((chart) => chart.series.map((series) => toKpi(chart, series, group.id)))
  );
  return new Map(items.map((item) => [`${item.csv}:${item.col}` as KpiKey, item]));
}

function pick(map: Map<KpiKey, Kpi>, keys: KpiKey[]): Kpi[] {
  return keys.map((key) => map.get(key)).filter((item): item is Kpi => Boolean(item));
}

export function Overview({ onNav }: { onNav: (path: string) => void }) {
  const map = allKpis();
  const core = pick(map, CORE_KEYS);
  return (
    <div className="max-w-[1800px] space-y-6">
      <section className="space-y-2">
        <div className="text-[11px] tracking-widest text-muted-foreground/60 num uppercase">核心状态</div>
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
          {core.map((k, i) => (
            <div key={`${k.nav}:${k.csv}:${k.col}`} style={{ animationDelay: `${i * 35}ms` }} className="rise h-full">
              <KpiCard spec={k} onClick={() => onNav(k.nav)} />
            </div>
          ))}
        </div>
      </section>

      {OVERVIEW_SECTIONS.map((section) => (
        <KpiSection
          key={section.label}
          label={section.label}
          items={pick(map, section.keys)}
          onNav={onNav}
        />
      ))}
    </div>
  );
}
