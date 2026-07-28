# Tushare数据能力矩阵

> 路线图阶段：P1.2  
> 状态：已确认  
> 形成日期：2026-07-29  
> 说明：本矩阵区分“真实可用”“历史记录具备”“官方候选”“明确不可用”，避免把官方存在误写成当前Token可用。

## 1. 状态定义

| 状态 | 含义 | 是否可进入首批设计 |
|---|---|---|
| A-实测可用 | 当前Token已完成真实调用 | 可以 |
| B-历史记录具备 | 项目资源记录为已购买，但本次未复核 | 只能预留，正式启用前验证 |
| C-官方候选 | 官方存在接口，当前Token未实测 | 不可以 |
| D-实测无权限 | 当前Token明确返回权限错误 | 不可以 |
| E-证据不足 | 接口名称、许可或行为不明确 | 不可以 |

## 2. 首批核心能力

| 领域 | 数据项 | API | 状态 | 当前实测 | 采集形态 | 首批结论 |
|---|---|---|---|---|---|---|
| 基础 | 交易日历 | `trade_cal` | A | SSE/SZSE各9行；BSE 0行 | 交易所+日期范围 | SSE/SZSE可用，BSE独立日历不可确认 |
| 基础 | 股票基础信息 | `stock_basic` | A | L 5533、D 338、P/G 0 | 状态+交易所 | 必须覆盖L/D/P/G |
| 行情 | A股日线 | `daily` | A | 20260724共5526行 | 按交易日全市场 | 首批正式数据 |
| 行情 | 复权因子 | `adj_factor` | A | 20260724共5544行 | 按交易日/股票 | 保存原始因子和版本 |
| 行情 | 每日指标 | `daily_basic` | A | 20260724共5526行 | 按交易日全市场 | 首批正式数据 |
| 事件 | 停复牌 | `suspend_d` | A | 20260724共5行 | 按交易日/股票 | 事件保存并次日复核 |
| 行情 | 涨跌停价格 | `stk_limit` | A | 5800+1907行 | offset分页 | 必须分页 |
| 分钟 | A股历史分钟 | `stk_mins` | A | 20260724为241行；2009五日1205行 | 股票+频率+时间窗口 | 具备独立权限 |
| 财务 | 利润表 | `income` | A | 单股票6行 | 逐股票+报告期 | 无VIP，只能逐股 |
| 财务 | 财务指标 | `fina_indicator` | A | 单股票6行 | 逐股票+报告期 | 单次100行保护 |

## 3. 独立权限能力

| 数据项 | API/名称 | 状态 | 官方限制 | 当前结论 |
|---|---|---|---|---|
| 开盘集合竞价 | `stk_auction_o` | B | 10000行/次，独立权限 | 历史资源记录已购买，当前未复核 |
| 收盘集合竞价 | `stk_auction_c` | B | 10000行/次，独立权限 | 历史资源记录已购买，当前未复核 |
| 集合竞价权限项 | `stk_auction` | E | 当前官方独立接口证据不足 | 不建立运行依赖 |
| A股历史分钟 | `stk_mins` | A | 8000行/次，500次/分钟，2009年起 | 当前真实可用 |
| A股实时分钟 | 实时分钟接口 | C | 独立权限 | 当前不作为已有资源 |
| 指数历史分钟 | `idx_mins` | C | 8000行/次，独立权限 | 候选 |
| 申万历史分钟 | `sw_mins` | C | 5000行/次，独立权限 | 候选 |

## 4. 扩展数据域矩阵

| 数据域 | 代表接口 | 当前状态 | 首批处理 |
|---|---|---|---|
| 指数基础与行情 | `index_basic`、`index_daily`、`index_weight` | C | 数据目录预留，不实现 |
| 申万行业 | `index_classify`、`index_member_all`、`sw_daily` | C | 数据目录预留，不实现 |
| 同花顺板块 | `ths_index`、`ths_member`、`ths_daily` | C | 数据目录预留，不实现 |
| 东财板块 | `dc_index`、`dc_member`、`dc_daily` | C | 数据目录预留，不实现 |
| 通达信板块 | `tdx_index`、`tdx_member`、`tdx_daily` | C | 数据目录预留，不实现 |
| 个股资金流向 | `moneyflow`、`moneyflow_ths`、`moneyflow_dc` | C | 后续按策略需求验证 |
| 北向持股与成交 | `hk_hold`、`hsgt_top10`等 | C | 后续按策略需求验证 |
| 板块资金流向 | THS/DC资金流接口 | C | 后续按策略需求验证 |
| 龙虎榜 | `top_list`、`top_inst` | C | 后续按策略需求验证 |
| 大宗交易 | `block_trade` | C | 后续按策略需求验证 |
| 融资融券 | `margin`、`margin_detail`、`margin_secs` | C | 后续按策略需求验证 |
| 股东数据 | `top10_holders`、`stk_holdernumber`等 | C | 后续按策略需求验证 |
| 公司行为 | `repurchase`、`share_float`、`dividend` | C | 后续按策略需求验证 |
| 业绩事件 | `forecast`、`express`、`disclosure_date` | C | 后续按策略需求验证 |
| 实时行情 | `rt_k`、实时分钟接口 | C | P12实时桥接阶段处理 |

## 5. 明确不可用能力

| 数据项 | API | 状态 | 实测错误 |
|---|---|---|---|
| 全市场利润表VIP | `income_vip` | D | 当前Token没有接口访问权限 |
| 全市场财务指标VIP | `fina_indicator_vip` | D | 当前Token没有接口访问权限 |

资产负债表VIP、现金流量表VIP等其他VIP接口未调用，不从两个已失败接口外推绝对结论；在购买5000积分级能力前统一按不可作为当前前提处理。

## 6. 关键限制矩阵

| API | 权限方式 | 单次上限 | 频率依据 | 更新时间 | 截断处理 |
|---|---|---:|---|---|---|
| `stock_basic` | 2000积分 | 6000 | 接口50次/分钟 | 不定期 | 状态+交易所拆分 |
| `daily` | 积分 | 6000 | 账户与接口较小值 | 15:00—16:00 | 命中6000拆分 |
| `adj_factor` | 2000积分 | 项目登记6000 | 账户与接口较小值 | 9:15—9:20 | 按日/股票拆分 |
| `daily_basic` | 2000积分 | 6000 | 账户与接口较小值 | 15:00—17:00 | 命中6000拆分 |
| `stk_limit` | 2000积分 | 5800 | 账户与接口较小值 | 约8:40 | offset分页 |
| `stk_mins` | 独立权限 | 8000 | 500次/分钟 | 17:00—21:00 | 动态缩小时间窗口 |
| `fina_indicator` | 2000积分 | 100 | 账户与接口较小值 | 随公告 | 缩小报告期窗口 |
| `stk_auction_o` | 独立权限 | 10000 | 500次/分钟 | 每日更新 | 命中10000继续拆分 |
| `stk_auction_c` | 独立权限 | 10000 | 500次/分钟 | 盘后更新 | 命中10000继续拆分 |

## 7. 字段口径矩阵

| 数据 | 源字段 | 源单位 | CLEAN字段 | CLEAN单位 |
|---|---|---|---|---|
| 日线 | `vol` | 手 | `volume_share` | 股 |
| 日线 | `amount` | 千元 | `amount_cny` | 元 |
| 分钟 | `vol` | 股 | `volume_share` | 股 |
| 分钟 | `amount` | 元 | `amount_cny` | 元 |
| 复权 | `adj_factor` | 因子 | `adj_factor` | 原值 |
| 每日指标 | `total_share`等 | 按官方字段定义 | 标准字段 | 逐字段登记 |
| 财务 | 报表金额字段 | 按官方字段定义 | 标准财务字段 | 逐字段登记 |

## 8. 数据目录登记要求

每个接口必须登记：

```text
api_name
permission_type
required_points
entitlement_code
max_rows_per_request
account_calls_per_minute
api_calls_per_minute
effective_calls_per_minute
max_calls_per_day
supports_pagination
pagination_mode
split_dimension
history_start
update_time_rule
license_scope
capability_status
last_probe_at
last_probe_status
```

当前矩阵是设计输入，不等于自动修改数据库。由OpenCode依据本矩阵设计并实施元数据修正。
