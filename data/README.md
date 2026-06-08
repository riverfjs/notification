# data 目录约定

- `macro/`: 仪表盘直接消费的宏观与衍生指标 CSV,由 `feeds/*.py` 通过 `save()` 输出。
- `tickers/`: yfinance 口径的标准 OHLCV 缓存,表头固定为 `date,o,h,l,c,v`,由 `feeds/prices.py` 刷新。
- `spot/`: 非 yfinance OHLCV 的现货日频价格,目前是 `XAUUSD.csv` 与 `COPPER.csv`,表头为 `date,c`。
- `cache/`: feed 内部中间缓存,不直接作为图表数据源;`cache/sp500/` 存 S&P500 成分与个股价格面板。
- `legacy/`: 旧研究遗留数据,当前 feed 管线不维护。

前端 `csv` 配置使用相对 `data/` 的无后缀路径,例如 `macro/rates`、`tickers/VIX`。
