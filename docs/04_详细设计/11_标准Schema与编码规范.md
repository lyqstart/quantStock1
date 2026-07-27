# 标准 Schema 与编码规范

> 路线图阶段：P4 数据治理与分层存储  
> 项目：A股量化研究与信号决策平台（quantStock1）  
> 文档性质：详细设计——CLEAN 标准 Schema 与编码基线  
> 日期：2026-07-27  
> 状态：已确认

---

# 1. 文档目的

本文件在《10_数据分层与主题域设计.md》基础上，正式确定 quantStock1 标准数据层的：

1. 命名规则；
2. 证券代码规则；
3. 交易所、频率、状态编码；
4. 日期、时间和时区规则；
5. 数值类型和单位规则；
6. NULL、0、空字符串的语义；
7. 主键和唯一性原则；
8. CLEAN 通用系统字段；
9. P3 已跑通的 10 个 DataItem 的第一版 CLEAN 标准表结构。

本文件是 P4 后续清洗规则、质量规则、血缘结构和数据库实施的字段基线。

---

# 2. 与 P3 设计的关系

P3 的《04_Tushare接口字段与数据表映射设计.md》已经完成 RAW 字段和初步 CLEAN 映射设计。

P4 在此基础上做一次正式标准化。

本文件确认：

```text
P3 RAW 映射
继续有效

P3 CLEAN 中与来源绑定的命名
由本文件正式标准替代
```

最重要的调整是：

```text
RAW:
ts_code

CLEAN:
security_code
```

值仍可以是：

```text
000001.SZ
600000.SH
920xxx.BJ
```

但 `security_code` 是 quantStock1 的平台字段，不再使用带有数据源含义的字段名 `ts_code`。

---

# 3. 总体命名规范

## 3.1 Schema

正式 Schema 继续使用：

```text
meta
raw
clean
quality
ops
audit
migration
research
```

P4 不再增加主题域 Schema。

---

## 3.2 表名

全部：

```text
小写
snake_case
业务语义命名
```

CLEAN 禁止出现：

```text
tushare_
akshare_
legacy_
```

例如：

```text
正确：
clean.stock_daily

错误：
clean.tushare_daily
```

---

## 3.3 业务字段

业务字段：

```text
snake_case
不使用来源前缀
不把单位藏在注释里
需要时把单位写入字段名
```

例如：

```text
volume_share
amount_cny
total_market_value_cny
```

而不是：

```text
vol
amount
mv
```

来源原字段仍原样保留在 RAW。

---

## 3.4 系统字段

CLEAN 系统字段统一以下划线开头：

```text
_clean_batch_id
_source
_available_at
_quality_status
_mapping_version
_normalization_version
_quality_rule_version
_created_at
_updated_at
```

这样业务字段和治理字段可以直接区分。

---

# 4. 平台证券代码

## 4.1 正式字段名

所有 CLEAN 股票级数据统一使用：

```text
security_code
```

不再使用：

```text
ts_code
code
stock_code
ticker
```

作为正式跨模块主标识。

---

## 4.2 A 股第一版格式

第一版 canonical code：

```text
6位证券代码 + "." + 交易所后缀
```

当前 A 股范围：

```text
.SH
.SZ
.BJ
```

例如：

```text
600000.SH
000001.SZ
920992.BJ
```

校验规则：

```text
^[0-9]{6}\.(SH|SZ|BJ)$
```

当前 P4 不重新编码为内部数字证券 ID。

原因：

```text
A股代码规模可控
代码可读
跨表联接直接
现阶段没有内部ID带来的实际收益
```

如果未来需要支持同一证券跨市场、多代码生命周期或全球资产，再新增内部 SecurityId，不提前复杂化。

---

# 5. symbol 与 exchange_code

`security_code` 之外，证券主表保留：

```text
symbol
exchange_code
```

例如：

```text
security_code = 000001.SZ
symbol        = 000001
exchange_code = SZSE
```

正式 exchange_code：

```text
SSE
SZSE
BSE
```

映射：

```text
.SH -> SSE
.SZ -> SZSE
.BJ -> BSE
```

所有映射由 CLEAN 规则显式完成。

不能依赖字符串猜测后静默写入。

---

# 6. 货币编码

正式货币代码使用：

```text
ISO 4217
```

当前 A 股默认：

```text
CNY
```

字段：

```text
currency_code
```

不使用：

```text
RMB
人民币
CNY人民币
```

作为数据库枚举。

---

# 7. 日期规范

所有纯业务日期使用 PostgreSQL：

```text
date
```

包括：

```text
trade_date
calendar_date
previous_trade_date
list_date
delist_date
report_period
ann_date
actual_ann_date
available_from_trade_date
```

RAW 中的：

```text
YYYYMMDD
```

字符串必须在 CLEAN 转成 `date`。

CLEAN 禁止继续用 `varchar(8)` 表示日期。

---

# 8. 时间与时区规范

## 8.1 时间点

所有真实时间点统一：

```text
timestamptz
```

包括：

```text
trade_time
_available_at
_created_at
_updated_at
observed_from
observed_to
```

---

## 8.2 业务时区

A 股正式业务时区：

```text
Asia/Shanghai
```

规则：

```text
来源没有时区
↓
按 Asia/Shanghai 解释
↓
写入 timestamptz
```

PostgreSQL 内部如何存储不作为业务语义；业务展示和规则解释统一使用 `Asia/Shanghai`。

---

## 8.3 分钟时间语义

`stock_minute.trade_time` 表示：

```text
bar结束时间
```

例如：

```text
09:31:00
```

表示截至 09:31 的该分钟 bar。

不能在不同接口中同时混用：

```text
bar开始时间
bar结束时间
```

---

# 9. 周期编码

分钟正式 frequency 保持 P3 已验证编码：

```text
1min
5min
15min
30min
60min
```

P4 第一阶段长期基础粒度：

```text
1min
```

其他周期优先由 1min 确定性聚合。

---

# 10. 数值类型原则

## 10.1 市场研究数值

第一版继续采用：

```text
double precision
```

用于：

- 价格；
- 比率；
- 百分比；
- 复权因子；
- 市值；
- 成交额；
- 财务数值；
- 财务指标。

这是研究分析数据，不是会计记账总账。

P4 不为了形式上的小数精确度把大规模行情全部改成高开销 `numeric`。

---

## 10.2 整数数量

能够明确转换为整数的数量使用：

```text
bigint
```

例如：

```text
volume_share
after_hours_volume_share
```

---

## 10.3 枚举

小型数值枚举使用：

```text
smallint
```

例如：

```text
limit_status
```

枚举解释进入元数据字典，不把中文文字作为事实值。

---

# 11. 单位规范

CLEAN 必须只存在一种正式单位。

## 11.1 价格

```text
元/股
```

适用：

```text
open
high
low
close
pre_close
up_limit
down_limit
change
```

---

## 11.2 成交量

统一：

```text
股
```

日线 Tushare RAW：

```text
手
```

转换：

```text
CLEAN volume_share = RAW vol × 100
```

分钟 RAW 当前已经是股：

```text
不得再次 ×100
```

---

## 11.3 成交额

统一：

```text
人民币元
```

日线 RAW：

```text
千元
```

转换：

```text
CLEAN amount_cny = RAW amount × 1000
```

分钟 RAW 当前已经是元：

```text
不得再次 ×1000
```

---

## 11.4 股本

`daily_basic` RAW 为：

```text
万股
```

CLEAN：

```text
股
```

转换：

```text
×10000
```

字段：

```text
total_share
float_share
free_share
```

---

## 11.5 市值

`daily_basic` RAW 为：

```text
万元
```

CLEAN：

```text
人民币元
```

转换：

```text
×10000
```

字段：

```text
total_market_value_cny
circulating_market_value_cny
```

---

## 11.6 百分比

百分比字段统一保存：

```text
百分数值
```

例如：

```text
5.23 = 5.23%
```

不是：

```text
0.0523
```

适用：

```text
pct_change
turnover_rate
turnover_rate_free
dividend_yield
dividend_yield_ttm
```

后续 Feature 层需要 0～1 小数时自行显式转换。

---

## 11.7 倍数/比率

PE、PB、PS、量比等继续保存：

```text
倍数原值
```

不隐式除100或乘100。

---

## 11.8 财务字段

当前财务接口没有一套已经被项目验证、可以安全用于全部字段的统一换算规则。

因此 P4 第一版继续遵守 P3 决策：

```text
financial_income
financial_indicator

保持来源返回数值
不做隐式 ×10000 / ÷100 / 单位猜测
```

每个财务字段的单位必须进入后续 FieldMetadata。

没有确认单位前，不允许通过字段名伪装成已完成单位标准化。

---

# 12. NULL 规范

## 12.1 NULL 的正式含义

`NULL` 表示：

```text
来源未提供
该历史时期不存在该字段
业务上不适用
当前无法可靠确定
```

---

## 12.2 0 的正式含义

`0` 只能表示：

```text
实际业务值为0
```

禁止：

```text
NULL -> 0
空字符串 -> 0
未知 -> 0
```

---

## 12.3 空字符串

字符串进入 CLEAN 前：

```text
仅空白字符串 -> NULL
```

除非某字段的业务规则明确允许空字符串作为有效值。

---

## 12.4 NaN / Infinity

数值型 CLEAN 禁止正式发布：

```text
NaN
+Infinity
-Infinity
```

发现后进入质量问题，不通过 NULL 或 0 静默替代。

---

## 12.5 历史新增字段

例如：

```text
stock_daily.ah_vol
stock_daily.ah_amount
```

2026-07-06 之前没有来源数据时：

```text
NULL = 合法历史状态
```

不能因此单独判定整行失败。

---

# 13. Boolean 规范

布尔型字段统一 PostgreSQL：

```text
boolean
```

例如：

```text
trade_calendar.is_open
```

来源：

```text
'1' -> true
'0' -> false
```

无法识别的来源值不能强转，应进入质量异常。

---

# 14. 状态与枚举规范

正式数据库只保存稳定代码。

例如：

```text
list_status:
L
D
P
G
```

```text
stock_suspend.event_type:
S
R
```

```text
limit_status:
0
1
2
3
4
5
6
```

中文说明进入：

```text
meta 字典/展示层
```

不在事实表存：

```text
“上市”
“退市”
“涨停”
```

作为唯一状态值。

---

# 15. CLEAN 通用治理字段

普通 CLEAN 表第一版统一包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| `_clean_batch_id` | UUID | 生成本记录的清洗批次 |
| `_source` | varchar(32) | 当前正式值的数据来源代码 |
| `_available_at` | timestamptz | 最早允许下游使用的时间 |
| `_quality_status` | varchar(16) | 当前质量门禁状态 |
| `_mapping_version` | varchar(32) | 字段映射版本 |
| `_normalization_version` | varchar(32) | 标准化规则版本 |
| `_quality_rule_version` | varchar(32) | 质量规则版本 |
| `_created_at` | timestamptz | 首次建立 |
| `_updated_at` | timestamptz | 最近更新 |

其中：

```text
_clean_batch_id
```

是行级追溯入口。

具体 CleanBatch 表结构在 P4 血缘专题中确定。

---

# 16. 高容量分钟表例外

`clean.stock_minute` 预计是长期最大表。

不能在未来数十亿行上重复保存大量字符串治理字段。

分钟事实表每行只强制保留：

```text
_clean_batch_id
```

其余：

```text
source
mapping_version
normalization_version
quality_rule_version
quality_status
```

优先放到 CleanBatch / 分区质量记录。

只有发生行级异常时才建立单独异常引用。

这样：

```text
业务行保持窄表
治理信息仍可追溯
```

---

# 17. 主键总原则

## 17.1 稳定自然键

稳定且明确的数据使用业务复合主键。

例如：

```text
股票 + 交易日
```

---

## 17.2 事件/版本数据

存在多版本、多事件的数据使用：

```text
UUID 内部主键
+
业务唯一性约束/索引
```

不能为了方便把不同版本覆盖成一行。

---

# 18. clean.trade_calendar

DataItem：

```text
trade_calendar
```

主键：

```text
(exchange_code, calendar_date)
```

标准字段：

| 字段 | 类型 | NULL | 说明 |
|---|---|---:|---|
| `exchange_code` | varchar(8) | 否 | SSE/SZSE/BSE |
| `calendar_date` | date | 否 | 日历日期 |
| `is_open` | boolean | 否 | 是否交易 |
| `previous_trade_date` | date | 是 | 上一有效交易日 |

只有实际验证过的交易所 SourceBinding 才能进入 CLEAN。

不能根据沪深交易日历推断北交所。

---

# 19. clean.security_master

DataItem：

```text
stock_basic
```

主键：

```text
security_code
```

字段：

| 字段 | 类型 | NULL |
|---|---|---:|
| `security_code` | varchar(16) | 否 |
| `symbol` | varchar(16) | 否 |
| `name` | varchar(128) | 是 |
| `area` | varchar(64) | 是 |
| `industry_name` | varchar(128) | 是 |
| `full_name` | varchar(256) | 是 |
| `english_name` | varchar(256) | 是 |
| `cn_spell` | varchar(64) | 是 |
| `market` | varchar(32) | 是 |
| `exchange_code` | varchar(8) | 否 |
| `currency_code` | varchar(8) | 是 |
| `list_status` | varchar(8) | 否 |
| `list_date` | date | 是 |
| `delist_date` | date | 是 |
| `hsgt_status` | varchar(8) | 是 |
| `actual_controller_name` | varchar(256) | 是 |
| `actual_controller_entity_type` | varchar(128) | 是 |

`security_master` 表示：

```text
当前已确认的主记录
```

不能作为历史某日证券属性的真值来源。

---

# 20. clean.security_master_history

`stock_basic` 同时维护系统观察历史。

主键：

```text
security_master_version_id UUID
```

字段至少：

```text
security_master_version_id
security_code
observed_from
observed_to
content_hash
+ security_master业务字段
+ 通用治理字段
```

这里使用：

```text
observed_from / observed_to
```

而不是：

```text
valid_from / valid_to
```

原因：

当前 `stock_basic` 只证明“系统从什么时候观察到这个版本”，不能证明该属性在历史市场中的真实生效时间。

---

# 21. clean.stock_daily

DataItem：

```text
stock_daily
```

主键：

```text
(security_code, trade_date)
```

字段：

| 字段 | 类型 | 单位 |
|---|---|---|
| `security_code` | varchar(16) | - |
| `trade_date` | date | - |
| `open` | double precision | 元/股 |
| `high` | double precision | 元/股 |
| `low` | double precision | 元/股 |
| `close` | double precision | 元/股 |
| `pre_close` | double precision | 元/股 |
| `change` | double precision | 元/股 |
| `pct_change` | double precision | % |
| `volume_share` | bigint | 股 |
| `amount_cny` | double precision | 元 |
| `after_hours_volume_share` | bigint | 股 |
| `after_hours_amount_cny` | double precision | 元 |

索引：

```text
PRIMARY KEY(security_code, trade_date)
INDEX(trade_date)
```

只保存：

```text
未复权官方事实
```

不在本表持久化前复权、后复权价格。

---

# 22. clean.stock_adj_factor

DataItem：

```text
stock_adj_factor
```

主键：

```text
(security_code, trade_date)
```

字段：

```text
security_code varchar(16) NOT NULL
trade_date date NOT NULL
adj_factor double precision NULL
```

索引：

```text
PRIMARY KEY(security_code, trade_date)
INDEX(trade_date)
```

历史因子允许后续更新，但每次变化必须有 CleanBatch 和来源批次追溯。

---

# 23. clean.stock_daily_basic

DataItem：

```text
stock_daily_basic
```

主键：

```text
(security_code, trade_date)
```

标准字段：

```text
security_code
trade_date
close
turnover_rate
turnover_rate_free
volume_ratio
pe
pe_ttm
pb
ps
ps_ttm
dividend_yield
dividend_yield_ttm
total_share
float_share
free_share
total_market_value_cny
circulating_market_value_cny
limit_status
```

类型：

```text
security_code -> varchar(16)
trade_date -> date
limit_status -> smallint
其余 -> double precision
```

其中股本和市值按照第 11 节完成单位转换。

索引：

```text
PRIMARY KEY(security_code, trade_date)
INDEX(trade_date)
```

---

# 24. clean.stock_suspend_event

DataItem：

```text
stock_suspend
```

停复牌属于事件，不使用普通日快照表结构。

主键：

```text
suspend_event_id UUID
```

字段：

```text
suspend_event_id UUID
security_code varchar(16)
trade_date date
event_type varchar(8)
suspend_timing varchar(64) NULL
+ 通用治理字段
```

业务唯一约束：

```text
security_code
+
trade_date
+
event_type
+
COALESCE(suspend_timing,'')
```

同一股票同一天的停牌和复牌不能相互覆盖。

---

# 25. clean.stock_limit_price

DataItem：

```text
stock_limit_price
```

主键：

```text
(security_code, trade_date)
```

字段：

```text
security_code varchar(16)
trade_date date
pre_close double precision
up_limit double precision
down_limit double precision
```

单位：

```text
元/股
```

进入 CLEAN 前必须通过 `security_master` 验证属于当前平台正式 A 股证券范围。

RAW 可以保留来源返回的额外证券。

---

# 26. clean.stock_minute

DataItem：

```text
stock_minute
```

主键：

```text
(security_code, frequency, trade_time)
```

字段：

| 字段 | 类型 | 单位 |
|---|---|---|
| `security_code` | varchar(16) | - |
| `frequency` | varchar(8) | - |
| `trade_time` | timestamptz | Asia/Shanghai bar结束时间 |
| `open` | double precision | 元/股 |
| `high` | double precision | 元/股 |
| `low` | double precision | 元/股 |
| `close` | double precision | 元/股 |
| `volume_share` | bigint | 股 |
| `amount_cny` | double precision | 元 |
| `_clean_batch_id` | UUID | 血缘入口 |

TimescaleDB：

```text
Hypertable time_column = trade_time
```

查询核心：

```text
security_code + frequency + time range
```

chunk、压缩、保留周期在 P4 存储生命周期专题通过真实数据量确定。

---

# 27. clean.financial_income

DataItem：

```text
financial_income
```

主键：

```text
financial_version_id UUID
```

关键身份字段：

| 字段 | 类型 | NULL |
|---|---|---:|
| `financial_version_id` | UUID | 否 |
| `security_code` | varchar(16) | 否 |
| `ann_date` | date | 是 |
| `actual_ann_date` | date | 是 |
| `report_period` | date | 否 |
| `report_type` | varchar(8) | 是 |
| `company_type` | varchar(8) | 是 |
| `period_type` | varchar(8) | 是 |
| `update_flag` | varchar(8) | 是 |
| `available_from_trade_date` | date | 否 |
| `content_hash` | char(64) | 否 |

其余利润表数值字段：

```text
沿用 P3《04_Tushare接口字段与数据表映射设计.md》
已确认的完整字段集合
```

第一版 PostgreSQL 类型：

```text
double precision
```

单位：

```text
保持来源明确返回语义
不做未经确认的隐式换算
```

索引：

```text
INDEX(security_code, report_period)
INDEX(available_from_trade_date)
INDEX(security_code, content_hash)
```

不能使用：

```text
security_code + report_period
```

覆盖历史版本。

---

# 28. clean.financial_indicator

DataItem：

```text
financial_indicator
```

主键：

```text
financial_indicator_version_id UUID
```

关键字段：

```text
financial_indicator_version_id UUID
security_code varchar(16)
ann_date date
report_period date
update_flag varchar(8)
available_from_trade_date date
content_hash char(64)
```

其余财务指标字段：

```text
沿用 P3 已确认完整字段集合
```

第一版类型：

```text
double precision
```

索引：

```text
INDEX(security_code, report_period)
INDEX(available_from_trade_date)
INDEX(security_code, content_hash)
```

同样禁止按报告期覆盖旧版本。

---

# 29. 首批 DataItem → CLEAN 表总表

| DataItem | CLEAN正式表 | 正式主键 |
|---|---|---|
| `trade_calendar` | `clean.trade_calendar` | `(exchange_code, calendar_date)` |
| `stock_basic` | `clean.security_master` | `security_code` |
| `stock_basic` | `clean.security_master_history` | `security_master_version_id` |
| `stock_daily` | `clean.stock_daily` | `(security_code, trade_date)` |
| `stock_adj_factor` | `clean.stock_adj_factor` | `(security_code, trade_date)` |
| `stock_daily_basic` | `clean.stock_daily_basic` | `(security_code, trade_date)` |
| `stock_suspend` | `clean.stock_suspend_event` | `suspend_event_id` |
| `stock_limit_price` | `clean.stock_limit_price` | `(security_code, trade_date)` |
| `stock_minute` | `clean.stock_minute` | `(security_code, frequency, trade_time)` |
| `financial_income` | `clean.financial_income` | `financial_version_id` |
| `financial_indicator` | `clean.financial_indicator` | `financial_indicator_version_id` |

---

# 30. 外键原则

高容量事实表不强制建立到 `security_master` 的数据库物理外键。

例如：

```text
stock_daily
stock_minute
```

原因：

```text
大批量写入性能
历史退市证券仍需存在
主数据刷新时不能阻断历史事实
```

但 CLEAN 发布时必须进行逻辑证券范围校验。

因此：

```text
无物理FK
≠
无数据完整性检查
```

完整性由 Clean/Quality Gate 负责。

---

# 31. 可用时间字段

正式区分：

```text
业务时间
数据可用时间
系统处理时间
```

例如：

```text
trade_date
_available_at
_updated_at
```

三者不能混为一个字段。

财务数据额外保留：

```text
available_from_trade_date
```

用于清晰表达日级防未来函数边界。

具体各 DataItem 的 `_available_at` 计算规则在 P4 清洗规则专题确定。

---

# 32. CLEAN 写入规则

所有 CLEAN 写入必须满足：

```text
先标准化
↓
质量检查
↓
通过门禁
↓
幂等发布
```

日级快照：

```text
按业务主键 upsert
```

但必须：

```text
内容变化
↓
保留新 CleanBatch
↓
能够追溯旧来源与规则版本
```

事件和财务版本数据：

```text
不得简单覆盖
```

---

# 33. 字段增加规则

来源新增字段不能自动进入 CLEAN。

流程：

```text
RAW先接住
↓
SchemaFingerprint识别
↓
确认业务语义与单位
↓
升级字段映射版本
↓
Alembic新增CLEAN列
↓
测试
↓
正式启用
```

---

# 34. 字段删除/改名规则

来源删除或改名：

```text
不直接删除CLEAN业务字段
```

先判断：

```text
只是来源变化
还是业务语义真的消失
```

来源变化由 mapping 层适配。

只有平台业务语义变化时才修改 CLEAN Contract。

---

# 35. 第一版必须验证的编码规则

P4 实施时至少自动测试：

1. `ts_code -> security_code` 正确；
2. SH/SZ/BJ 与 SSE/SZSE/BSE 映射正确；
3. 日期字符串全部转 `date`；
4. 分钟时间按 Asia/Shanghai 转 `timestamptz`；
5. 日线手→股只转换一次；
6. 日线千元→元只转换一次；
7. 分钟量额不重复换算；
8. daily_basic 万股→股；
9. daily_basic 万元→元；
10. 百分数没有误除100；
11. NULL 没有误填0；
12. 空字符串标准化为 NULL；
13. NaN/Infinity 不允许正式发布；
14. 财务历史版本不覆盖；
15. 分钟零成交 bar 不因 0 自动删除；
16. 北交所交易日历不能通过沪深数据猜测；
17. 高容量分钟表没有重复存储完整治理元数据。

---

# 36. P4.2 正式决策

本文件确认：

1. CLEAN 证券主标识正式改为 `security_code`；
2. 第一版 security_code 使用 `000001.SZ` 等可读格式；
3. 交易所统一 SSE/SZSE/BSE；
4. 日期统一 PostgreSQL `date`；
5. 时间统一 `timestamptz`，A股业务时区 Asia/Shanghai；
6. 分钟 trade_time 统一为 bar 结束时间；
7. 行情价格、比率、财务指标第一版使用 `double precision`；
8. 明确整数股数使用 `bigint`；
9. 成交量统一股，成交额和市值统一人民币元；
10. 百分比保存百分数值，不保存 0～1 小数；
11. NULL、0、空字符串语义严格区分；
12. 财务数据不做未经确认的隐式单位换算；
13. 普通 CLEAN 表保留完整治理字段；
14. stock_minute 采用窄表，治理信息主要放批次级；
15. 稳定日级事实使用业务复合主键；
16. 停复牌、财务历史使用 UUID 版本/事件主键；
17. 高容量事实表不强制物理外键，完整性由质量门禁保证；
18. P4 正式 CLEAN 命名覆盖 P3 中带来源色彩的 CLEAN 字段命名，P3 RAW 映射继续有效。

---

# 37. 下一步

进入：

```text
P4.3 清洗规则与状态口径
```

下一步正式确定：

```text
RAW → CLEAN 每个字段怎么转换
证券范围怎么判定
上市/退市/ST/停复牌如何表达
异常值怎么处理
来源修订如何覆盖
财务版本如何选择
_available_at如何计算
清洗成功/阻断/重洗的状态机
```
