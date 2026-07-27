# Tushare采集详细设计

> 路线图阶段：P3 数据源与采集平台  
> 项目：A股量化研究与信号决策平台（quantStock1）  
> 文档性质：详细设计——Tushare采集引擎  
> 日期：2026-07-27  
> 状态：已确认

---

# 1. 设计目标

本文件定义 quantStock1 如何稳定、可恢复、可追溯地采集 Tushare 数据。

目标不是为每个接口写一套独立程序，而是建立：

```text
统一采集引擎
+
少量标准采集策略
+
DataItem / SourceBinding配置
```

最终新增大多数 Tushare 接口时，只需要增加：

```text
目录配置
SourceBinding
字段映射
采集策略参数
质量规则
```

不修改采集框架主体。

---

# 2. 已确认的账户条件

当前账户：

```text
2120积分
+
A股历史分钟独立权限
+
集合竞价独立权限
```

Token基础有效性已经历史实际验证。

运行时仍必须进行接口级能力探测，因为：

```text
Token有效
≠
全部接口可用
```

---

# 3. 官方限制基线

当前官方文档已经确认的典型限制包括：

## stock_basic

```text
2000积分
每次最多6000行
每分钟50次
```

## daily

```text
每次最多6000行
基础积分每分钟500次
交易日15:00～16:00之间入库
官方建议按交易日期循环提取全市场
```

## daily_basic

```text
2000积分
每次最多6000行
交易日15:00～17:00之间更新
```

## stk_limit

```text
2000积分
每次最多5800行
交易日约08:40更新当日数据
```

## 历史分钟

当前已购买独立权限。

按已确认权限资料：

```text
每次最多8000行
通过股票代码 + 时间窗口循环
支持1/5/15/30/60分钟
```

具体接口能力以运行时 SourceBinding + CapabilityProbe 为最终依据。

---

# 4. 采集架构

```text
Scheduler / Manual Request
        ↓
Task Planner
        ↓
CollectTask
        ↓
Worker
        ↓
Collect Engine
        ↓
SourceBinding
        ↓
TushareAdapter
        ↓
RateLimiter
        ↓
Tushare API
        ↓
RawBatch
        ↓
RAW
```

采集程序只负责：

```text
可靠地获得来源数据
```

不负责：

- 业务清洗；
- 策略判断；
- 数据质量最终放行；
- Feature计算。

---

# 5. 核心对象

## 5.1 CollectTask

表示“应该完成的采集目标”。

例如：

```text
stock_daily
2026-07-24
全市场
```

或者：

```text
stock_minute
000001.SZ
1m
2020-01-01 ～ 2020-06-30
```

---

## 5.2 CollectRun

表示一次真实执行。

一个 CollectTask 可以因为：

- 重试；
- 续跑；
- 人工重跑；

产生多个 Run。

---

## 5.3 RequestSlice

CollectTask 必须拆成一个或多个：

```text
RequestSlice
```

它是实际向 Tushare 发起一次请求的最小工作单元。

例如：

```text
daily / 20260724
```

或者：

```text
stk_mins / 000001.SZ / 1m /
20260101 09:00:00 ～ 20260131 23:59:59
```

---

# 6. RequestSlice 必要字段

至少：

```text
slice_id
collect_task_id
collect_run_id
source_binding_id
partition_key
request_params
request_hash
expected_range
status
attempt_count
response_rows
started_at
finished_at
error_type
next_retry_at
```

---

# 7. 采集策略分类

所有 Tushare DataItem 优先归入以下标准策略：

```text
S1 静态/低频全量
S2 全市场按交易日
S3 单股票按时间窗口
S4 财务按股票/报告期
S5 事件按公告/事件时间
S6 指数/行业按对象或交易日
S7 分钟按股票+频率+时间窗口
S8 遗留/特殊接口自定义策略
```

只有无法落入前七类的接口才允许自定义策略。

---

# 8. S1：静态/低频全量策略

适用：

```text
stock_basic
stock_company
index_basic
行业分类
部分基础映射
```

特点：

- 数据量较小；
- 更新频率低；
- 适合定期整体刷新；
- 必须保留历史状态变化。

---

# 9. stock_basic 特殊处理

不能只请求默认：

```text
list_status = L
```

否则只有当前上市股票。

为了形成历史证券主数据，初始化时至少考虑：

```text
L 上市
D 退市
P 暂停上市
G 未交易
```

不同状态分别获取后合并。

这样历史研究不会因为退市股票缺失产生：

```text
幸存者偏差
```

---

# 10. S1更新方式

初始化：

```text
全状态/全范围拉取
↓
RAW
↓
比较变化
```

日常：

```text
低频定时刷新
+
新股发行/状态事件补充
```

不需要每分钟刷新基础资料。

---

# 11. S2：全市场按交易日策略

适用典型接口：

```text
daily
daily_basic
adj_factor
stk_limit
moneyflow
margin_detail
部分市场统计
```

基本模式：

```text
trade_date
↓
一次或若干次请求
↓
获得当日全市场
```

---

# 12. 为什么优先按交易日

对于全市场日级数据：

```text
按交易日
```

比：

```text
按股票循环多年历史
```

更适合日常增量。

优势：

- 当天新增任务数量少；
- 容易判断完整性；
- 容易补某一天；
- 容易和交易日历对账；
- 失败范围明确。

Tushare `daily` 官方也明确建议按日期循环提取全市场。

---

# 13. 按交易日仍必须防止6000行截断

当前 A 股数量已经接近部分接口：

```text
6000行
5800行
```

的单次返回上限。

因此不能假设：

```text
trade_date请求一定永远完整
```

规则：

```text
response_rows < max_rows
→ 正常进入下一检查

response_rows == max_rows
→ 标记 possible_truncation
→ 自动执行二次拆分
```

---

# 14. S2二次拆分

如果单日全市场命中上限：

优先根据该接口支持的参数拆分，例如：

```text
股票代码集合
市场
交易所
其他合法维度
```

若接口没有可用市场参数，则由平台证券主数据生成股票代码分组：

```text
Group A
Group B
...
```

分别请求。

最终合并时按业务唯一键去重。

---

# 15. 全市场任务完整性判断

日级任务不能只判断：

```text
API返回成功
```

还应结合：

```text
交易日历
当日有效证券集合
停牌规则
接口自身覆盖范围
历史统计
```

判断是否存在明显缺口。

例如 `daily`：

```text
停牌股票本来就没有记录
```

因此不能简单要求：

```text
daily行数 == stock_basic全部上市股票数
```

完整性由数据质量层做正式判定。

---

# 16. S3：单股票按时间窗口

适用：

```text
某些股票历史接口
部分事件接口
部分股东接口
```

模式：

```text
ts_code
+
start_date
+
end_date
```

由 Planner 自动生成多个时间窗口。

---

# 17. 时间窗口不能写死

不同接口：

```text
max_rows_per_request
```

不同。

不同股票历史记录密度也不同。

因此系统采用：

```text
初始窗口
+
返回行数判断
+
自适应拆分
```

而不是为所有接口写死：

```text
每次365天
```

---

# 18. 自适应窗口算法

基本逻辑：

```text
请求窗口
↓
rows < soft_limit
    → 接受
rows >= soft_limit
    → 缩小窗口
rows == hard_limit
    → 必须拆分
```

其中：

```text
hard_limit = 官方单次最大行数
soft_limit < hard_limit
```

soft_limit 用于提前避免频繁触顶。

具体比例作为 SourceBinding 配置，不在代码中固定。

---

# 19. S4：财务按股票/报告期策略

适用：

```text
income
balancesheet
cashflow
fina_indicator
fina_mainbz
```

当前2120积分下，部分财务接口更适合：

```text
单股票历史
```

采集。

不能照搬5000积分VIP的：

```text
按报告期一次拉全市场
```

能力。

---

# 20. 财务初始化方式

初始历史采集：

```text
证券主数据
↓
逐股票建立财务采集任务
↓
按接口允许的历史范围请求
↓
命中上限则继续拆分
```

并行度受到：

```text
接口频率
服务器负载
数据库写入
```

共同限制。

---

# 21. 财务日常增量

财务数据不是：

```text
每天给每只股票重拉全部历史
```

建议：

```text
按公告窗口扫描
+
对近期可能修订的报告期回看
+
必要时单股票补采
```

具体回看窗口进入每个接口的 SourceBinding / UpdatePolicy。

---

# 22. 财务数据必须允许修订

新财报接口返回旧报告期新版本时：

```text
不能覆盖旧RAW事实
```

采集层必须允许：

```text
同报告期
+
不同公告/修订版本
```

进入RAW。

最终版本语义由清洗和标准化层处理。

---

# 23. S5：事件型策略

适用：

```text
repurchase
share_float
stk_holdertrade
pledge_detail
block_trade
top_list
dividend
```

事件数据优先按：

```text
公告日期
事件日期
交易日
```

做增量扫描。

---

# 24. 事件采集不能只靠最大ID

外部接口不保证提供平台可长期依赖的连续自增ID。

因此不能用：

```text
last_id + 1
```

作为统一增量方案。

使用：

```text
时间窗口
+
业务唯一键
+
内容Hash
```

实现幂等增量。

---

# 25. 事件回看窗口

事件数据可能：

- 延迟发布；
- 修正；
- 更新状态。

因此每日增量可以配置：

```text
lookback_days
```

例如：

```text
今天任务
不仅请求今天
还回看最近N天
```

N属于接口级配置。

不在框架里写死一个统一数字。

---

# 26. S6：指数/行业策略

指数、行业数据分：

```text
基础定义
成员关系
行情
权重
```

分别处理。

---

# 27. 指数基础

```text
index_basic
```

属于S1低频全量。

---

# 28. 指数行情

```text
index_daily
index_weekly
index_monthly
index_dailybasic
```

使用：

```text
按交易日
或
按指数+时间范围
```

具体由接口返回上限和实际数量决定。

日常优先按交易日。

---

# 29. 指数成分与权重

```text
index_weight
index_member_all
```

必须保存：

```text
生效时间
失效时间
权重时间
```

不能只保留当前成员。

采集任务必须支持历史回补。

---

# 30. S7：分钟策略

分钟是第一阶段数据量最大的特殊采集模式。

正式键：

```text
ts_code
+
frequency
+
trade_time
```

---

# 31. 分钟初始化维度

历史分钟任务：

```text
股票
×
频率
×
时间窗口
```

生成RequestSlice。

例如：

```text
000001.SZ
1m
2024-01-01 ～ 2024-01-31
```

---

# 32. 分钟单次8000行约束

1分钟完整交易日约：

```text
240条/股票
```

理论上：

```text
8000 / 240 ≈ 33个交易日
```

所以1分钟不能用很大的时间窗口。

设计不依赖固定“33天”。

采用：

```text
初始窗口
+
自适应拆分
```

保证未来接口变化或特殊数据不会截断。

---

# 33. 分钟初始窗口建议

第一版实现可采用保守初始值：

```text
1m：约20个交易日
5m：更大窗口
15m：更大窗口
30m：更大窗口
60m：更大窗口
```

最终窗口不按自然日固定，而应结合：

```text
trade_calendar
```

生成交易日范围。

---

# 34. 分钟窗口动态调整

同一股票连续多个窗口：

```text
远低于soft_limit
```

可以适当扩大后续窗口。

连续接近上限：

```text
缩小
```

目的：

```text
减少请求次数
+
保证不截断
```

第一版也允许只实现“触顶继续二分”，不必一开始做复杂预测算法。

---

# 35. 分钟end_date语义

分钟接口时间参数必须使用：

```text
完整datetime
```

不能用含糊的：

```text
2026-07-24
```

作为结束边界后假设包含全天。

所有分钟窗口统一明确：

```text
start_datetime
end_datetime
```

并在接口适配层处理Tushare具体边界语义。

---

# 36. 分钟频率策略

平台保留采集：

```text
1m
5m
15m
30m
60m
```

的能力。

但首次正式历史初始化优先：

```text
1m
```

之后对样本做：

```text
1m内部聚合
vs
Tushare高周期分钟
```

一致性验证。

验证通过后，不默认重复下载全部高周期历史。

---

# 37. 分钟股票范围

历史分钟只对：

```text
目标日期当时有效的A股证券
```

进行规划。

不能用：

```text
今天的上市股票清单
```

简单向历史回推。

必须考虑：

```text
list_date
delist_date
证券状态
```

避免大量无意义请求。

---

# 38. 首次全量初始化总体流程

```text
DataItem启用
↓
CapabilityProbe
↓
读取历史范围
↓
读取证券主数据/交易日历
↓
生成CollectTask
↓
Planner生成RequestSlice
↓
Worker采集
↓
RawBatch
↓
完整性检查
↓
Checkpoint
↓
下一Slice
```

---

# 39. 首次全量不追求一次跑完

历史初始化必须：

```text
可暂停
可继续
可分批
可限速
```

不能设计成：

```text
一个Python进程跑几天
中途失败全部重来
```

---

# 40. 历史初始化批次

建议按：

```text
DataItem
+
历史阶段
```

形成批次。

例如：

```text
stock_daily / 1990-2005
stock_daily / 2006-2015
stock_daily / 2016-current
```

具体边界由Planner生成，不要求人工固定年代。

---

# 41. 日常增量总体流程

```text
Scheduler
↓
判断DataItem到更新时间
↓
创建Incremental CollectTask
↓
Planner生成Slice
↓
Worker执行
↓
RAW
↓
成功/失败记录
↓
进入清洗任务
```

---

# 42. 日常任务必须由UpdatePolicy驱动

不能所有接口统一：

```text
每天15:30
```

因为不同接口更新时间不同。

例如当前官方：

```text
daily：15:00～16:00
daily_basic：15:00～17:00
stk_limit：约08:40
margin_detail：约次日08:30
```

所以：

```text
DataItem
+
SourceBinding
+
UpdatePolicy
```

决定调度时机。

---

# 43. 交易日判断

交易相关DataItem创建任务前必须读取：

```text
trade_calendar
```

非交易日不创建无意义的普通交易日任务。

---

# 44. trade_calendar优先级

交易日历属于采集平台的基础依赖。

系统启动或年度切换时优先确保：

```text
过去完整
+
未来足够范围
```

的交易日历已经存在。

其他调度不能长期依赖硬编码节假日表。

---

# 45. 日常任务依赖

典型依赖：

```text
trade_calendar
↓
stock_daily
↓
adj_factor / daily_basic
↓
后续Clean/Quality
```

但采集层不要求完全串行。

不同接口在数据可用时可以独立执行。

正式“数据是否可用”由下游DataItem状态判断。

---

# 46. 补采 Backfill

用户可以指定：

```text
DataItem
对象范围
时间范围
```

创建：

```text
run_type = backfill
```

的任务。

补采不能伪装成普通日常任务。

---

# 47. 自动缺口补采

Quality发现：

```text
DataGap
```

后可以创建：

```text
Repair CollectTask
```

链路：

```text
DataGap
↓
Repair Task
↓
CollectRun
↓
RAW
↓
重新质量检查
↓
Gap关闭
```

---

# 48. 手工重跑

用户可以对失败或可疑任务：

```text
retry
rerun
```

但每次必须产生新的执行事实。

旧失败Run不能被覆盖成成功。

---

# 49. Checkpoint

长任务必须保存：

```text
最后成功Slice
未完成Slice
已完成范围
失败范围
```

Checkpoint存数据库。

不能只存在内存或本地临时文件。

---

# 50. Slice状态

统一：

```text
pending
running
succeeded
failed
retry_wait
split_required
cancelled
```

---

# 51. 任务领取

Worker从PostgreSQL领取任务。

必须使用数据库原子并发控制，保证：

```text
同一个Slice
不会被两个Worker同时正式执行
```

第一阶段不依赖Celery。

---

# 52. Lease机制

Worker领取Slice后记录：

```text
worker_id
leased_at
lease_expires_at
heartbeat_at
```

Worker异常退出：

```text
lease过期
↓
Slice重新可领取
```

---

# 53. 幂等键

CollectTask建议使用可计算幂等键：

```text
data_item
source_binding
run_type
object_scope
time_scope
frequency
```

避免Scheduler重复创建同一个日常目标。

---

# 54. Request Hash

每次真实外部请求保存：

```text
request_hash
```

基于：

- api_name；
- 规范化参数；
- 字段版本；

生成。

用于发现重复请求和审计。

---

# 55. RAW写入顺序

推荐：

```text
获得API响应
↓
基础结构校验
↓
建立RawBatch
↓
批量写RAW
↓
提交事务
↓
更新Slice成功
```

不能：

```text
先标记任务成功
再慢慢写数据
```

---

# 56. API成功不等于采集成功

以下情况即使HTTP/SDK没有异常，也不能判成功：

- 返回达到单次上限；
- Schema变化；
- 业务主键缺失；
- 请求范围与返回范围明显不匹配；
- 必需字段全部为空；
- 返回数据不属于请求对象；
- 写RAW失败。

---

# 57. 空结果处理

空结果分三类：

```text
EXPECTED_EMPTY
SUSPICIOUS_EMPTY
UNKNOWN_EMPTY
```

例如：

```text
退市股票在上市前请求
```

可以是EXPECTED_EMPTY。

而：

```text
正常交易日全市场daily返回0
```

是SUSPICIOUS_EMPTY。

不能统一把空结果当成功。

---

# 58. RateLimiter

统一限流器按：

```text
source
api_name
当前账户权限
```

控制。

SourceBinding保存：

```text
documented_limit
effective_limit
```

---

# 59. documented_limit 与 effective_limit

```text
documented_limit
```

是当前已知官方/实测上限。

```text
effective_limit
```

是系统实际使用上限。

要求：

```text
effective_limit <= documented_limit
```

为重试、人工操作和规则变化留安全余量。

---

# 60. 限流实现要求

第一阶段不需要复杂分布式限流。

因为：

```text
同一svr3
+
单Worker优先
```

可以通过数据库/进程级统一RateLimiter完成。

以后多Worker时再升级全局限流实现。

---

# 61. 429 / 频控错误

收到明确频控错误：

```text
RATE_LIMITED
```

处理：

```text
暂停该Binding请求
↓
退避
↓
更新运行时有效速率
↓
重试
```

不能立即高速重试。

---

# 62. Retry分类

## 自动重试

```text
NETWORK_ERROR
TIMEOUT
RATE_LIMITED
临时PROVIDER_ERROR
```

## 不自动无限重试

```text
AUTH_ERROR
PERMISSION_DENIED
INVALID_REQUEST
SCHEMA_CHANGED
```

---

# 63. Retry必须有上限

每个Slice：

```text
max_attempts
```

达到上限：

```text
failed
```

等待：

```text
人工处理
或
后续Repair
```

不能永久占用Worker。

---

# 64. Schema变化

Adapter接收到字段结构与：

```text
schema_fingerprint
```

明显不一致时：

```text
停止该Binding向正式RAW继续推进
↓
标记SCHEMA_CHANGED
↓
等待字段映射确认
```

避免悄悄错位。

---

# 65. 历史范围

每个 SourceBinding 必须配置或探测：

```text
history_start
```

Planner不能对明显不存在数据的时期产生海量请求。

---

# 66. 证券生命周期裁剪

股票相关历史任务范围：

```text
max(request_start, list_date)
～
min(request_end, delist_date/current)
```

减少无效调用。

---

# 67. 交易日裁剪

日行情和分钟行情：

```text
只在有效交易日
```

规划时间范围。

分钟窗口仍使用连续datetime传给API，但内部预估行数使用交易日历。

---

# 68. 采集优先级

统一：

```text
P0 日常关键增量
P1 失败修复/缺口补采
P2 第一阶段初始化
P3 普通历史扩展
P4 遗留数据验证/大规模迁移辅助
```

历史全量不能拖慢当天关键增量。

---

# 69. 服务器资源限制

svr3同时承担：

- 开发；
- 测试；
- 正式；
- 旧quantStock；
- 其他服务。

所以采集并发不能只看Tushare调用频率。

还要限制：

```text
CPU
内存
数据库写入
磁盘IO
```

第一版从低并发开始。

---

# 70. 并发策略

第一阶段优先：

```text
单Worker进程
+
有限任务并发
```

不要为了追求接口500次/分钟理论上限强行开启大量并发。

实测以后再调高。

---

# 71. 批量写入

外部返回DataFrame后：

```text
不要逐行INSERT
```

应采用批量写入。

具体技术可以根据表类型选择：

- PostgreSQL COPY；
- 批量INSERT；
- SQLAlchemy Core批量；
- 其他经过测试的批量方法。

P4存储设计阶段最终确定。

---

# 72. 事务边界

建议以：

```text
RequestSlice / RawBatch
```

作为可控制事务边界。

避免一个数小时历史任务使用一个巨大事务。

---

# 73. RAW与采集日志分离

数据正文：

```text
raw.*
```

运行事实：

```text
ops.*
```

不能把完整API数据JSON全部塞进任务日志表。

---

# 74. 采集审计

每个Run最终至少统计：

```text
slice_total
slice_succeeded
slice_failed
request_total
rows_total
retry_total
rate_limit_count
started_at
finished_at
duration
```

---

# 75. DataItem新鲜度

每个DataItem维护：

```text
latest_expected_business_time
latest_collected_business_time
latest_clean_business_time
```

这样系统能够回答：

```text
数据是否已经更新到应该到的位置
```

---

# 76. 运行完成条件

CollectTask只有满足：

```text
所有必要Slice成功
+
没有未处理split_required
+
没有未知截断
+
RawBatch事务成功
```

才能：

```text
succeeded
```

部分成功：

```text
partial
```

不能强行写成成功。

---

# 77. 初始化完成条件

一个DataItem历史初始化完成不能只看：

```text
任务都运行过
```

还必须确认：

```text
目标历史范围
↓
没有未解释Gap
↓
没有未解决possible_truncation
↓
没有失败Slice
```

---

# 78. 数据采集状态与CLEAN状态分离

例如：

```text
采集成功
```

但：

```text
质量检查失败
```

此时：

```text
RAW存在
CLEAN不可用
```

系统不能显示：

```text
DataItem完全正常
```

必须分别展示采集和可用状态。

---

# 79. 第一批实现顺序

第一批顺序：

```text
1. trade_calendar
2. stock_basic
3. stock_daily
4. stock_adj_factor
5. stock_daily_basic
6. stock_suspend
7. stock_limit_price
```

随后验证特殊模式：

```text
8. stock_minute 1m样本
9. financial_income样本
10. financial_indicator样本
```

---

# 80. 为什么trade_calendar先做

后续：

- 日常任务；
- 历史窗口；
- 分钟行数预估；
- 是否交易日；

全部依赖交易日历。

所以它属于采集平台基础设施数据。

---

# 81. 为什么先做daily而不是分钟全量

daily：

- 体量小；
- 官方支持按交易日全市场；
- 容易验证完整性；
- 能快速验证整个任务闭环。

先跑通：

```text
Task
↓
Slice
↓
Adapter
↓
RateLimiter
↓
RAW
↓
Checkpoint
```

再进入数亿行分钟数据。

---

# 82. 为什么分钟只先做样本

旧quantStock已经证明分钟数据会快速形成大容量。

新项目必须先验证：

- 分片；
- 写入；
- 索引；
- 压缩；
- 去重；
- 时间语义；

再决定全历史迁移/重新采集。

---

# 83. 财务样本验证目标

使用少量股票验证：

```text
报告期
公告时间
修订版本
历史回看
```

确保不会把：

```text
后来修订数据
```

直接覆盖历史版本。

---

# 84. 运行期接口能力基线

正式启用接口前：

```text
CapabilityProbe
↓
保存last_probe_result
↓
确认available
```

接口长期连续权限错误：

```text
暂停Binding
```

不能让Scheduler每天制造大量必失败任务。

---

# 85. 官方规则变化

官方文档、积分和接口规则可能变化。

因此：

```text
接口限制
不是代码常量
```

运行时以：

```text
SourceBinding配置
+
CapabilityProbe
```

维护。

---

# 86. Tushare新增字段

例如官方 `daily` 已出现后续新增字段。

新字段处理：

```text
发现Schema变化
↓
评估字段含义
↓
更新FieldMappingVersion
↓
测试
↓
启用
```

不因新字段出现就让旧历史批次失去解释。

---

# 87. 删除字段/语义变化

如果官方删除字段或改变语义：

```text
旧FieldMappingVersion保留
+
新版本单独建立
```

不能直接修改历史映射定义。

---

# 88. 采集框架不得写策略逻辑

禁止采集层出现：

```text
PE小于20才保存
涨停股票特殊进入策略池
某行业才采集
```

这些属于后续研究逻辑。

采集层只按DataItem范围采数据。

---

# 89. 采集范围配置

允许通过DataItem配置限定：

```text
A股范围
交易所
上市状态
历史起点
```

但这些是：

```text
平台数据资产范围
```

不是策略筛选条件。

---

# 90. 测试要求

实现后至少测试：

## 单元测试

- Slice生成；
- 自适应拆分；
- 幂等键；
- 重试分类；
- 交易日裁剪；
- 上市生命周期裁剪。

## 集成测试

- Tushare最小真实调用；
- 限频；
- 空结果；
- 触顶拆分；
- RAW批量写入；
- Worker重启恢复。

## 故障测试

- 网络中断；
- Worker kill；
- 数据库短暂不可用；
- 权限错误；
- Schema变化模拟。

---

# 91. P3采集平台验收场景

### 场景1：首次初始化daily

指定历史范围后能够：

```text
自动生成交易日Slice
↓
持续采集
↓
中断恢复
↓
完成全部范围
```

### 场景2：日常daily

当天数据到达后：

```text
自动采集
↓
RAW
↓
状态成功
```

### 场景3：触顶

模拟或真实出现：

```text
rows == max_rows
```

系统自动拆分，不误判完整。

### 场景4：分钟

1m样本跨多个窗口：

```text
自动切片
↓
中断
↓
恢复
↓
无重复/无缺口
```

### 场景5：财务修订

同一报告期后续出现新版本：

```text
旧RAW保留
+
新RAW新增
```

### 场景6：权限错误

接口返回无权限：

```text
不无限重试
↓
Binding状态可见
```

---

# 92. 当前官方依据

当前官方接口文档确认：

## daily

```text
交易日15:00～16:00之间入库
基础积分每分钟500次
单次6000条
建议按交易日期循环提取全市场
```

## stock_basic

```text
2000积分
单次最多6000行
每分钟50次
```

## daily_basic

```text
2000积分
单次最多6000行
交易日15:00～17:00之间更新
```

## stk_limit

```text
2000积分
单次最多5800条
约08:40更新当日数据
```

## margin_detail

```text
2000积分
单次最多6000行
交易所约每天08:30更新上一日
```

这些信息进入SourceBinding配置，而不是直接散落硬编码。

官方参考：

```text
https://tushare.pro/document/1?doc_id=27
https://tushare.pro/document/1?doc_id=25
https://tushare.pro/document/2?doc_id=32
https://tushare.pro/document/2?doc_id=183
https://tushare.pro/document/2?doc_id=59
```

---

# 93. 最终结论

Tushare采集引擎确定为：

```text
配置驱动
+
标准策略
+
请求切片
+
自适应拆分
+
统一限流
+
断点恢复
+
幂等
+
RAW批次追溯
```

关键决策：

1. 不为每个接口开发独立采集程序；
2. 所有接口归入少量标准采集策略；
3. 日级全市场数据优先按交易日采集；
4. 单股票历史按时间窗口采集；
5. 财务数据按股票/报告期和公告语义采集；
6. 事件数据使用时间窗口+业务键+Hash增量；
7. 分钟按股票+频率+自适应时间窗口采集；
8. 命中接口返回上限必须继续拆分；
9. Token有效不等于接口可用；
10. 权限错误不能无限重试；
11. 所有长任务必须有数据库Checkpoint；
12. Worker退出后任务可重新领取；
13. 日常关键增量优先于历史全量；
14. 首批先做daily等低体量数据，再做分钟样本；
15. 采集成功和CLEAN可用必须分开；
16. 所有接口限制配置化并支持后续调整。
