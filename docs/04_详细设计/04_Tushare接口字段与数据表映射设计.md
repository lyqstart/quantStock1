# Tushare接口字段与数据表映射设计

> 路线图阶段：P3 数据源与采集平台  
> 项目：A股量化研究与信号决策平台（quantStock1）  
> 文档性质：详细设计——第一批正式接口字段与表结构基线  
> 日期：2026-07-27  
> 状态：第一批字段基线已确认

---

# 1. 设计范围

本版先完成第一批开发直接需要的10个DataItem：

```text
trade_calendar
stock_basic
stock_daily
stock_adj_factor
stock_daily_basic
stock_suspend
stock_limit_price
stock_minute
financial_income
financial_indicator
```

后续其它Tushare接口继续按本文件相同模板追加。

这样第一轮开发不需要等待80多个接口全部完成字段设计。

---

# 2. 设计原则

## 2.1 RAW与CLEAN分离

```text
Tushare字段
↓
RAW原始表
↓
FieldMappingVersion
↓
CLEAN标准表
```

RAW用于保存来源事实。

CLEAN用于平台正式研究。

---

## 2.2 RAW字段名原则

RAW字段：

```text
尽量保持Tushare原字段名
```

这样：

- 容易和官方文档对账；
- 容易排查接口变化；
- 迁移和重新清洗简单。

---

## 2.3 CLEAN字段名原则

CLEAN字段按平台业务语义定义。

如果Tushare字段名本身已经足够清晰，可以保持同名。

“同名”不表示CLEAN依赖Tushare。

真正解耦关系由：

```text
FieldMappingVersion
```

确定。

以后AKShare进入同一个DataItem时，需要映射到同一个CLEAN Contract。

---

# 3. PostgreSQL类型统一规则

| 业务类型 | RAW建议 | CLEAN建议 |
|---|---|---|
| 股票/指数代码 | `varchar(16)` | `varchar(16)` |
| 日期型Tushare `YYYYMMDD` | `char(8)` | `date` |
| 分钟时间字符串 | `varchar(19)` | `timestamptz` |
| 枚举/状态 | `varchar(...)` | `varchar(...)`或受控枚举 |
| 普通数值 | `double precision` | `double precision` |
| 计数/整数 | `bigint` | `bigint` |
| 布尔含义 | 原值保存 | `boolean`或受控状态 |
| 内容Hash | `char(64)` | 必要时保留 |
| JSON扩展 | 原则上不用万能JSON表 | 只用于少量不可预知扩展 |

---

# 4. 时间规则

## 4.1 RAW

保留Tushare原始日期/时间字符串。

例如：

```text
trade_date = '20260724'
```

## 4.2 CLEAN

标准化：

```text
trade_date -> PostgreSQL date
trade_time -> timestamptz
```

Tushare A股分钟时间没有携带时区时：

```text
按 Asia/Shanghai 解释
```

后再写入`timestamptz`。

---

# 5. 单位统一规则

这是本次字段设计最重要的规则之一。

Tushare日线：

```text
vol = 手
amount = 千元
```

Tushare历史分钟：

```text
vol = 股
amount = 元
```

因此CLEAN统一为：

```text
volume_share = 股
amount_cny = 人民币元
```

日线转换：

```text
volume_share = vol * 100
amount_cny = amount * 1000
```

分钟：

```text
volume_share = vol
amount_cny = amount
```

这样以后跨日线/分钟聚合时不会产生100倍或1000倍误差。

---

# 6. 百分比规则

Tushare明确标记为 `%` 的字段：

```text
CLEAN仍以“百分数值”保存
```

例如：

```text
2.35 = 2.35%
```

不在CLEAN层自动除以100。

Feature计算需要小数比例时，由公共数值转换函数显式处理。

避免：

```text
有些表2.35
有些表0.0235
```

的隐性混乱。

---

# 7. RAW通用审计字段

所有RAW表追加：

| 字段 | 类型 | 说明 |
|---|---|---|
| `_raw_id` | `bigint`/UUID | RAW内部记录ID |
| `_source` | `varchar(32)` | `tushare` |
| `_source_api` | `varchar(64)` | API名称 |
| `_collect_run_id` | UUID | 采集执行 |
| `_raw_batch_id` | UUID | RAW批次 |
| `_fetched_at` | `timestamptz` | 实际获取时间 |
| `_request_hash` | `char(64)` | 请求指纹 |
| `_content_hash` | `char(64)` | 数据正文指纹 |
| `_schema_version` | `varchar(32)` | 来源结构版本 |

不重复保存完整RAW JSON副本，避免容量翻倍。

---

# 8. CLEAN通用系统字段

正式CLEAN表根据需要追加：

| 字段 | 类型 | 说明 |
|---|---|---|
| `_clean_batch_id` | UUID | 产生本记录的Clean批次 |
| `_source` | `varchar(32)` | 当前正式值来源 |
| `_available_at` | `timestamptz`/date | 最早允许研究使用时间 |
| `_quality_status` | `varchar(16)` | 质量状态 |
| `_mapping_version` | `varchar(32)` | 字段映射版本 |
| `_created_at` | `timestamptz` | 建立时间 |
| `_updated_at` | `timestamptz` | 最后更新 |

---

# 9. trade_calendar / 交易日历

官方接口：

```text
trade_cal
```

RAW表：

```text
raw.tushare_trade_cal
```

CLEAN表：

```text
clean.trade_calendar
```

业务唯一键：

```text
exchange + cal_date
```

字段映射：

| Tushare | RAW | CLEAN | RAW类型 | CLEAN类型 | 语义 |
|---|---|---|---|---|---|
| `exchange` | `exchange` | `exchange` | `varchar(16)` | `varchar(16)` | 交易所 |
| `cal_date` | `cal_date` | `cal_date` | `char(8)` | `date` | 日历日期 |
| `is_open` | `is_open` | `is_open` | `varchar(1)` | `boolean` | 是否交易 |
| `pretrade_date` | `pretrade_date` | `previous_trade_date` | `char(8)` | `date` | 上一交易日 |

转换：

```text
is_open == '1' -> true
is_open == '0' -> false
```

注意：

当前官方接口说明明确列出SSE、SZSE等交易所，但没有把BSE列入该字段说明。

因此：

```text
北交所交易日历不能靠猜测
```

实施阶段需要接口级实测后再决定BSE的正式Calendar来源。

---

# 10. stock_basic / 股票基础信息

官方接口：

```text
stock_basic
```

RAW表：

```text
raw.tushare_stock_basic
```

CLEAN：

```text
clean.security_master
clean.security_master_history
```

`security_master`保存当前有效主记录。

`security_master_history`在内容变化时形成历史版本。

当前主键：

```text
ts_code
```

字段映射：

| Tushare | CLEAN | 类型 | 说明 |
|---|---|---|---|
| `ts_code` | `ts_code` | `varchar(16)` | TS代码，主键 |
| `symbol` | `symbol` | `varchar(16)` | 本地股票代码 |
| `name` | `name` | `varchar(128)` | 股票名称 |
| `area` | `area` | `varchar(64)` | 地域 |
| `industry` | `industry_name` | `varchar(128)` | Tushare当前行业标签 |
| `fullname` | `full_name` | `varchar(256)` | 股票全称 |
| `enname` | `english_name` | `varchar(256)` | 英文名称 |
| `cnspell` | `cn_spell` | `varchar(64)` | 拼音缩写 |
| `market` | `market` | `varchar(32)` | 市场类型 |
| `exchange` | `exchange` | `varchar(16)` | SSE/SZSE/BSE |
| `curr_type` | `currency` | `varchar(16)` | 交易货币 |
| `list_status` | `list_status` | `varchar(8)` | L/D/G/P |
| `list_date` | `list_date` | `date` | 上市日期 |
| `delist_date` | `delist_date` | `date` | 退市日期 |
| `is_hs` | `hsgt_status` | `varchar(8)` | 沪深港通标记 |
| `act_name` | `actual_controller_name` | `varchar(256)` | 实控人名称 |
| `act_ent_type` | `actual_controller_entity_type` | `varchar(128)` | 实控人企业性质 |

历史注意：

```text
stock_basic是当前基础资料来源
```

不能拿今天的`industry/name/list_status`直接回填过去某一历史时点。

只有带有明确有效期的数据才能用于历史时点关系判断。

---

# 11. stock_daily / A股日线

官方接口：

```text
daily
```

RAW：

```text
raw.tushare_daily
```

CLEAN：

```text
clean.stock_daily
```

唯一键：

```text
ts_code + trade_date
```

字段映射：

| Tushare | CLEAN | CLEAN类型 | 单位/规则 |
|---|---|---|---|
| `ts_code` | `ts_code` | `varchar(16)` | 股票代码 |
| `trade_date` | `trade_date` | `date` | 交易日 |
| `open` | `open` | `double precision` | 元/股 |
| `high` | `high` | `double precision` | 元/股 |
| `low` | `low` | `double precision` | 元/股 |
| `close` | `close` | `double precision` | 元/股 |
| `pre_close` | `pre_close` | `double precision` | 除权昨收 |
| `change` | `change` | `double precision` | 元/股 |
| `pct_chg` | `pct_change` | `double precision` | % |
| `vol` | `volume_share` | `bigint` | RAW为手；CLEAN×100为股 |
| `amount` | `amount_cny` | `double precision` | RAW为千元；CLEAN×1000为元 |
| `ah_vol` | `after_hours_volume_share` | `bigint` | RAW为手；×100；2026-07-06起有数据 |
| `ah_amount` | `after_hours_amount_cny` | `double precision` | RAW为千元；×1000；2026-07-06起有数据 |

`ah_vol`、`ah_amount`必须允许NULL。

不能因为历史数据为空判为质量失败。

---

# 12. stock_daily的价格语义

Tushare当前官方说明：

```text
daily为未复权行情
pre_close为除权价
pct_chg基于除权后的昨收计算
```

因此：

```text
clean.stock_daily
```

只保存未复权官方事实。

前复权/后复权价格：

```text
stock_daily
+
stock_adj_factor
```

计算获得。

不另外把复权价格当作原始事实长期重复存储。

---

# 13. stock_adj_factor / 复权因子

RAW：

```text
raw.tushare_adj_factor
```

CLEAN：

```text
clean.stock_adj_factor
```

唯一键：

```text
ts_code + trade_date
```

| Tushare | CLEAN | 类型 | 单位 |
|---|---|---|---|
| `ts_code` | `ts_code` | `varchar(16)` | - |
| `trade_date` | `trade_date` | `date` | - |
| `adj_factor` | `adj_factor` | `double precision` | 因子 |

复权因子可能随除权事件刷新。

更新策略必须允许：

```text
历史trade_date对应值发生变化
```

并留下批次追溯。

---

# 14. stock_daily_basic / 每日指标

RAW：

```text
raw.tushare_daily_basic
```

CLEAN：

```text
clean.stock_daily_basic
```

唯一键：

```text
ts_code + trade_date
```

字段映射：

| Tushare | CLEAN | CLEAN类型 | CLEAN单位 |
|---|---|---|---|
| `ts_code` | `ts_code` | `varchar(16)` | - |
| `trade_date` | `trade_date` | `date` | - |
| `close` | `close` | `double precision` | 元/股 |
| `turnover_rate` | `turnover_rate` | `double precision` | % |
| `turnover_rate_f` | `turnover_rate_free` | `double precision` | % |
| `volume_ratio` | `volume_ratio` | `double precision` | 倍 |
| `pe` | `pe` | `double precision` | 倍 |
| `pe_ttm` | `pe_ttm` | `double precision` | 倍 |
| `pb` | `pb` | `double precision` | 倍 |
| `ps` | `ps` | `double precision` | 倍 |
| `ps_ttm` | `ps_ttm` | `double precision` | 倍 |
| `dv_ratio` | `dividend_yield` | `double precision` | % |
| `dv_ttm` | `dividend_yield_ttm` | `double precision` | % |
| `total_share` | `total_share` | `double precision` | CLEAN换算为股：RAW×10000 |
| `float_share` | `float_share` | `double precision` | CLEAN换算为股：RAW×10000 |
| `free_share` | `free_share` | `double precision` | CLEAN换算为股：RAW×10000 |
| `total_mv` | `total_market_value_cny` | `double precision` | CLEAN换算为元：RAW×10000 |
| `circ_mv` | `circulating_market_value_cny` | `double precision` | CLEAN换算为元：RAW×10000 |
| `limit_status` | `limit_status` | `smallint` | 0～6，按官方枚举 |

---

# 15. limit_status

当前官方定义：

```text
0 平盘
1 上涨（不含涨停）
2 涨停（不含一字涨停）
3 一字涨停
4 下跌（不含跌停）
5 跌停（不含一字跌停）
6 一字跌停
```

系统保留数字值，并在meta字典中保存解释。

不要只存中文文字。

---

# 16. stock_suspend / 每日停复牌

RAW：

```text
raw.tushare_suspend_d
```

CLEAN：

```text
clean.stock_suspend_event
```

业务键不能仅使用：

```text
ts_code + trade_date
```

因为同一股票/日期需要区分S/R以及可能的日内时段。

建议唯一性：

```text
ts_code
+
trade_date
+
suspend_type
+
COALESCE(suspend_timing,'')
```

字段：

| Tushare | CLEAN | 类型 | 说明 |
|---|---|---|---|
| `ts_code` | `ts_code` | `varchar(16)` | 股票 |
| `trade_date` | `trade_date` | `date` | 停复牌日期 |
| `suspend_timing` | `suspend_timing` | `varchar(64)` | 可NULL，如09:30-10:00 |
| `suspend_type` | `event_type` | `varchar(8)` | S停牌/R复牌 |

---

# 17. stock_limit_price / 涨跌停价格

RAW：

```text
raw.tushare_stk_limit
```

CLEAN：

```text
clean.stock_limit_price
```

唯一键：

```text
ts_code + trade_date
```

字段：

| Tushare | CLEAN | 类型 |
|---|---|---|
| `trade_date` | `trade_date` | `date` |
| `ts_code` | `ts_code` | `varchar(16)` |
| `pre_close` | `pre_close` | `double precision` |
| `up_limit` | `up_limit` | `double precision` |
| `down_limit` | `down_limit` | `double precision` |

注意：

Tushare接口覆盖说明包含A/B股和基金。

quantStock1的DataItem是A股研究数据，因此进入CLEAN前必须通过：

```text
security_master
```

限定正式A股证券范围。

RAW仍可保留来源实际返回范围。

---

# 18. stock_minute / 历史分钟

官方API：

```text
stk_mins
```

RAW：

```text
raw.tushare_stk_mins
```

CLEAN：

```text
clean.stock_minute
```

TimescaleDB：

```text
Hypertable
time_column = trade_time
```

正式唯一键：

```text
ts_code + frequency + trade_time
```

字段：

| Tushare | CLEAN | CLEAN类型 | 单位 |
|---|---|---|---|
| `ts_code` | `ts_code` | `varchar(16)` | - |
| `trade_time` | `trade_time` | `timestamptz` | Asia/Shanghai解释 |
| `open` | `open` | `double precision` | 元/股 |
| `close` | `close` | `double precision` | 元/股 |
| `high` | `high` | `double precision` | 元/股 |
| `low` | `low` | `double precision` | 元/股 |
| `vol` | `volume_share` | `bigint` | 股 |
| `amount` | `amount_cny` | `double precision` | 元 |

Tushare输出没有单独返回`freq`列。

因此：

```text
frequency
```

必须由请求上下文写入RAW/CLEAN。

允许值：

```text
1min
5min
15min
30min
60min
```

---

# 19. 分钟时间边界

官方样例显示：

```text
09:30:00
...
15:00:00
```

并可能出现：

```text
vol = 0
amount = 0
```

的bar。

因此：

```text
零成交bar不能仅因volume=0自动删除
```

必须保留来源事实，再由质量规则判定其合法性。

---

# 20. financial_income / 利润表

官方API：

```text
income
```

RAW：

```text
raw.tushare_income
```

CLEAN：

```text
clean.financial_income
```

财务记录不能用：

```text
ts_code + end_date
```

覆盖式存储。

必须保留版本。

---

# 21. 利润表版本字段

关键字段：

| Tushare | CLEAN | 类型 | 作用 |
|---|---|---|---|
| `ts_code` | `ts_code` | `varchar(16)` | 股票 |
| `ann_date` | `ann_date` | `date` | 公告日期 |
| `f_ann_date` | `actual_ann_date` | `date` | 实际公告日期 |
| `end_date` | `report_period` | `date` | 报告期 |
| `report_type` | `report_type` | `varchar(8)` | 报表类型 |
| `comp_type` | `company_type` | `varchar(8)` | 公司类型 |
| `end_type` | `period_type` | `varchar(8)` | 报告期类型 |
| `update_flag` | `update_flag` | `varchar(8)` | 更新标识 |

CLEAN内部增加：

```text
financial_version_id
available_from_trade_date
content_hash
```

---

# 22. 利润表历史可用时间

为了防未来数据泄漏：

```text
published_date
=
优先 actual_ann_date
否则 ann_date
```

由于该接口只提供日期、没有精确发布时间，日级回测采用保守规则：

```text
available_from_trade_date
=
published_date之后的第一个有效交易日
```

这样不会假设财报在公告日开盘前就已经可用。

如果以后获得精确公告时间，可升级规则版本。

---

# 23. report_type必须保留

官方当前明确存在多种报表类型，包括：

```text
1 合并报表
2 单季合并
3 调整单季合并表
4 调整合并报表
5 调整前合并报表
6 母公司报表
7 母公司单季表
8 母公司调整单季表
9 母公司调整表
10 母公司调整前报表
11 母公司调整前合并报表
12 母公司调整前报表
```

不能只保留默认类型后覆盖其它版本。

---

# 24. 利润表全部普通数值字段

下面字段均从TushareRAW显式映射到CLEAN同名语义字段。

Tushare官方页面对这些财务数值没有提供一个可以统一安全换算的全局单位规则。

因此第一版：

```text
保持Tushare返回原数值
不做隐式×10000等换算
```

后续每个字段的单位进入FieldMetadata后再显式转换。

| Source | RAW | CLEAN | PostgreSQL | 单位处理 | 角色 |
|---|---|---|---|---|---|
| `basic_eps` | `basic_eps` | `basic_eps` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `diluted_eps` | `diluted_eps` | `diluted_eps` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `total_revenue` | `total_revenue` | `total_revenue` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `revenue` | `revenue` | `revenue` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `int_income` | `int_income` | `int_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `prem_earned` | `prem_earned` | `prem_earned` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `comm_income` | `comm_income` | `comm_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `n_commis_income` | `n_commis_income` | `n_commis_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `n_oth_income` | `n_oth_income` | `n_oth_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `n_oth_b_income` | `n_oth_b_income` | `n_oth_b_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `prem_income` | `prem_income` | `prem_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `out_prem` | `out_prem` | `out_prem` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `une_prem_reser` | `une_prem_reser` | `une_prem_reser` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `reins_income` | `reins_income` | `reins_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `n_sec_tb_income` | `n_sec_tb_income` | `n_sec_tb_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `n_sec_uw_income` | `n_sec_uw_income` | `n_sec_uw_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `n_asset_mg_income` | `n_asset_mg_income` | `n_asset_mg_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `oth_b_income` | `oth_b_income` | `oth_b_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `fv_value_chg_gain` | `fv_value_chg_gain` | `fv_value_chg_gain` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `invest_income` | `invest_income` | `invest_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ass_invest_income` | `ass_invest_income` | `ass_invest_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `forex_gain` | `forex_gain` | `forex_gain` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `total_cogs` | `total_cogs` | `total_cogs` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `oper_cost` | `oper_cost` | `oper_cost` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `int_exp` | `int_exp` | `int_exp` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `comm_exp` | `comm_exp` | `comm_exp` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `biz_tax_surchg` | `biz_tax_surchg` | `biz_tax_surchg` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `sell_exp` | `sell_exp` | `sell_exp` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `admin_exp` | `admin_exp` | `admin_exp` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `fin_exp` | `fin_exp` | `fin_exp` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `assets_impair_loss` | `assets_impair_loss` | `assets_impair_loss` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `prem_refund` | `prem_refund` | `prem_refund` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `compens_payout` | `compens_payout` | `compens_payout` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `reser_insur_liab` | `reser_insur_liab` | `reser_insur_liab` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `div_payt` | `div_payt` | `div_payt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `reins_exp` | `reins_exp` | `reins_exp` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `oper_exp` | `oper_exp` | `oper_exp` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `compens_payout_refu` | `compens_payout_refu` | `compens_payout_refu` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `insur_reser_refu` | `insur_reser_refu` | `insur_reser_refu` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `reins_cost_refund` | `reins_cost_refund` | `reins_cost_refund` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `other_bus_cost` | `other_bus_cost` | `other_bus_cost` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `operate_profit` | `operate_profit` | `operate_profit` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `non_oper_income` | `non_oper_income` | `non_oper_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `non_oper_exp` | `non_oper_exp` | `non_oper_exp` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `nca_disploss` | `nca_disploss` | `nca_disploss` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `total_profit` | `total_profit` | `total_profit` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `income_tax` | `income_tax` | `income_tax` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `n_income` | `n_income` | `n_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `n_income_attr_p` | `n_income_attr_p` | `n_income_attr_p` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `minority_gain` | `minority_gain` | `minority_gain` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `oth_compr_income` | `oth_compr_income` | `oth_compr_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `t_compr_income` | `t_compr_income` | `t_compr_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `compr_inc_attr_p` | `compr_inc_attr_p` | `compr_inc_attr_p` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `compr_inc_attr_m_s` | `compr_inc_attr_m_s` | `compr_inc_attr_m_s` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ebit` | `ebit` | `ebit` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ebitda` | `ebitda` | `ebitda` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `insurance_exp` | `insurance_exp` | `insurance_exp` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `undist_profit` | `undist_profit` | `undist_profit` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `distable_profit` | `distable_profit` | `distable_profit` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `rd_exp` | `rd_exp` | `rd_exp` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `fin_exp_int_exp` | `fin_exp_int_exp` | `fin_exp_int_exp` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `fin_exp_int_inc` | `fin_exp_int_inc` | `fin_exp_int_inc` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `transfer_surplus_rese` | `transfer_surplus_rese` | `transfer_surplus_rese` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `transfer_housing_imprest` | `transfer_housing_imprest` | `transfer_housing_imprest` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `transfer_oth` | `transfer_oth` | `transfer_oth` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `adj_lossgain` | `adj_lossgain` | `adj_lossgain` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `withdra_legal_surplus` | `withdra_legal_surplus` | `withdra_legal_surplus` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `withdra_legal_pubfund` | `withdra_legal_pubfund` | `withdra_legal_pubfund` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `withdra_biz_devfund` | `withdra_biz_devfund` | `withdra_biz_devfund` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `withdra_rese_fund` | `withdra_rese_fund` | `withdra_rese_fund` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `withdra_oth_ersu` | `withdra_oth_ersu` | `withdra_oth_ersu` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `workers_welfare` | `workers_welfare` | `workers_welfare` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `distr_profit_shrhder` | `distr_profit_shrhder` | `distr_profit_shrhder` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `prfshare_payable_dvd` | `prfshare_payable_dvd` | `prfshare_payable_dvd` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `comshare_payable_dvd` | `comshare_payable_dvd` | `comshare_payable_dvd` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `capit_comstock_div` | `capit_comstock_div` | `capit_comstock_div` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `net_after_nr_lp_correct` | `net_after_nr_lp_correct` | `net_after_nr_lp_correct` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `credit_impa_loss` | `credit_impa_loss` | `credit_impa_loss` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `net_expo_hedging_benefits` | `net_expo_hedging_benefits` | `net_expo_hedging_benefits` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `oth_impair_loss_assets` | `oth_impair_loss_assets` | `oth_impair_loss_assets` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `total_opcost` | `total_opcost` | `total_opcost` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `amodcost_fin_assets` | `amodcost_fin_assets` | `amodcost_fin_assets` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `oth_income` | `oth_income` | `oth_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `asset_disp_income` | `asset_disp_income` | `asset_disp_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `continued_net_profit` | `continued_net_profit` | `continued_net_profit` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `end_net_profit` | `end_net_profit` | `end_net_profit` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |

---

# 25. 利润表唯一性与重复

Tushare官方样例本身可能出现：

```text
相同股票
相同公告日期
相同报告期
```

的多行。

因此数据库不能依赖简单自然键强行去重。

RAW：

```text
按_content_hash识别完全重复正文
```

CLEAN：

```text
financial_version_id
```

作为内部主键。

同时建立查询索引：

```text
ts_code
report_period
report_type
company_type
actual_ann_date/ann_date
update_flag
```

完全相同内容可以只保存一次数据正文，但多个采集批次仍保留执行关系。

---

# 26. financial_indicator / 财务指标

官方API：

```text
fina_indicator
```

当前限制：

```text
单次最多100条
2120积分账户按单股票历史采集
```

RAW：

```text
raw.tushare_fina_indicator
```

CLEAN：

```text
clean.financial_indicator
```

---

# 27. 财务指标关键字段

| Tushare | CLEAN | 类型 | 作用 |
|---|---|---|---|
| `ts_code` | `ts_code` | `varchar(16)` | 股票 |
| `ann_date` | `ann_date` | `date` | 公告日期 |
| `end_date` | `report_period` | `date` | 报告期 |
| `update_flag` | `update_flag` | `varchar(8)` | 更新标识 |

内部增加：

```text
financial_indicator_version_id
available_from_trade_date
content_hash
```

由于接口没有`f_ann_date`：

```text
available_from_trade_date
=
ann_date之后第一个有效交易日
```

第一版保持保守的点时正确性。

---

# 28. 财务指标全部数值字段

| Source | RAW | CLEAN | PostgreSQL | 单位处理 | 角色 |
|---|---|---|---|---|---|
| `eps` | `eps` | `eps` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `dt_eps` | `dt_eps` | `dt_eps` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `total_revenue_ps` | `total_revenue_ps` | `total_revenue_ps` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `revenue_ps` | `revenue_ps` | `revenue_ps` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `capital_rese_ps` | `capital_rese_ps` | `capital_rese_ps` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `surplus_rese_ps` | `surplus_rese_ps` | `surplus_rese_ps` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `undist_profit_ps` | `undist_profit_ps` | `undist_profit_ps` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `extra_item` | `extra_item` | `extra_item` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `profit_dedt` | `profit_dedt` | `profit_dedt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `gross_margin` | `gross_margin` | `gross_margin` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `current_ratio` | `current_ratio` | `current_ratio` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `quick_ratio` | `quick_ratio` | `quick_ratio` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `cash_ratio` | `cash_ratio` | `cash_ratio` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `invturn_days` | `invturn_days` | `invturn_days` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `arturn_days` | `arturn_days` | `arturn_days` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `inv_turn` | `inv_turn` | `inv_turn` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ar_turn` | `ar_turn` | `ar_turn` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ca_turn` | `ca_turn` | `ca_turn` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `fa_turn` | `fa_turn` | `fa_turn` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `assets_turn` | `assets_turn` | `assets_turn` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `op_income` | `op_income` | `op_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `valuechange_income` | `valuechange_income` | `valuechange_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `interst_income` | `interst_income` | `interst_income` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `daa` | `daa` | `daa` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ebit` | `ebit` | `ebit` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ebitda` | `ebitda` | `ebitda` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `fcff` | `fcff` | `fcff` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `fcfe` | `fcfe` | `fcfe` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `current_exint` | `current_exint` | `current_exint` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `noncurrent_exint` | `noncurrent_exint` | `noncurrent_exint` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `interestdebt` | `interestdebt` | `interestdebt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `netdebt` | `netdebt` | `netdebt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `tangible_asset` | `tangible_asset` | `tangible_asset` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `working_capital` | `working_capital` | `working_capital` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `networking_capital` | `networking_capital` | `networking_capital` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `invest_capital` | `invest_capital` | `invest_capital` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `retained_earnings` | `retained_earnings` | `retained_earnings` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `diluted2_eps` | `diluted2_eps` | `diluted2_eps` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `bps` | `bps` | `bps` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ocfps` | `ocfps` | `ocfps` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `retainedps` | `retainedps` | `retainedps` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `cfps` | `cfps` | `cfps` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ebit_ps` | `ebit_ps` | `ebit_ps` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `fcff_ps` | `fcff_ps` | `fcff_ps` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `fcfe_ps` | `fcfe_ps` | `fcfe_ps` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `netprofit_margin` | `netprofit_margin` | `netprofit_margin` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `grossprofit_margin` | `grossprofit_margin` | `grossprofit_margin` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `cogs_of_sales` | `cogs_of_sales` | `cogs_of_sales` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `expense_of_sales` | `expense_of_sales` | `expense_of_sales` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `profit_to_gr` | `profit_to_gr` | `profit_to_gr` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `saleexp_to_gr` | `saleexp_to_gr` | `saleexp_to_gr` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `adminexp_of_gr` | `adminexp_of_gr` | `adminexp_of_gr` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `finaexp_of_gr` | `finaexp_of_gr` | `finaexp_of_gr` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `impai_ttm` | `impai_ttm` | `impai_ttm` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `gc_of_gr` | `gc_of_gr` | `gc_of_gr` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `op_of_gr` | `op_of_gr` | `op_of_gr` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ebit_of_gr` | `ebit_of_gr` | `ebit_of_gr` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `roe` | `roe` | `roe` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `roe_waa` | `roe_waa` | `roe_waa` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `roe_dt` | `roe_dt` | `roe_dt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `roa` | `roa` | `roa` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `npta` | `npta` | `npta` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `roic` | `roic` | `roic` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `roe_yearly` | `roe_yearly` | `roe_yearly` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `roa2_yearly` | `roa2_yearly` | `roa2_yearly` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `roe_avg` | `roe_avg` | `roe_avg` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `opincome_of_ebt` | `opincome_of_ebt` | `opincome_of_ebt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `investincome_of_ebt` | `investincome_of_ebt` | `investincome_of_ebt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `n_op_profit_of_ebt` | `n_op_profit_of_ebt` | `n_op_profit_of_ebt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `tax_to_ebt` | `tax_to_ebt` | `tax_to_ebt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `dtprofit_to_profit` | `dtprofit_to_profit` | `dtprofit_to_profit` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `salescash_to_or` | `salescash_to_or` | `salescash_to_or` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ocf_to_or` | `ocf_to_or` | `ocf_to_or` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ocf_to_opincome` | `ocf_to_opincome` | `ocf_to_opincome` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `capitalized_to_da` | `capitalized_to_da` | `capitalized_to_da` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `debt_to_assets` | `debt_to_assets` | `debt_to_assets` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `assets_to_eqt` | `assets_to_eqt` | `assets_to_eqt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `dp_assets_to_eqt` | `dp_assets_to_eqt` | `dp_assets_to_eqt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ca_to_assets` | `ca_to_assets` | `ca_to_assets` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `nca_to_assets` | `nca_to_assets` | `nca_to_assets` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `tbassets_to_totalassets` | `tbassets_to_totalassets` | `tbassets_to_totalassets` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `int_to_talcap` | `int_to_talcap` | `int_to_talcap` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `eqt_to_talcapital` | `eqt_to_talcapital` | `eqt_to_talcapital` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `currentdebt_to_debt` | `currentdebt_to_debt` | `currentdebt_to_debt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `longdeb_to_debt` | `longdeb_to_debt` | `longdeb_to_debt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ocf_to_shortdebt` | `ocf_to_shortdebt` | `ocf_to_shortdebt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `debt_to_eqt` | `debt_to_eqt` | `debt_to_eqt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `eqt_to_debt` | `eqt_to_debt` | `eqt_to_debt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `eqt_to_interestdebt` | `eqt_to_interestdebt` | `eqt_to_interestdebt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `tangibleasset_to_debt` | `tangibleasset_to_debt` | `tangibleasset_to_debt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `tangasset_to_intdebt` | `tangasset_to_intdebt` | `tangasset_to_intdebt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `tangibleasset_to_netdebt` | `tangibleasset_to_netdebt` | `tangibleasset_to_netdebt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ocf_to_debt` | `ocf_to_debt` | `ocf_to_debt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ocf_to_interestdebt` | `ocf_to_interestdebt` | `ocf_to_interestdebt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ocf_to_netdebt` | `ocf_to_netdebt` | `ocf_to_netdebt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ebit_to_interest` | `ebit_to_interest` | `ebit_to_interest` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `longdebt_to_workingcapital` | `longdebt_to_workingcapital` | `longdebt_to_workingcapital` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ebitda_to_debt` | `ebitda_to_debt` | `ebitda_to_debt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `turn_days` | `turn_days` | `turn_days` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `roa_yearly` | `roa_yearly` | `roa_yearly` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `roa_dp` | `roa_dp` | `roa_dp` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `fixed_assets` | `fixed_assets` | `fixed_assets` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `profit_prefin_exp` | `profit_prefin_exp` | `profit_prefin_exp` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `non_op_profit` | `non_op_profit` | `non_op_profit` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `op_to_ebt` | `op_to_ebt` | `op_to_ebt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `nop_to_ebt` | `nop_to_ebt` | `nop_to_ebt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ocf_to_profit` | `ocf_to_profit` | `ocf_to_profit` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `cash_to_liqdebt` | `cash_to_liqdebt` | `cash_to_liqdebt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `cash_to_liqdebt_withinterest` | `cash_to_liqdebt_withinterest` | `cash_to_liqdebt_withinterest` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `op_to_liqdebt` | `op_to_liqdebt` | `op_to_liqdebt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `op_to_debt` | `op_to_debt` | `op_to_debt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `roic_yearly` | `roic_yearly` | `roic_yearly` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `total_fa_trun` | `total_fa_trun` | `total_fa_trun` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `profit_to_op` | `profit_to_op` | `profit_to_op` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_opincome` | `q_opincome` | `q_opincome` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_investincome` | `q_investincome` | `q_investincome` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_dtprofit` | `q_dtprofit` | `q_dtprofit` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_eps` | `q_eps` | `q_eps` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_netprofit_margin` | `q_netprofit_margin` | `q_netprofit_margin` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_gsprofit_margin` | `q_gsprofit_margin` | `q_gsprofit_margin` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_exp_to_sales` | `q_exp_to_sales` | `q_exp_to_sales` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_profit_to_gr` | `q_profit_to_gr` | `q_profit_to_gr` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_saleexp_to_gr` | `q_saleexp_to_gr` | `q_saleexp_to_gr` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_adminexp_to_gr` | `q_adminexp_to_gr` | `q_adminexp_to_gr` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_finaexp_to_gr` | `q_finaexp_to_gr` | `q_finaexp_to_gr` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_impair_to_gr_ttm` | `q_impair_to_gr_ttm` | `q_impair_to_gr_ttm` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_gc_to_gr` | `q_gc_to_gr` | `q_gc_to_gr` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_op_to_gr` | `q_op_to_gr` | `q_op_to_gr` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_roe` | `q_roe` | `q_roe` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_dt_roe` | `q_dt_roe` | `q_dt_roe` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_npta` | `q_npta` | `q_npta` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_opincome_to_ebt` | `q_opincome_to_ebt` | `q_opincome_to_ebt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_investincome_to_ebt` | `q_investincome_to_ebt` | `q_investincome_to_ebt` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_dtprofit_to_profit` | `q_dtprofit_to_profit` | `q_dtprofit_to_profit` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_salescash_to_or` | `q_salescash_to_or` | `q_salescash_to_or` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_ocf_to_sales` | `q_ocf_to_sales` | `q_ocf_to_sales` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_ocf_to_or` | `q_ocf_to_or` | `q_ocf_to_or` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `basic_eps_yoy` | `basic_eps_yoy` | `basic_eps_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `dt_eps_yoy` | `dt_eps_yoy` | `dt_eps_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `cfps_yoy` | `cfps_yoy` | `cfps_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `op_yoy` | `op_yoy` | `op_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ebt_yoy` | `ebt_yoy` | `ebt_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `netprofit_yoy` | `netprofit_yoy` | `netprofit_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `dt_netprofit_yoy` | `dt_netprofit_yoy` | `dt_netprofit_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `ocf_yoy` | `ocf_yoy` | `ocf_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `roe_yoy` | `roe_yoy` | `roe_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `bps_yoy` | `bps_yoy` | `bps_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `assets_yoy` | `assets_yoy` | `assets_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `eqt_yoy` | `eqt_yoy` | `eqt_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `tr_yoy` | `tr_yoy` | `tr_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `or_yoy` | `or_yoy` | `or_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_gr_yoy` | `q_gr_yoy` | `q_gr_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_gr_qoq` | `q_gr_qoq` | `q_gr_qoq` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_sales_yoy` | `q_sales_yoy` | `q_sales_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_sales_qoq` | `q_sales_qoq` | `q_sales_qoq` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_op_yoy` | `q_op_yoy` | `q_op_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_op_qoq` | `q_op_qoq` | `q_op_qoq` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_profit_yoy` | `q_profit_yoy` | `q_profit_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_profit_qoq` | `q_profit_qoq` | `q_profit_qoq` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_netprofit_yoy` | `q_netprofit_yoy` | `q_netprofit_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `q_netprofit_qoq` | `q_netprofit_qoq` | `q_netprofit_qoq` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `equity_yoy` | `equity_yoy` | `equity_yoy` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |
| `rd_exp` | `rd_exp` | `rd_exp` | `double precision` | 保持Tushare返回数值，不做隐式单位换算 | 普通指标 |

---

# 29. 财务指标百分比字段

`fina_indicator`同时包含：

- 金额；
- 每股值；
- 比率；
- 百分比；
- 周转天数；

官方不同字段含义不同。

因此禁止写一个通用规则：

```text
所有fina_indicator浮点数都/100
```

第一版CLEAN保持提供方数值。

字段级单位元数据后续至少区分：

```text
amount
per_share
ratio
percent
days
times
```

---

# 30. 财务指标版本处理

同一：

```text
ts_code + report_period
```

可以存在多条。

不能：

```text
UPSERT覆盖成最后一条
```

必须保留：

```text
ann_date
update_flag
content_hash
```

以及内部版本ID。

---

# 31. RAW主键策略

RAW不使用业务唯一键作为强主键。

统一：

```text
_raw_id
```

作为物理主键。

业务字段建立普通索引。

原因：

```text
RAW必须允许来源修订和重复到达
```

---

# 32. CLEAN主键策略

不同数据类型分别处理。

## 日级快照

```text
stock_daily:
(ts_code, trade_date)

stock_adj_factor:
(ts_code, trade_date)

stock_daily_basic:
(ts_code, trade_date)

stock_limit_price:
(ts_code, trade_date)
```

## 分钟

```text
(ts_code, frequency, trade_time)
```

## 交易日历

```text
(exchange, cal_date)
```

## 财务

使用内部版本ID，不采用报告期覆盖。

---

# 33. available_at规则

| DataItem | available_at |
|---|---|
| `trade_calendar` | 平台获取后即可作为调度事实；历史回测不作为价格信号 |
| `stock_basic` | 当前主数据使用；历史关系不能反推 |
| `stock_daily` | 交易日收盘数据正式发布并清洗完成后 |
| `stock_adj_factor` | Tushare盘前更新后的实际可用时间；历史使用需按采集/规则定义 |
| `stock_daily_basic` | 数据发布并清洗完成后 |
| `stock_suspend` | 按事件日期和实际获得时间 |
| `stock_limit_price` | 当日盘前发布后 |
| `stock_minute` | 对历史库按bar结束时间语义；实时另行设计 |
| `financial_income` | 公告日期后第一个交易日（当前保守规则） |
| `financial_indicator` | 公告日期后第一个交易日（当前保守规则） |

真正运行时会形成：

```text
business_available_at
system_cleaned_at
```

两个概念。

回测取：

```text
max(业务可用时间规则, 数据契约要求)
```

而不能简单使用`_fetched_at`。

---

# 34. RAW到CLEAN的转换版本

每个DataItem至少登记：

```text
field_mapping_version
normalization_version
availability_rule_version
quality_rule_version
```

正式数据记录可以追溯到这些版本。

---

# 35. 字段缺失处理

如果Tushare历史时期某字段不存在：

例如：

```text
daily.ah_vol
daily.ah_amount
```

则：

```text
NULL是合法历史状态
```

不能：

- 填0；
- 用当前值回填；
- 质量失败。

字段开始可用日期进入FieldMetadata。

---

# 36. 新增字段处理

Tushare新增字段时：

```text
CapabilityProbe/SchemaFingerprint发现变化
↓
确认官方含义
↓
更新FieldMappingVersion
↓
Alembic新增列
↓
test验证
↓
prod启用
```

不能让未知字段直接进入CLEAN。

---

# 37. 删除/改名字段处理

来源字段删除或改名：

```text
旧RAW结构版本保留
新RAW结构版本增加
映射层负责兼容
```

CLEAN字段只有业务语义真的变化时才调整。

---

# 38. 索引初步设计

第一阶段只建立真实使用所需索引。

## stock_daily / daily_basic / adj_factor

```text
PRIMARY KEY(ts_code, trade_date)
INDEX(trade_date)
```

## stock_minute

TimescaleDB Hypertable：

```text
time = trade_time
```

查询核心：

```text
ts_code + frequency + time range
```

具体复合索引与chunk间隔必须通过真实分钟样本压测后定，不在本阶段猜。

## financial

```text
INDEX(ts_code, report_period)
INDEX(available_from_trade_date)
```

---

# 39. 不为RAW建立大量重复索引

旧quantStock实测中大量表索引空间占比很高。

新项目RAW只建立：

- 主查询；
- 去重Hash；
- 迁移/清洗批次；

真正需要的索引。

不能对每个字段建索引。

---

# 40. 第一轮开发数据库表

第一轮Alembic至少需要创建：

```text
raw.tushare_trade_cal
raw.tushare_stock_basic
raw.tushare_daily
raw.tushare_adj_factor
raw.tushare_daily_basic
raw.tushare_suspend_d
raw.tushare_stk_limit
raw.tushare_stk_mins
raw.tushare_income
raw.tushare_fina_indicator

clean.trade_calendar
clean.security_master
clean.security_master_history
clean.stock_daily
clean.stock_adj_factor
clean.stock_daily_basic
clean.stock_suspend_event
clean.stock_limit_price
clean.stock_minute
clean.financial_income
clean.financial_indicator
```

---

# 41. 第一轮字段验收

每个接口实现后必须验证：

1. 官方全部需要字段均进入RAW；
2. RAW和官方字段名可一一对账；
3. 日期转换正确；
4. 分钟时区正确；
5. 日线成交量已从手转换为股；
6. 日线成交额已从千元转换为元；
7. 分钟成交量/成交额没有重复换算；
8. daily_basic股本从万股转换为股；
9. daily_basic市值从万元转换为元；
10. NULL没有被误填0；
11. 财务历史版本没有被覆盖；
12. 财务available_from_trade_date符合保守规则；
13. `ah_vol/ah_amount`历史缺失合法；
14. SourceBinding字段结构指纹与数据库映射一致；
15. 所有数据能追溯到RawBatch和CollectRun。

---

# 42. 第二批字段设计

第一轮开发闭环完成后，再按同模板扩展：

```text
balancesheet
cashflow
forecast
express
dividend
fina_audit
fina_mainbz
disclosure_date
股东
公司行为
资金流
融资融券
指数
行业
集合竞价
...
```

不改变本文件定义的：

```text
类型规则
单位规则
版本规则
available_at规则
RAW/CLEAN边界
```

只有接口自身语义不同处增加专用规则。

---

# 43. 当前官方依据

本版字段基线以2026-07-27当前Tushare官方页面为准：

```text
trade_cal:
https://tushare.pro/document/2?doc_id=26

stock_basic:
https://tushare.pro/document/1?doc_id=25

daily:
https://tushare.pro/document/1?doc_id=27

adj_factor:
https://tushare.pro/document/2?doc_id=28

daily_basic:
https://tushare.pro/document/2?doc_id=32

suspend_d:
https://tushare.pro/document/2?doc_id=214

stk_limit:
https://tushare.pro/document/2?doc_id=183

stk_mins:
https://tushare.pro/document/2?doc_id=370

income:
https://tushare.pro/document/2?doc_id=33

fina_indicator:
https://tushare.pro/document/2?doc_id=79
```

---

# 44. 本阶段结论

第一批10个接口的字段与表结构基线确定。

最重要的设计决策：

1. RAW保持Tushare字段，CLEAN使用平台标准契约；
2. 日线和分钟统一成交量为“股”、成交额为“元”；
3. `daily`新增的`ah_vol/ah_amount`正式纳入，历史允许NULL；
4. `daily_basic`股本和市值在CLEAN统一为基础单位；
5. 分钟数据必须把请求中的`frequency`写入正式记录；
6. 分钟时间按Asia/Shanghai解释后存`timestamptz`；
7. 0成交量分钟bar不能自动删除；
8. 财务数据绝不按`ts_code + report_period`覆盖；
9. 财务当前采用“公告日期后第一个交易日”作为保守可用边界；
10. 财务数值没有可靠统一单位依据时不做隐式换算；
11. RAW允许来源修订，物理主键与业务键分离；
12. CLEAN日级事实使用稳定复合主键；
13. 字段映射、单位、可用时间和质量规则全部版本化；
14. 第二批接口沿用相同设计模板扩展。
