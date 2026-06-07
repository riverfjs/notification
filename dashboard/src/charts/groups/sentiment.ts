import type { GroupSpec } from "../types";

/** 市场情绪(6 图,含 F&G) */
export const sentiment: GroupSpec = {
  id: "sentiment",
  title: "市场情绪",
  charts: [
    {
      id: "fng",
      title: "CNN Fear & Greed 与分量",
      subtitle: "主指数(0-100)+ 可切换七分量原始值",
      series: [
        { csv: "macro/fng", col: "fng", name: "F&G 指数" },
        { csv: "macro/fng", col: "vix", name: "VIX", axis: 1, off: true },
        { csv: "macro/fng", col: "putcall_5d", name: "P/C 5日均", axis: 1, off: true },
        { csv: "macro/fng", col: "junk_spread", name: "垃圾债利差", axis: 1, off: true },
        { csv: "macro/fng", col: "strength_52w", name: "52周强度", axis: 1, off: true },
        { csv: "macro/fng", col: "safehaven_diff", name: "避险需求差", axis: 1, off: true },
      ],
      y0: { min: 0, max: 100 },
      y1: { name: "分量" },
      hLines: [
        { value: 25, label: "恐慌 25" },
        { value: 75, label: "贪婪 75" },
      ],
      note: "官方 API 2020-09~2021-01 回填段为占位脏值,2021-02 起为有效值;七分量为各自原始量纲,值域差异大。",
      defaultYears: 3,
    },
    {
      id: "aaii",
      title: "个人投资者调查 AAII",
      subtitle: "散户多空差(Bull−Bear)—— 极端值反指",
      series: [
        { csv: "macro/aaii", col: "bull_bear_spread", name: "多空差", area: true },
        { csv: "macro/aaii", col: "bullish", name: "看多 %", off: true },
        { csv: "macro/aaii", col: "bearish", name: "看空 %", off: true },
      ],
      y0: { name: "百分点" },
      hLines: [
        { value: 0 },
        { value: -20, label: "极端 −20" },
      ],
      note: "AAII 官方周度调查,1987+,单位为百分点(看多% − 看空%);低于 −20 为极端看空区(全史仅 8% 的周触及,2009-03 大底 = −51)。",
      defaultYears: 10,
    },
    {
      id: "naaim",
      title: "投资经理人调查 NAAIM",
      subtitle: "主动管理人平均股票仓位(0-200%)",
      series: [
        { csv: "macro/naaim", col: "naaim_mean", name: "平均仓位" },
        { csv: "macro/naaim", col: "most_bearish", name: "最空者仓位", off: true },
        { csv: "macro/naaim", col: "most_bullish", name: "最多者仓位", off: true },
      ],
      y0: { name: "仓位 %" },
      hLines: [
        { value: 20, label: "极度防御 20" },
        { value: 90, label: "拥挤 90" },
      ],
      defaultYears: 10,
    },
    {
      id: "putcall",
      title: "期权市场交易方向 Put/Call",
      subtitle: "CBOE 全市场聚合,2006-11 至今(两代统计系统拼接)",
      series: [
        {
          csv: "macro/putcall", col: "equity_pc", name: "股票 P/C",
          append: { csv: "macro/putcall_cboe", col: "equity_pc", cut: "2019-10-07" },
        },
        {
          csv: "macro/putcall", col: "total_pc", name: "总 P/C", off: true,
          append: { csv: "macro/putcall_cboe", col: "total_pc", cut: "2019-10-07" },
        },
        { csv: "macro/putcall_cboe", col: "index_pc", name: "指数 P/C(对冲盘)", off: true },
      ],
      y0: { name: "Put/Call" },
      hLines: [{ value: 1, label: "1.0" }],
      vLines: [
        { date: "2012-06-11", label: "口径断点" },
        { date: "2019-10-07", label: "统计系统切换" },
      ],
      note: "股票 P/C >1 = 恐慌尖峰(反向看多),<0.5 = 自满;两段无重叠不可证同基,跨 2019-10 比较只看形态。",
      defaultYears: 10,
    },
    {
      id: "cot-sp500",
      title: "标普500 COT 指数",
      subtitle: "期货持仓:非商业净 − 商业净(传统口径,1986+)",
      series: [
        { csv: "macro/cot_legacy", col: "sp500_emini_cot_index_mm", name: "E-mini(1997+)" },
        { csv: "macro/cot_legacy", col: "sp500_big_cot_index_mm", name: "大合约(1986-2021)", off: true },
        { csv: "macro/cot_sp500", col: "lev_money_cot_index", name: "对冲基金 COT 指数(0-100)", axis: 1, off: true },
      ],
      y0: { name: "净合约数差" },
      y1: { name: "0-100", min: 0, max: 100 },
      hLines: [{ value: 0 }],
      note: "周频(CFTC 周二仓位,周五发布);右轴为 TFF 口径 Williams 指数,与左轴口径不同。",
      defaultYears: 10,
    },
    {
      id: "cot-ndx",
      title: "纳指100 COT 指数",
      subtitle: "期货持仓:非商业净 − 商业净(传统口径)",
      series: [
        { csv: "macro/cot_legacy", col: "ndx_mini_cot_index_mm", name: "E-mini" },
        { csv: "macro/cot_legacy", col: "ndx_big_cot_index_mm", name: "大合约", off: true },
        { csv: "macro/cot_nasdaq100", col: "lev_money_cot_index", name: "对冲基金 COT 指数(0-100)", axis: 1, off: true },
      ],
      y0: { name: "净合约数差" },
      y1: { name: "0-100", min: 0, max: 100 },
      hLines: [{ value: 0 }],
      defaultYears: 10,
    },
  ],
};
