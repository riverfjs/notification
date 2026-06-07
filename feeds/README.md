# feeds/ — 宏观 & 市场情绪数据层(30 个模块,每日自动更新)

每个脚本独立负责一类数据:从官方免费源抓**全历史**,落成一个同名 CSV
(`../data/macro/<脚本名>.csv`;基础价格缓存在 `../data/`)。全部幂等 —— 重复跑、
断了重跑都安全,每次运行把整条序列刷新到最新。覆盖**就业消费、地产供给、通胀
利率、信用、情绪、宽度板块**六大类,作为仪表盘 / 择时信号 / 回测的统一数据底座。

## 跑法
```bash
uv run feeds/run_all.py        # 全部 30 个,按依赖排序(prices/spot_gold/spot_copper 在前)
uv run feeds/rates.py          # 任意单个
```
- **云端为主**:`.github/workflows/feeds.yml` UTC 周二~六 02:30(= 美东周一~五晚 21:30/22:30,等 CBOE/FRED 当日发布完毕)自动跑并把
  更新的 CSV 提交回仓库;push 改动 `feeds/**` 代码(`.md` 除外)也会触发一轮验证。
  任一模块失败任务标红(`run_all.py` 非零退出),成功模块的数据照常提交。
  本地只 `git pull`,不要再开本地 cron(会互相产生提交冲突)。
- **FRED key**(FRED 类 14 个模块必需):免费注册 `fredaccount.stlouisfed.org/apikeys`。
  本地放 `feeds/.fred_api_key`(已 gitignore)或环境变量 `FRED_API_KEY`;GitHub 上配
  repo secret `FRED_API_KEY`。纯官方 API(api.stlouisfed.org),无回退逻辑。

## 模块一览(脚本名 = 输出 CSV 名)

### 基础层(3)— 价格缓存,供下游模块读取
| 脚本 | 产出 | 内容 |
|---|---|---|
| prices | data/ 下 30 个 ticker 的日线 OHLCV | SPY/QQQ/DIA/IWM、11 个 GICS 行业 ETF、VIX/VXO、GLD/TLT/HYG 等(yfinance 复权价);带防回退守门:新数据为空/倒退/缩水则保留旧文件 |
| spot_gold | data/XAUUSD.csv(date,c) | 现货金 $/盎司:LBMA PM 定盘,1968+,PM 缺日用 AM 补(站点前置 Imunify360 对数据中心 IP **间歇拦截**:curl_cffi 仿 Chrome + 5 次退避;彻底失败则保留全量历史软跳过、下次自愈) |
| spot_copper | data/COPPER.csv(date,c) | 铜 $/公吨:LME 现汇结算 2008+(Westmetall 免费档)⊕ HG=F×2204.62 补 2000-2007 |

### 宏观基本面(14,FRED 官方 API)
| 脚本 | 列 | 这是什么 | 历史 |
|---|---|---|---|
| jobs_monthly | nonfarm_payrolls_k, unemployment_rate_pct | 非农就业(千人)与失业率 | 1948 月 |
| claims_weekly | initial_claims_weekly | 初请失业金 —— 最快的就业转折先行指标 | 1967 周 |
| personal_finance | personal_income, real_disposable_income, personal_saving_rate_pct | 收入 / 实际可支配收入 / 储蓄率,消费余力 | 1959 月 |
| home_sales_prices | new_home_sales_k, existing_home_sales_k, case_shiller_natl | 新房/成屋销售(千套年化)+ Case-Shiller 全国房价指数 | 1963(成屋 2013)月 |
| vehicle_sales | total_vehicle_sales_m, light_vehicle_sales_m, autos_m, light_trucks_m | 汽车销售(百万辆年化),大件消费意愿 | 1976 月 |
| retail | retail_food_services, retail_ex_autos | 零售总额 / 除汽车零售,消费动能 | 1992 月 |
| housing_supply | building_permits_k, housing_starts_k, months_supply_new | 建房许可 / 新开工 / 新房库存月数,地产供给周期 | 1959 月 |
| mfg_orders_pmi | durable_goods_orders, mfg_new_orders_total, philly_fed_mfg, ny_fed_mfg | 耐用品与制造业新订单($)+ 费城/纽约联储制造业指数(荣枯线=0) | 1968 月 |
| wei | weekly_economic_index | 纽约联储周度经济指数,GDP 的周频代理 | 2008 周 |
| copper_gold_ppi | copper_usd_mt, ppi_all_commod, copper_gold_ratio(月)+ copper_fut_usd_mt, copper_gold_ratio_daily(日) | **铜金比**(吨铜值多少盎司金):升=再通胀/risk-on,降=避险;对照 PPI | 月 1992 / 日 2000 |
| oil_gold_cpi | wti_usd_bbl, cpi_all_urban, gold_usd_oz, oil_gold_ratio | **油金比**(桶油值多少盎司金)与 CPI,能源通胀温度计 | 1986 日(比率) |
| inflation_monetary | breakeven_5y, breakeven_10y, fwd_5y5y_infl, fed_funds_target | 盈亏平衡通胀预期 + 5y5y 远期 + 联储目标利率(DFEDTAR⊕DFEDTARU 拼接单列) | 1982 日(预期 2003) |
| rates | ust_3m, ust_2y, ust_10y, fed_funds_eff, curve_10y_2y, curve_10y_3m | 国债收益率 / 有效联邦基金利率 / 期限利差(倒挂→衰退前瞻) | 1954 日 |
| credit_spread | baa_10y_spread, aaa_10y_spread, vix, baa_aaa_quality, hy_oas_full, hyg_tlt_ratio, hy_stress | 信用利差全家桶:Baa/Aaa−10Y(1983+)、真 HY OAS(1996+,Wayback 镜像⊕官方 API 逐位核对)、hy_stress=HYG/TLT 比值 252d 回撤(2007+);走阔=风险偏好恶化 | 1983 日 |

### 市场情绪(9)
| 脚本 | 列 | 这是什么 | 历史 |
|---|---|---|---|
| ism_pmi | ism_pmi | ISM 制造业 PMI,50 荣枯线(Wayback+DBnomics+MQL5 拼接) | **1948** 月 |
| naaim | naaim_mean, most_bullish, most_bearish | 主动型基金经理平均仓位(0-200%),极端高=拥挤(官方 xlsx) | 2006 周 |
| cot_sp500 / cot_nasdaq100 | open_interest + lev_money/asset_mgr/dealer 各自 \_net 与 \_cot_index | 标普500 / 纳指100 期货持仓结构(CFTC TFF):对冲基金、机构资金、做市商净持仓 + 0-100 Williams COT 指数 | 2006 周 |
| cot_legacy | sp500_big_\* / sp500_emini_\* / ndx_big_\* / ndx_mini_\*(oi, noncomm_net, comm_net, cot_index_mm) | 传统口径 COT(CFTC Legacy):cot_index_mm = 非商业净−商业净,历史最长 | **1986** 周 |
| aaii | bullish, neutral, bearish, bull_bear_spread | 散户情绪调查(AAII 官方),极端看空历来是反指 | **1987** 周 |
| putcall | equity_pc, index_pc, total_pc(+ \*_archive 列) | CBOE 全市场期权 put/call **历史档**(官方归档,冻结于 2019-10;2012-06-11 有口径断点,archive 列独立不拼接) | 2003-2019 日 |
| putcall_cboe | total_pc, index_pc, etp_pc, equity_pc, call_volume, put_volume | put/call **续作**(CBOE 每日统计页 `?dt=` 历史查询,累积缓存断点续传):equity>1≈恐慌、<0.5≈自满 | 2019-10+ 日 |
| fng | fng, fng_rating + 7 分量原始值(momentum_spx/_ma125, strength_52w, breadth_mcclellan, putcall_5d, vix/_ma50, junk_spread, safehaven_diff) | CNN Fear & Greed 主指数(0-100)与全部七分量(CNN dataviz 官方 API,新值覆盖式累积缓存,可全量自愈) | 2020-09 日(**信号从 2021-02**) |

### 市场宽度 & 板块(4)
| 脚本 | 列 | 这是什么 | 历史 |
|---|---|---|---|
| breadth | breadth20/50/200, regime_bull | 11 个 GICS 行业 ETF 在 MA 上方比例:>50=牛市机制;粒度粗但历史深 | 1999 日 |
| breadth_official | pct_above_ma20/50/200 | **官方个股宽度** $S5TW/$S5FI/$S5TH(标普500 成分股在 MA 上方百分比,Barchart 免费 EOD,无幸存者偏差):**≤15 washout / ≥85 过热**阈值可直接用 | **2006-12** 日 |
| breadth_stocks | pct_above_ma20/50/200, n_ma\*, n_members | 自算个股宽度(时点成分 + 不复权收盘),与官方线交叉验证(近 30 日偏差 −0.04pp) | 2000 日 |
| sector_strength | {XLB..XLY}_rs63 + {XLB..XLY}_rs_line | 11 行业 vs SPY:63 日超额收益(>0=跑赢)+ 累计相对强度线(ETF 上市首日重基 1.0) | 1999 日 |

## 使用注意(全部对抗验证过)
- **宽度极值阈值(≤15/≥85)只用 breadth_official**(2008-11-20=2.02%、2020-03-23=2.97%,washout 含义成立);breadth_stocks 是交叉验证用(残余:326 只退市票无免费价格,深历史略偏负);行业级 breadth 只用 >50 牛熊线。
- **铜金比日频腿**(copper_gold_ratio_daily)用 LME 现汇结算,T+1 滞后一个交易日;纯 COMEX HG=F 自 2024 关税后有 +3.5~5% 溢价,故弃用;月频 IMF 列保留(滞后 1-2 月)。
- **COT 两套口径并存**:cot_sp500/cot_nasdaq100 = TFF 分类 + Williams 0-100(结构分析用);cot_legacy = 传统「非商业净−商业净」且回溯 1986。底层净持仓均与 CFTC 官方逐位一致。
- **credit_spread**:hy_oas_full 镜像段冻结于 2025-11,每次跑与官方 API 重叠段逐位核对,不一致自动降级 API-only。
- **ism_pmi 混合 vintage**(1948-2016 修订值 / 2017+ 当期值,±0.5 典型差)——画图/研究够用,逐点回测发布意外不行。
- **成屋销售**(existing_home_sales_k):FRED 被 NAR 限制为滚动 13 个月窗口,全历史靠 `feeds/ehs_archive.csv` 镜像(2013+,API 窗口自动回写续期);历史段偏差有界(mean 0.82%/max 2.81%)。
- **putcall + putcall_cboe = 连续的 CBOE 聚合口径**,但两段分属 CBOE 新老统计系统、无重叠段可证同基 —— 拼长图在 2019-10 标注「统计系统切换」。**单标的** put/call 查询是独立工具 `pcr/`(仓库根目录),不在本管线内。
- **fng**:CNN API 自己的 2020-09~2021-01 回填段很脏(成段 50.0 占位 + 异常值)——画图无妨,做信号从 2021-02 起算。
- **冻结序列**(日志里日期永不前进,属正常):VXO ..2021-09-23(CBOE 停止发布;它是覆盖 1987 股灾的唯一免费波动率序列,1990 后用 VIX)、putcall ..2019-10(由 putcall_cboe 续)。
- prices 全量覆写(复权基准随分红回移,不能增量追加);盘中跑会含当日半根 K,收盘后跑最稳。

依赖:`pandas numpy openpyxl xlrd yfinance lxml curl_cffi`(uv 脚本头各自声明,`uv run` 自动装);取数以 stdlib urllib 为主,**spot_gold 例外用 curl_cffi(Chrome TLS 指纹)** —— LBMA 站点前置 Imunify360 对数据中心 IP 间歇拦截(同代码时而 200 时而 415/质询页),故指纹 + 退避重试,彻底失败软跳过保留历史。外部站点:api.stlouisfed.org、publicreporting.cftc.gov、naaim.org、aaii.com、cdn/www.cboe.com、web.archive.org、westmetall.com、barchart.com、LBMA、production.dataviz.cnn.io。
