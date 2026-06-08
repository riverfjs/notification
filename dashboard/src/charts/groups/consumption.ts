import type { GroupSpec } from "../types";

/** 消费・就业 */
export const consumption: GroupSpec = {
  id: "consumption",
  title: "消费・就业",
  charts: [
    {
      id: "jobs",
      title: "失业与就业",
      subtitle: "失业率 vs 初请失业金(衰退的最快先行指标)",
      series: [
        { csv: "macro/jobs_monthly", col: "unemployment_rate_pct", name: "失业率" },
        { csv: "macro/claims_weekly", col: "initial_claims_weekly", name: "初请失业金(千人/周)", axis: 1, scale: 0.001 },
        { csv: "macro/jobs_monthly", col: "nonfarm_payrolls_change_k", name: "非农变化(千人)", axis: 1 },
      ],
      y0: { name: "失业率", fmt: "pct" },
      y1: { name: "千人" },
      defaultYears: 10,
    },
    {
      id: "personal-finance",
      title: "个人财务状况",
      subtitle: "储蓄率与实际可支配收入同比 —— 消费余力",
      series: [
        { csv: "macro/personal_finance", col: "personal_saving_rate_pct", name: "个人储蓄率" },
        { csv: "macro/personal_finance", col: "real_disposable_income", name: "实际可支配收入 YoY", axis: 1, yoyMonths: 12 },
        { csv: "macro/personal_finance", col: "personal_income", name: "个人收入 YoY", axis: 1, yoyMonths: 12, off: true },
      ],
      y0: { name: "储蓄率", fmt: "pct" },
      y1: { name: "YoY", fmt: "pct" },
      defaultYears: 10,
    },
    {
      id: "home-sales",
      title: "房屋销售与房价",
      subtitle: "新房/成屋销售(千套年化)与 Case-Shiller 房价同比",
      series: [
        { csv: "macro/home_sales_prices", col: "new_home_sales_k", name: "新房销售" },
        { csv: "macro/home_sales_prices", col: "existing_home_sales_k", name: "成屋销售" },
        { csv: "macro/home_sales_prices", col: "case_shiller_natl", name: "Case-Shiller YoY", axis: 1, yoyMonths: 12 },
      ],
      y0: { name: "千套(年化)" },
      y1: { name: "YoY", fmt: "pct" },
      note: "成屋销售 2013 起(FRED 被 NAR 限滚动窗,历史靠镜像,偏差 ≤1%)。",
      defaultYears: 10,
    },
    {
      id: "vehicle-sales",
      title: "汽车销售",
      subtitle: "百万辆・年化 —— 大件消费意愿",
      series: [
        { csv: "macro/vehicle_sales", col: "total_vehicle_sales_m", name: "总销量" },
        { csv: "macro/vehicle_sales", col: "light_trucks_m", name: "轻卡/SUV" },
        { csv: "macro/vehicle_sales", col: "autos_m", name: "乘用车" },
        { csv: "macro/vehicle_sales", col: "light_vehicle_sales_m", name: "轻型车合计", off: true },
      ],
      y0: { name: "百万辆" },
      defaultYears: 10,
    },
    {
      id: "retail",
      title: "零售",
      subtitle: "零售与餐饮销售同比 —— 消费动能",
      series: [
        { csv: "macro/retail", col: "retail_food_services", name: "零售+餐饮 YoY", yoyMonths: 12 },
        { csv: "macro/retail", col: "retail_ex_autos", name: "除汽车 YoY", yoyMonths: 12 },
        { csv: "macro/retail", col: "retail_food_services", name: "零售+餐饮($B)", axis: 1, scale: 0.001, off: true },
      ],
      y0: { name: "YoY", fmt: "pct" },
      y1: { name: "$B" },
      hLines: [{ value: 0 }],
      defaultYears: 10,
    },
    {
      id: "michigan-sentiment",
      title: "密歇根消费者信心",
      subtitle: "UMich 官方消费者信心、现况、预期与通胀预期",
      series: [
        { csv: "macro/michigan_sentiment", col: "sentiment", name: "消费者信心" },
        { csv: "macro/michigan_sentiment", col: "current_conditions", name: "当前状况" },
        { csv: "macro/michigan_sentiment", col: "expectations", name: "消费者预期" },
        { csv: "macro/michigan_sentiment", col: "inflation_1y", name: "1年通胀预期", axis: 1, off: true },
        { csv: "macro/michigan_sentiment", col: "inflation_5y", name: "5年通胀预期", axis: 1, off: true },
      ],
      y0: { name: "指数" },
      y1: { name: "通胀预期", fmt: "pct" },
      note: "UMich 主站公开 CSV 提供最新发布与近月数据;FRED 的 UMCSENT 延迟,不作为本数据源。",
      defaultYears: 3,
    },
  ],
};
