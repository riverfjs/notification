/** 图表声明式规格:registry 里每张图一个 ChartSpec,ChartCard 负责渲染。 */

export interface SeriesSpec {
  /** 数据文件,相对 data/(不带 .csv),如 "macro/rates" 或 "tickers/VIX" */
  csv: string;
  col: string;
  name: string;
  /** 0=左轴(默认) 1=右轴 */
  axis?: 0 | 1;
  /** 同比变换:按日历回看 N 个月(月频列用 12;对缺测月鲁棒) */
  yoyMonths?: number;
  /** 数值乘数(单位换算) */
  scale?: number;
  /** 阶梯线(政策利率类) */
  step?: boolean;
  /** 面积填充 */
  area?: boolean;
  /** 图例默认关闭 */
  off?: boolean;
  color?: string;
  /** 第二段数据源:展示层拼接(如 putcall 2019-10 切换) */
  append?: { csv: string; col: string; cut: string };
}

export interface AxisSpec {
  /** 轴名(单位) */
  name?: string;
  /** 'pct' 加 % 后缀 */
  fmt?: "pct" | "num";
  min?: number | "dataMin";
  max?: number;
}

export interface ChartSpec {
  id: string;
  title: string;
  subtitle?: string;
  series: SeriesSpec[];
  y0?: AxisSpec;
  y1?: AxisSpec;
  /** 水平参考线(画在左轴),如 PMI 50、宽度 15/85 */
  hLines?: { value: number; label?: string }[];
  /** 垂直日期参考线,如口径切换点 */
  vLines?: { date: string; label?: string }[];
  /** 卡片底部脚注(caveat) */
  note?: string;
  /** 默认展示窗口(年数,undefined=全部) */
  defaultYears?: number;
}

export interface GroupSpec {
  id: string;
  title: string;
  charts: ChartSpec[];
}
