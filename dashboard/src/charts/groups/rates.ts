import type { GroupSpec } from "../types";

/** 利率・信用(2 图) */
export const rates: GroupSpec = {
  id: "rates",
  title: "利率・信用",
  charts: [
    {
      id: "rates-policy",
      title: "市场利率与政策利率",
      subtitle: "国债收益率曲线 vs 联邦基金利率;10Y−2Y 倒挂 = 衰退前瞻",
      series: [
        { csv: "macro/rates", col: "ust_10y", name: "10Y" },
        { csv: "macro/rates", col: "ust_2y", name: "2Y" },
        { csv: "macro/rates", col: "ust_3m", name: "3M", off: true },
        { csv: "macro/rates", col: "fed_funds_eff", name: "联邦基金利率", step: true },
        { csv: "macro/rates", col: "curve_10y_2y", name: "10Y−2Y 利差", area: true },
        { csv: "macro/rates", col: "curve_10y_3m", name: "10Y−3M 利差", off: true },
      ],
      y0: { name: "%", fmt: "pct" },
      hLines: [{ value: 0, label: "倒挂线" }],
      defaultYears: 10,
    },
    {
      id: "credit",
      title: "信用利差",
      subtitle: "HY OAS / Baa 利差走阔 = 风险偏好恶化;对照 VIX",
      series: [
        { csv: "macro/credit_spread", col: "hy_oas_full", name: "高收益债 OAS" },
        { csv: "macro/credit_spread", col: "baa_10y_spread", name: "Baa−10Y 利差" },
        { csv: "tickers/VIX", col: "c", name: "VIX", axis: 1 },  // yfinance 当日收盘(FRED VIXCLS T+1 滞后)
        { csv: "macro/credit_spread", col: "hy_stress", name: "HYG/TLT 回撤(压力)", axis: 1, off: true },
      ],
      y0: { name: "利差", fmt: "pct" },
      y1: { name: "VIX" },
      note: "HY OAS:1996+ 全史(官方快照镜像 ⊕ 官方 API,重叠段逐位核对);>6% 历史上对应信用承压区。",
      defaultYears: 10,
    },
  ],
};
