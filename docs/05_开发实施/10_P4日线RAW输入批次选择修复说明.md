# P4 日线 RAW 输入批次选择修复说明

## 问题

P3 RAW 使用内容哈希幂等。重复采集相同日线时，接口可能返回 5526 条，但由于内容已存在，数据库实际不会再次插入这 5526 条 RAW 行。

因此 `raw.raw_batch.row_count` 表达来源响应行数，不能证明该 RawBatch 实际拥有物理 RAW 行。

P4-1 之前使用 `row_count > 0` 选择最新清洗来源，可能选中“响应非空、实际物理 RAW 为 0”的重复采集批次，导致 CLEAN 出现 `0/0`。

## 修复

`enqueue-clean-latest` 不再依据 `RawBatch.row_count` 判断可清洗输入。

现在必须确认：

```text
CollectTask
→ CollectRun
→ RawBatch
→ 对应 DataItem 的 RAW 物理表
```

至少存在一条实际 RAW 行，才允许作为 CLEAN 来源任务。

P4-1 三个 DataItem 分别检查：

```text
trade_calendar → raw.tushare_trade_cal
stock_basic    → raw.tushare_stock_basic
stock_daily    → raw.tushare_daily
```

重复采集没有产生新 RAW 行时，CLEAN 会回退选择最近一个真正持有物理 RAW 数据的成功采集任务。

## 版本

```text
app_version = 0.7.3
Alembic = 0010_p4_skip_audit
```

本修复不需要数据库迁移。
