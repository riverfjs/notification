import { KpiCard, type KpiSpec } from "../components/KpiCard";
import { ChartCard } from "../components/ChartCard";
import type { ChartSpec } from "../charts/types";

type Kpi = KpiSpec & { nav: string };

/** 市场温度:情绪/波动/宽度/信用 —— 点击直达对应图表并高亮 */
const MARKET: Kpi[] = [
  { title: "CNN Fear & Greed", csv: "macro/fng", col: "fng", digits: 0, goodWhen: "high", hint: "≤25 恐慌 / ≥75 贪婪", nav: "sentiment/fng" },
  { title: "VIX", csv: "tickers/VIX", col: "c", goodWhen: "low", hint: ">30 高波动", nav: "rates/credit" },
  { title: "标普500 > MA200 占比", csv: "macro/breadth_official", col: "pct_above_ma200", fmt: "pct", digits: 1, goodWhen: "high", hint: "≤15 washout / ≥85 过热", nav: "breadth/sp500-breadth" },
  { title: "股票 Put/Call", csv: "macro/putcall_cboe", col: "equity_pc", goodWhen: "low", hint: ">1 恐慌 / <0.5 自满", nav: "sentiment/putcall" },
  { title: "高收益债 OAS", csv: "macro/credit_spread", col: "hy_oas_full", fmt: "pct", goodWhen: "low", hint: ">6% 信用承压", nav: "rates/credit" },
  { title: "期限利差 10Y−2Y", csv: "macro/rates", col: "curve_10y_2y", fmt: "pct", goodWhen: "high", hint: "<0 倒挂", nav: "rates/rates-policy" },
];

/** 宏观速览:就业/制造/仓位/商品比价 */
const MACRO: Kpi[] = [
  { title: "失业率", csv: "macro/jobs_monthly", col: "unemployment_rate_pct", fmt: "pct", digits: 1, goodWhen: "low", nav: "consumption/jobs" },
  { title: "初请失业金", csv: "macro/claims_weekly", col: "initial_claims_weekly", scale: 0.001, digits: 0, goodWhen: "low", hint: "千人/周", nav: "consumption/jobs" },
  { title: "ISM 制造业 PMI", csv: "macro/ism_pmi", col: "ism_pmi", digits: 1, goodWhen: "high", hint: "50 荣枯线", nav: "supply/mfg-orders" },
  { title: "NAAIM 经理人仓位", csv: "macro/naaim", col: "naaim_mean", digits: 0, hint: "0-200%,≤20 防御 / ≥90 拥挤", nav: "sentiment/naaim" },
  { title: "AAII 多空差", csv: "macro/aaii", col: "bull_bear_spread", digits: 1, goodWhen: "high", hint: "百分点,≤−20 极端看空", nav: "sentiment/aaii" },
  { title: "铜金比(日)", csv: "macro/copper_gold_ppi", col: "copper_gold_ratio_daily", digits: 2, goodWhen: "high", hint: "升=再通胀 risk-on", nav: "inflation/copper-gold" },
];

const FOCUS: ChartSpec[] = [
  {
    id: "ov-fng",
    title: "CNN Fear & Greed",
    subtitle: "恐惧贪婪指数(0-100)· 官方 API",
    series: [{ csv: "macro/fng", col: "fng", name: "F&G" }],
    y0: { min: 0, max: 100 },
    hLines: [
      { value: 25, label: "恐慌 25" },
      { value: 75, label: "贪婪 75" },
    ],
    note: "API 2020-09~2021-01 回填段为占位脏值,2021-02 起为有效值。",
    defaultYears: 3,
  },
  {
    id: "ov-breadth",
    title: "标普500 市场宽度(官方)",
    subtitle: "成分股收于 200 日均线上方的占比 $S5TH",
    series: [
      { csv: "macro/breadth_official", col: "pct_above_ma200", name: ">MA200" },
      { csv: "macro/breadth_official", col: "pct_above_ma50", name: ">MA50", off: true },
    ],
    y0: { fmt: "pct", min: 0, max: 100 },
    hLines: [
      { value: 15, label: "washout 15" },
      { value: 85, label: "过热 85" },
    ],
    defaultYears: 3,
  },
];

function KpiRow({ label, items, onNav }: { label: string; items: Kpi[]; onNav: (p: string) => void }) {
  return (
    <div>
      <div className="text-[11px] tracking-widest text-muted-foreground/60 mb-2 num uppercase">{label}</div>
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        {items.map((k, i) => (
          <div key={k.title} style={{ animationDelay: `${i * 50}ms` }} className="rise h-full">
            <KpiCard spec={k} onClick={() => onNav(k.nav)} />
          </div>
        ))}
      </div>
    </div>
  );
}

export function Overview({ onNav }: { onNav: (path: string) => void }) {
  return (
    <div className="max-w-[1800px] space-y-5">
      <KpiRow label="市场温度" items={MARKET} onNav={onNav} />
      <KpiRow label="宏观速览" items={MACRO} onNav={onNav} />
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {FOCUS.map((c) => (
          <div key={c.id} className="h-[440px]">
            <ChartCard spec={c} />
          </div>
        ))}
      </div>
    </div>
  );
}
