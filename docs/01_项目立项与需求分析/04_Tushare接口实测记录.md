# Tushare接口实测记录

> 路线图阶段：P1.2  
> 状态：已确认  
> 探测时间：2026-07-28  
> 探测位置：`svr3`的quantStock1 API容器  
> Tushare SDK：`1.4.29`  
> 探测方式：只读最小请求，不写数据库  
> 原始证据：`evidence/quantstock1_tushare_capability_probe_20260728.jsonl`

## 1. 探测结果摘要

```text
探测总数：19
可调用：17
明确无权限：2
```

“可调用”包含返回空表的请求。空表不能自动解释为业务无数据。

## 2. 逐项记录

| 探测 | 状态 | 行数 | 秒 | 日期范围 | 返回字段 | 错误 |
|---|---|---:|---:|---|---|---|
| `trade_cal_sse` | AVAILABLE | 9 | 0.15 | cal_date_max=20260728；cal_date_min=20260720 | exchange、cal_date、is_open、pretrade_date | — |
| `trade_cal_szse` | AVAILABLE | 9 | 0.13 | cal_date_max=20260728；cal_date_min=20260720 | exchange、cal_date、is_open、pretrade_date | — |
| `trade_cal_bse` | AVAILABLE | 0 | 0.145 | — | exchange、cal_date、is_open、pretrade_date | — |
| `stock_basic_L` | AVAILABLE | 5533 | 0.292 | list_date_max=20260727；list_date_min=19901219 | ts_code、symbol、name、market、exchange、list_status、list_date、delist_date | — |
| `stock_basic_D` | AVAILABLE | 338 | 0.143 | delist_date_max=20260717；delist_date_min=19990712；list_date_max=20220525；list_date_min=19901201 | ts_code、symbol、name、market、exchange、list_status、list_date、delist_date | — |
| `stock_basic_P` | AVAILABLE | 0 | 0.129 | — | ts_code、symbol、name、market、exchange、list_status、list_date、delist_date | — |
| `stock_basic_G` | AVAILABLE | 0 | 0.126 | — | ts_code、symbol、name、market、exchange、list_status、list_date、delist_date | — |
| `daily_20260724` | AVAILABLE | 5526 | 0.425 | trade_date_max=20260724；trade_date_min=20260724 | ts_code、trade_date、open、high、low、close、pre_close、change、pct_chg、vol、amount、ah_vol、ah_amount | — |
| `adj_factor_20260724` | AVAILABLE | 5544 | 0.254 | trade_date_max=20260724；trade_date_min=20260724 | ts_code、trade_date、adj_factor | — |
| `daily_basic_20260724` | AVAILABLE | 5526 | 0.547 | trade_date_max=20260724；trade_date_min=20260724 | ts_code、trade_date、close、turnover_rate、turnover_rate_f、volume_ratio、pe、pe_ttm、pb、ps、ps_ttm、dv_ratio、dv_ttm、total_share、float_share、free_share、total_mv、circ_mv | — |
| `suspend_d_20260724` | AVAILABLE | 5 | 0.116 | trade_date_max=20260724；trade_date_min=20260724 | ts_code、trade_date、suspend_timing、suspend_type | — |
| `stk_limit_page_1` | AVAILABLE | 5800 | 0.248 | trade_date_max=20260724；trade_date_min=20260724 | trade_date、ts_code、up_limit、down_limit | — |
| `stk_limit_page_2` | AVAILABLE | 1907 | 0.201 | trade_date_max=20260724；trade_date_min=20260724 | trade_date、ts_code、up_limit、down_limit | — |
| `stk_mins_current_day` | AVAILABLE | 241 | 1.045 | trade_time_max=2026-07-24 15:00:00；trade_time_min=2026-07-24 09:30:00 | ts_code、trade_time、close、open、high、low、vol、amount | — |
| `stk_mins_2009_probe` | AVAILABLE | 1205 | 0.334 | trade_time_max=2009-01-09 15:00:00；trade_time_min=2009-01-05 09:30:00 | ts_code、trade_time、close、open、high、low、vol、amount | — |
| `income_standard` | AVAILABLE | 6 | 0.116 | ann_date_max=20260425；ann_date_min=20250315；end_date_max=20260331；end_date_min=20241231；f_ann_date_max=20260425；f_ann_date_min=20250315 | ts_code、ann_date、f_ann_date、end_date、report_type、comp_type、basic_eps、total_revenue、revenue、total_profit、n_income、update_flag | — |
| `fina_indicator_standard` | AVAILABLE | 6 | 0.111 | ann_date_max=20260425；ann_date_min=20250419；end_date_max=20260331；end_date_min=20250331 | ts_code、ann_date、end_date、eps、dt_eps、roe、roa、netprofit_margin、grossprofit_margin、debt_to_assets、update_flag | — |
| `income_vip` | UNAVAILABLE | - | 0.134 | — | — | 抱歉，您没有接口(income_vip)访问权限，权限的具体详情访问：https://tushare.pro/document/1?doc_id=108。 |
| `fina_indicator_vip` | UNAVAILABLE | - | 0.112 | — | — | 抱歉，您没有接口(fina_indicator_vip)访问权限，权限的具体详情访问：https://tushare.pro/document/1?doc_id=108。 |

## 3. 关键证据

### 3.1 交易日历

```text
SSE：9行
SZSE：9行
BSE：0行
```

BSE请求没有报错，但返回0行。结论只能是“当前参数未取得BSE独立日历”，不能解释为BSE在该期间全部休市。

### 3.2 股票范围

```text
L：5533
D：338
P：0
G：0
```

只采默认L状态会漏掉退市股票。证券主数据初始化和更新必须显式覆盖L、D、P、G。

### 3.3 日频数据

2026-07-24：

```text
daily：5526
adj_factor：5544
daily_basic：5526
suspend_d：5
```

各接口数量不同是正常可能，不应建立绝对相等规则。

### 3.4 涨跌停价格分页

```text
offset=0：5800
offset=5800：1907
合计：7707
```

该结果证明`stk_limit`真实支持offset分页，也证明只取第一页会静默漏数。当前数据库中`supports_pagination=false`与实测冲突。

### 3.5 历史分钟

```text
000001.SZ
2026-07-24：241行
2009-01-05至2009-01-09：1205行
```

1205行对应5个完整交易日，每日241条。当前Token至少可以取得该股票2009-01-05起的1分钟数据。

该结果不能外推为：

```text
所有股票都从2009年有数据
所有市场都从2009年有数据
所有交易日都固定241条
BSE历史分钟从2009年开始
```

### 3.6 财务接口

```text
income：可用，6行
fina_indicator：可用，6行
income_vip：无权限
fina_indicator_vip：无权限
```

当前采集设计必须使用普通逐股票接口，不能依赖VIP全市场接口。

## 4. 探测错误原文

```text
income_vip：
抱歉，您没有接口(income_vip)访问权限。

fina_indicator_vip：
抱歉，您没有接口(fina_indicator_vip)访问权限。
```

## 5. 证据完整性

原始JSONL：

```text
SHA256：
80E124097B0FEBF201B9962025BFA42BFD1F3DC871611446CBA4F4DE0658771C
```

本记录只表达2026-07-28探测时的真实结果。Tushare权限、接口规则和数据内容可能变化，后续只有在新增数据域、权限报错或规则变化时才重新做针对性验证，不进行无边界全接口扫描。
