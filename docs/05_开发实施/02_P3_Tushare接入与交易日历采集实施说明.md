# P3 Tushare接入与交易日历采集实施说明

> 日期：2026-07-27  
> 版本：0.2.0  
> 状态：真实环境闭环验证通过

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
0003_trade_cal_runtime
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

## 6. 验证结果

代码级验证：

- Python语法编译检查通过；
- Alembic迁移链通过；
- 迁移版本号长度回归测试已增加；
- Worker登记字段回归测试已增加。

2026-07-27在`svr3`真实开发环境完成闭环验证：

```text
CapabilityProbe = available
trade_calendar RAW = 208条
最早日期 = 2026-01-01
最晚日期 = 2026-07-27
CollectTask = SUCCEEDED
```

因此以下链路已有真实证据：

```text
Tushare
→ Worker
→ RawBatch
→ raw.tushare_trade_cal
→ Task成功
```

## 7. 已处理的真实环境缺陷

真实部署验证发现并修复：

1. Alembic revision ID超过默认32字符；
2. WorkerRegistry Python属性名与数据库`metadata`列映射使用错误。

两项均已增加回归测试。

## 8. 下一步

继续实现：

```text
stock_basic
stock_daily
Scheduler自动增量
```
