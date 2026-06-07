# pcr/ — 单标的期权 Put/Call 查询工具(Longbridge CLI)

输入美股 ticker → 输出该标的期权链的 Put/Call 数据。
与 `feeds/putcall_cboe.py`(CBOE 全市场聚合,对标 MacroMicro 图)互补:这里是**单标的**口径。

```bash
uv run pcr/pcr.py NVDA                # 实时快照 + 近10日 + 252日分位判读
uv run pcr/pcr.py SPY QQQ AAPL        # 多标的
uv run pcr/pcr.py NVDA --days 30      # 多显示历史
uv run pcr/pcr.py NVDA --csv          # 累积保存 pcr/data/NVDA.csv
```

输出字段:实时 call/put 量与 P/C;日频 `pc_vol`(成交量比)、`pc_oi`(未平仓比)、
call/put 量、总 OI;最新值的近 252 日分位 + 反向判读。

要点:
- 数据源 `longbridge option volume [daily]`(美股 only,需 `longbridge auth login`)。
- 源历史为 **~420 个交易日滚动窗**(实测最早 2024-09-30);`--csv` 做累积合并,越攒越长。
- 单标的 P/C 水平因对冲结构差异大(SPY≈1±,个股普遍低),**只与自身历史比分位**,
  勿跨标的、勿与 CBOE 聚合口径比绝对值。
- 判读是反向逻辑:高分位=避险极端(恐慌区确认器,配合左侧分批);低分位=自满(只停止追高,不作卖出信号)。
