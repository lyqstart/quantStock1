# P3 Tushare接入与交易日历采集实施说明

> 日期：2026-07-27  
> 版本：0.2.0  
> 状态：代码已实现，等待真实Token与PostgreSQL环境验证

## 1. 本批实现范围

已实现：

- Tushare SDK统一Adapter；
- Token仅从`QUANTSTOCK1_TUSHARE_TOKEN`读取；
- Provider错误标准化；
- trade_cal接口级CapabilityProbe；
- 单进程统一RateLimiter；
- trade_calendar按自然年切片；
- BACKFILL / INITIALIZE任务入队；
- Worker领取Slice；
- CollectRun / SliceAttempt / RawBatch执行事实；
- `raw.tushare_trade_cal`幂等写入；
- Task完成后推进`ops.data_watermark`；
- Worker容器入口；
- 开发命令行入口。

## 2. 当前官方能力基线

当前Tushare官方文档确认：

- `trade_cal`需要2000积分；
- 当前2000积分以上账户总体频次为200次/分钟、每API每天100000次；
- Python SDK支持通过`ts.pro_api(token)`直接初始化，不要求把Token保存到本地配置文件。

官方资料：

- https://tushare.pro/document/2?doc_id=26
- https://tushare.pro/document/1?doc_id=290
- https://tushare.pro/document/1?doc_id=131

## 3. 本批数据库变更

新增迁移：

```text
0003_tushare_trade_calendar_runtime
```

主要变更：

- 修正Tushare凭据引用为`env:QUANTSTOCK1_TUSHARE_TOKEN`；
- `trade_calendar`登记2000积分、200次/分钟、100000次/日；
- RAW交易日历增加内容Hash唯一约束；
- Watermark的`frequency`改为非空，避免PostgreSQL中NULL导致唯一约束失效。

## 4. 开发命令入口

接口能力探测：

```bash
python -m app.cli probe --binding tushare:trade_calendar
```

创建交易日历采集任务：

```bash
python -m app.cli enqueue-trade-calendar --start 2026-01-01 --end 2026-12-31 --exchange SSE --run-type BACKFILL
```

Worker执行一个Slice：

```bash
python -m app.collect.worker --once
```

持续Worker：

```bash
python -m app.collect.worker
```

## 5. Docker边界

`worker`放在Compose的`collect` profile中。

因此普通：

```bash
docker compose -f compose.dev.yml up -d db api
```

不会因为尚未配置Tushare Token让Worker反复重启。

配置Token后再启动：

```bash
docker compose -f compose.dev.yml --profile collect up -d --build
```

## 6. 本地验证结果

当前代码已完成：

- Python语法编译检查；
- 15个单元测试全部通过；
- Alembic迁移链可以生成PostgreSQL SQL；
- 迁移中的JSONB配置SQL已专项检查。

## 7. 尚未验证的事实

当前开发环境没有用户真实Tushare Token，也没有连接用户实际PostgreSQL实例。

因此以下不能宣称已经验证：

- 当前Token对`trade_cal`的真实调用；
- 真实RAW入库；
- 真实Worker执行；
- 真实Watermark推进；
- Docker环境中的完整闭环。

这些必须在用户环境执行后形成测试证据。

## 8. 下一步

本批合入后，下一步先在实际环境验证：

```text
CapabilityProbe
→ 创建trade_calendar任务
→ Worker执行
→ RAW入库
→ Task成功
→ Watermark推进
```

验证通过后再实现：

```text
stock_basic
stock_daily
Scheduler自动增量
```
