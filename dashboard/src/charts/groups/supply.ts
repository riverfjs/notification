import type { GroupSpec } from "../types";

/** 地产・供给 */
export const supply: GroupSpec = {
  id: "supply",
  title: "地产・供给",
  charts: [
    {
      id: "housing-supply",
      title: "建房许可、新开工与库存",
      subtitle: "供给端先行:许可领先开工,库存月数预警过剩",
      series: [
        { csv: "macro/housing_supply", col: "building_permits_k", name: "建房许可(千套)" },
        { csv: "macro/housing_supply", col: "housing_starts_k", name: "新开工(千套)" },
        { csv: "macro/housing_supply", col: "months_supply_new", name: "新房库存月数", axis: 1 },
      ],
      y0: { name: "千套(年化)" },
      y1: { name: "月" },
      defaultYears: 10,
    },
    {
      id: "mfg-orders",
      title: "制造业订单与采购",
      subtitle: "ISM PMI(50 荣枯)与耐用品订单同比",
      series: [
        { csv: "macro/ism_pmi", col: "ism_pmi", name: "ISM 制造业 PMI" },
        { csv: "macro/mfg_orders_pmi", col: "durable_goods_orders", name: "耐用品订单 YoY", axis: 1, yoyMonths: 12 },
        { csv: "macro/mfg_orders_pmi", col: "philly_fed_mfg", name: "费城联储指数(0 荣枯)", axis: 1, off: true },
        { csv: "macro/mfg_orders_pmi", col: "ny_fed_mfg", name: "纽约联储指数(0 荣枯)", axis: 1, off: true },
      ],
      y0: { name: "PMI" },
      y1: { name: "YoY% / 指数" },
      hLines: [{ value: 50, label: "荣枯 50" }],
      note: "ISM 为混合 vintage(1948-2016 修订值/2017+ 当期值,±0.5 典型差);右轴混排订单同比(%)与联储扩散指数(荣枯=0),按图例区分。",
      defaultYears: 10,
    },
    {
      id: "wei",
      title: "每周经济指数 WEI",
      subtitle: "纽约联储 WEI —— GDP 的周频代理",
      series: [{ csv: "macro/wei", col: "weekly_economic_index", name: "WEI", area: true }],
      y0: { name: "指数" },
      hLines: [{ value: 0 }],
      defaultYears: 10,
    },
    {
      id: "us-gdp-trade",
      title: "美国 GDP 与贸易差额",
      subtitle: "BEA 实际 GDP 环比折年率 vs Census/BEA 商品服务贸易差额",
      series: [
        { csv: "macro/us_growth_releases", col: "real_gdp_qoq_saar", name: "实际 GDP QoQ SAAR" },
        { csv: "macro/us_trade_orders", col: "trade_balance_goods_services", name: "贸易差额($B)", axis: 1, scale: 0.001 },
      ],
      y0: { name: "GDP QoQ SAAR", fmt: "pct" },
      y1: { name: "$B" },
      hLines: [{ value: 0 }],
      defaultYears: 10,
    },
    {
      id: "durable-ex-transport",
      title: "耐用品订单(剔除运输)",
      subtitle: "Census ADVM3:新订单金额与月环比",
      series: [
        { csv: "macro/us_trade_orders", col: "durable_ex_transport_orders", name: "新订单($B)", scale: 0.001 },
        { csv: "macro/us_trade_orders", col: "durable_ex_transport_orders_mom", name: "MoM", axis: 1 },
      ],
      y0: { name: "$B" },
      y1: { name: "MoM", fmt: "pct" },
      hLines: [{ value: 0 }],
      defaultYears: 10,
    },
  ],
};
