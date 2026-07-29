---
requirements_format: ears
module_code: CORE
work_item_id: WI-0001
base_spec_version: PSV-0001
covers: [S2-001, S2-002, S2-005, S2-006, S2-009, S2-010, S2-011, S2-012, S2-013, S2-014, S2-015, S2-016, S2-017, S2-018, S2-019, S2-020, S2-021, S2-022, S2-023, S2-024, S2-025]
---

# Requirements: 第2步数据底座 (S2-001—S2-025)

## 1. 简介

本文档定义 quantStock1 第 2 步数据底座开发的业务需求，覆盖 P3（数据源与采集）、P4（数据治理与分层存储）、P5（DataContext 与统一查询）三个阶段。

业务目标：把当前已运行的"数据采集 + RAW + CLEAN + 质量"链路升级为**可追溯、可复现、防未来、可恢复**的研究级数据底座，使上层研究、策略、回测、风控、信号模块只需通过 DataContext 与统一查询 API 即可获得一致且正确的历史数据视图。

本 WI 的范围严格限定于 S2-001—S2-025 任务清单，不含 Feature/Strategy/Backtest/Signal/UserDecision 等未来阶段对象。

权威输入：
- `docs/00_项目管理/08_第2步数据底座统一实施任务书.md`
- `docs/06_测试验证/10_第2步数据底座验收计划.md`
- `docs/02_可行性研究与资源评估/03_核心业务对象与生命周期.md`
- `docs/02_可行性研究与资源评估/08_非功能需求与服务目标.md`
- `.specforge/work-items/WI-0001/intake.md`
- `.specforge/work-items/WI-0001/trigger_result.json`

### 1.1 In Scope

- 10 个 DataItem 元数据补齐（S2-002）
- 采集状态机完整性、run_type 统一、幂等键（S2-005、S2-006）
- RAW 来源证据、CLEAN 版本与可用时间、复权分层、财务修订（S2-009、S2-010、S2-011）
- 质量发布门禁、DataGap 闭环（S2-012、S2-013）
- lineage_edge 基础表、AuditEvent 扩展（S2-014、S2-015）
- DataContext、DataSnapshot、防未来函数、统一查询 API（S2-016—S2-019）
- server-test 独立环境、迁盘脚本、备份恢复脚本（S2-020—S2-023）
- 单元、集成、Alembic、契约、故障、幂等、防未来、Lineage、备份恢复、真实数据测试（S2-024、S2-025）

### 1.2 Out of Scope

- Feature / Analysis / StockPool / Strategy / BacktestRun / RiskEvaluation / Signal / UserDecision / Order / Fill 等未来阶段对象（属于第 3 步及以后）
- 旧 quantStock 在线依赖（仅可作为只读迁移来源）
- 全市场分钟数据扩展（在迁盘、压缩、归档和恢复完成前禁止）
- 实时分钟行情（V1 仅 T+1 或批量）
- Celery / Redis 核心状态 / Kafka / RabbitMQ / Kubernetes / 微服务拆分
- 用户授权范围之外的 stable 数据库写入、迁盘、删卷、开端口等操作

### 1.3 硬约束（贯穿全文）

1. 所有数据库结构变化进入新 Alembic 迁移（从 0013 起，编号由实施时仓库实际状态决定）
2. 数据库功能必须使用真实 PostgreSQL 16 / TimescaleDB 2.28.3 验证，不得仅用 Mock / SQLite / 内存对象
3. 不引入 Celery、Redis 核心状态、Kafka、RabbitMQ、微服务或 Kubernetes
4. API 不执行长任务
5. DataContext 不读取 RAW
6. 不修改已执行的历史迁移
7. 不提交、不推送
8. 不自动修改 stable 数据库、端口、数据卷或网络
9. stable 不可逆操作必须生成完整可复制命令由用户执行

## 2. 术语表

| 术语 | 定义 |
|---|---|
| DataItem | 平台长期管理的一种业务数据（如 stock_daily），不是外部接口，也不是物理表 |
| DataSource | 外部或内部数据来源（当前正式为 Tushare） |
| SourceBinding | 某个 DataItem 如何从某个 DataSource 取得 |
| StoragePolicy | DataItem 在 RAW/CLEAN/归档/压缩/备份中的存储规则 |
| CollectTask | 明确、有限、可验收的采集业务目标 |
| CollectRun | CollectTask 的一次真实执行 |
| RequestSlice | CollectTask 内可独立执行和恢复的最小业务范围 |
| SliceAttempt | 一次真实外部请求 |
| run_type | 采集业务类型枚举：INITIALIZE / INCREMENTAL / BACKFILL / REPAIR / RETRY |
| RawBatch | 一次或一组来源请求形成的原始数据集合 |
| CleanBatch | RAW 经过指定规则版本后形成的标准化结果批次 |
| available_at | 某条 CLEAN 数据可被研究/回测读取的时间点 |
| as_of_time | 研究或回测模拟所处的业务时间点 |
| available_at_cutoff | DataContext 查询时设定的可用时间上限 |
| DataSnapshot | 为研究和回测复现而冻结的正式数据视图 |
| DataContext | 一次查询或计算的语义值对象，包含 as_of_time、范围、频率、复权策略、质量策略等 |
| 复权 | 价格调整机制；分为未复权行情、复权因子、动态复权计算三层 |
| DataGap | 已确认的数据缺口 |
| lineage_edge | 数据血缘基础表中的边记录，描述 RAW→CLEAN→QUALITY 之间的直接关系 |
| LOST | Worker/Run/Slice 失联状态；不等于正常业务失败 |
| Lease | Worker 对 Slice 的执行租约；过期后可被其他 Worker 接管 |
| 防未来函数 | 量化系统不允许使用在 as_of_time 时点尚不可得的数据 |
| server-test | 与 stable 完全隔离的独立测试环境 |
| stable | 正式运行环境 |

## 3. 需求追溯映射（S2 → REQ）

| S2 任务 | 原 REQ | 细粒度 REQ |
|---|---|---|
| S2-001 基线与差距 | （C1 已完成） | — |
| S2-002 DataItem 元数据补齐 | REQ-001 | REQ-CORE-001 |
| S2-005 状态机 LOST/Lease | REQ-002 | REQ-CORE-002 |
| S2-006 run_type + 幂等键 | REQ-002 | REQ-CORE-003、REQ-CORE-004 |
| S2-009 RAW 来源证据 | REQ-003 | REQ-CORE-005 |
| S2-010 CLEAN 基础属性 | REQ-004 | REQ-CORE-006 |
| S2-011 复权 + 财务修订 + available_at | REQ-004 | REQ-CORE-007、REQ-CORE-008、REQ-CORE-009 |
| S2-012 FAILED 门禁 | REQ-005 | REQ-CORE-010 |
| S2-013 WARNING + DataGap | REQ-005 | REQ-CORE-011、REQ-CORE-012 |
| S2-014 lineage_edge | REQ-006 | REQ-CORE-013 |
| S2-015 AuditEvent | REQ-007 | REQ-CORE-014、REQ-CORE-015 |
| S2-016 DataContext | REQ-008 | REQ-CORE-016、REQ-CORE-017、REQ-CORE-018 |
| S2-017 DataSnapshot | REQ-009 | REQ-CORE-019、REQ-CORE-020 |
| S2-018 防未来 | REQ-010 | REQ-CORE-021、REQ-CORE-022、REQ-CORE-023、REQ-CORE-024 |
| S2-019 统一查询 API | REQ-011 | REQ-CORE-025、REQ-CORE-026、REQ-CORE-027、REQ-CORE-028 |
| S2-020 迁盘脚本 | REQ-013 | REQ-CORE-029 |
| S2-021 分钟压缩归档 | REQ-014 | REQ-CORE-030 |
| S2-022 server-test | REQ-012 | REQ-CORE-031 |
| S2-023 备份恢复 | REQ-014 | REQ-CORE-032、REQ-CORE-033 |
| S2-024 测试覆盖 | REQ-015 | REQ-CORE-034 |
| S2-025 真实数据验收 | REQ-015 | REQ-CORE-035 |

## 4. 需求

### A. 数据目录与采集（REQ-CORE-001 — REQ-CORE-005）

---

#### REQ-CORE-001 DataItem 元数据补齐

**用户故事**：作为研究/回测使用者，我希望 10 个首批 DataItem 的 business_time_field、history_start、update_mode、retention_class 等元数据完整准确，以便系统能按业务时间正确推进水位、按更新模式正确触发采集、按保留级别正确归档。

**类型**：MUST

**覆盖**：S2-002

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 为 trade_calendar、stock_basic、stock_daily、stock_adj_factor、stock_daily_basic、stock_suspend、stock_limit_price、stock_minute、financial_income、financial_indicator 共 10 个 DataItem 各自填充 business_time_field、history_start、update_mode、retention_class、frequency、grain、availability_rule、schema_version、quality_policy_ref 字段。
2. [Ubiquitous] THE 系统 SHALL 拒绝将任何未通过真实接口实测的扩展能力标记为 capability_status=AVALABLE；未实测的 SourceBinding 能力必须保持 UNKNOWN 或对应的受限状态。
3. [Event-driven] WHEN 任一 DataItem 的元数据被更新时，THE 系统 SHALL 在新 Alembic 迁移或种子文件中记录变更并保留变更前的快照（不得直接覆盖历史种子且无审计）。
4. [Unwanted-behavior] IF business_time_field 或 update_mode 缺失或为空字符串，THEN THE 系统 SHALL 在 DataItem 进入 ACTIVE 状态前拒绝并返回明确错误。

**basis_refs**: [INTAKE-14-28, TASKBOOK-§5, NFR-§3.1]

**required_evidence**:
- EVREQ-1: 10 个 DataItem 的种子/迁移记录，每个 DataItem 至少包含上述 9 个字段且非空
- EVREQ-2: 字段值与真实接口实测结论一致的对照表
- EVREQ-3: 状态机拒绝空元数据的集成测试日志

**not_done_when**:
- 仅修改了种子文件但未在新迁移中体现
- 元数据填充了"待定"或"未知"占位值
- capability_status 被无依据地标记为 AVAILABLE

---

#### REQ-CORE-002 采集对象状态机 LOST 与 Lease 超时恢复

**用户故事**：作为运维人员，我希望 Worker 心跳中断或 Lease 超时后系统能识别失联并自动恢复，以便任务不会无限挂起或重复执行。

**类型**：MUST

**覆盖**：S2-005

**验收标准**：
1. [State-driven] WHILE Worker 心跳中断超过 <worker_lost_threshold: 10 分钟>（可配置），THE 系统 SHALL 把 WorkerRegistry 状态置为 LOST 并把其持有的 RUNNING 状态 CollectRun / RequestSlice 标记为可恢复。
2. [State-driven] WHILE Slice 的 Lease 过期且未收到心跳续约，THE 系统 SHALL 允许其他 ONLINE Worker 接管该 Slice，且接管过程不得覆盖原 Worker 已写入的 SliceAttempt。
3. [Event-driven] WHEN LOST 或 Lease 过期被识别后，THE 系统 SHALL 在 <recovery_sla: 15 分钟>（可配置）内进入自动恢复、重试或明确人工处置状态。
4. [Unwanted-behavior] IF 终态 CollectRun/SliceAttempt（SUCCEEDED / FAILED / CANCELLED）被尝试改回 RUNNING，THEN THE 系统 SHALL 拒绝该转换并审计记录。
5. [Event-driven] WHEN Scheduler 重启时，THE 系统 SHALL 不重复创建同一幂等任务。

**basis_refs**: [TASKBOOK-§6、§8, NFR-§5]

**required_evidence**:
- EVREQ-1: Worker LOST 触发的集成测试（心跳中断后 10 分钟内状态转换）
- EVREQ-2: Lease 过期被另一 Worker 接管的测试日志
- EVREQ-3: 终态不可逆的约束测试

**not_done_when**:
- 测试仅用 Mock 模拟心跳而未在真实 PG/TimescaleDB 上验证
- 终态被允许改回 RUNNING

---

#### REQ-CORE-003 run_type 统一枚举

**用户故事**：作为数据治理者，我希望所有 CollectTask 使用统一的 run_type 枚举，以便按业务类型筛选、统计和审计。

**类型**：MUST

**覆盖**：S2-006

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 把 CollectTask.run_type 收敛为枚举集合 {INITIALIZE, INCREMENTAL, BACKFILL, REPAIR, RETRY}；不允许出现枚举外的字符串值。
2. [Event-driven] WHEN 创建新 CollectTask 时，THE 系统 SHALL 校验 run_type 属于上述枚举，否则拒绝创建。
3. [State-driven] WHILE 历史遗留 CollectTask 存在非枚举 run_type 值，THE 系统 SHALL 通过数据修复迁移将其映射到合法枚举值，并在 AuditEvent 中记录映射前后值。
4. [Unwanted-behavior] IF run_type 为空或非法字符串，THEN THE 系统 SHALL 拒绝持久化并返回稳定错误码。

**basis_refs**: [TASKBOOK-§4.C2, COREOBJ-§7.2]

**required_evidence**:
- EVREQ-1: run_type CHECK 约束在迁移中存在的证据
- EVREQ-2: 非法值被拒绝的集成测试
- EVREQ-3: 历史数据修复迁移日志（含前后对照）

**not_done_when**:
- 仅在应用层校验而 DB 无 CHECK 约束
- 历史非枚举值被静默丢弃而非映射

---

#### REQ-CORE-004 采集幂等键

**用户故事**：作为运维人员，我希望相同业务目标的重跑不会产生不可控重复，以便保证数据一致性。

**类型**：MUST

**覆盖**：S2-006

**验收标准**：
1. [Event-driven] WHEN 同一 (data_item_id, business_scope, run_type, business_time_window) 的 CollectTask 被重复创建时，THE 系统 SHALL 通过幂等键阻止重复正文落库。
2. [Event-driven] WHEN 同一请求参数哈希的 SliceAttempt 被重复提交时，THE 系统 SHALL 复用已存在的 RAW 结果而非重新写入新 RawBatch。
3. [Unwanted-behavior] IF 幂等键冲突且业务要求强制重跑，THEN THE 系统 SHALL 要求显式 RETRY 或 RERUN 标识，并生成新 Run/Attempt 而非覆盖旧记录。
4. [Ubiquitous] THE 系统 SHALL 保证幂等重跑产生的不可控重复业务正文行数为 0。

**basis_refs**: [TASKBOOK-§8, NFR-§5]

**required_evidence**:
- EVREQ-1: 幂等键约束（唯一索引或应用层幂等表）的迁移证据
- EVREQ-2: 重复创建被阻止的测试日志
- EVREQ-3: 强制重跑路径生成新 Run/Attempt 而非覆盖的证据

**not_done_when**:
- 仅靠应用层 if-exists 检查而无 DB 约束
- 重跑覆盖了旧 Attempt 记录

---

#### REQ-CORE-005 RAW 批次来源证据完整性

**用户故事**：作为数据审计者，我希望任一 RAW 记录都能完整回查其请求链路，以便证明数据来源真实、可追溯。

**类型**：MUST

**覆盖**：S2-009

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 保证任一 RawBatch 可通过外键或引用链回查到 DataSource、SourceBinding、CollectTask、CollectRun、RequestSlice、SliceAttempt 共 7 个上游对象。
2. [Ubiquitous] THE 系统 SHALL 在每个 RawBatch 上记录 request_hash（请求参数哈希）、record_count（返回行数）、fetched_at（请求时间）、content_hash（内容哈希）、schema_fingerprint 共 5 个证据字段。
3. [Unwanted-behavior] IF RawBatch 缺少上述任一字段或引用，THEN THE 系统 SHALL 拒绝将该 RawBatch 置为 ACCEPTED。
4. [Event-driven] WHEN 任一 RAW 记录被查询时，THE 系统 SHALL 能在单次追溯查询内返回其完整来源链（p95 ≤ 3 秒）。

**basis_refs**: [TASKBOOK-§6.RAW, NFR-§3.1、§6]

**required_evidence**:
- EVREQ-1: 7 跳引用链的查询 SQL 与执行计划
- EVREQ-2: 5 个证据字段的迁移与种子证据
- EVREQ-3: 缺失字段被拒绝的集成测试

**not_done_when**:
- 引用链断裂或可空
- 任一证据字段可被静默置空

---

### B. CLEAN 与质量（REQ-CORE-006 — REQ-CORE-012）

---

#### REQ-CORE-006 CLEAN 版本与可用时间基础属性

**用户故事**：作为研究/回测使用者，我希望 CLEAN 数据具备业务主键、业务时间、available_at、规则版本、Schema 版本、CleanBatch、质量状态、来源关系共 8 类属性，以便我能正确按时间点读取数据并复现结果。

**类型**：MUST

**覆盖**：S2-010

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 保证任一 CLEAN 记录具备 business_key、business_time、available_at、clean_rule_version、schema_version、clean_batch_id、quality_status、source_relation 共 8 类属性。
2. [Event-driven] WHEN CLEAN 记录进入发布状态时，THE 系统 SHALL 校验 8 类属性全部非空且引用有效，否则拒绝发布。
3. [State-driven] WHILE 同一 business_key 存在多个版本，THE 系统 SHALL 通过 valid_from / valid_to / is_current 字段表达有效区间，且 is_current=true 的版本在同一 business_key 下唯一。
4. [Unwanted-behavior] IF 任一属性缺失或引用失效，THEN THE 系统 SHALL 把 CleanBatch 置为 QUARANTINED 或 FAILED 而非发布。

**basis_refs**: [TASKBOOK-§6.CLEAN, COREOBJ-§8.4]

**required_evidence**:
- EVREQ-1: 14 张 CLEAN 类型化表均含 8 类属性的迁移证据
- EVREQ-2: is_current 唯一约束（部分唯一索引）的测试
- EVREQ-3: 缺失属性被拒绝发布的集成测试

**not_done_when**:
- 仅有 CleanBatch 而无记录级版本字段
- available_at 默认等于 business_time 而无独立来源

---

#### REQ-CORE-007 复权分层

**用户故事**：作为量化研究者，我希望未复权行情、复权因子、动态复权计算三者分离存储，以便我在不同研究场景下选择不同复权口径而不互相污染。

**类型**：MUST

**覆盖**：S2-011

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 在 CLEAN 层独立存储 stock_daily（未复权行情）与 stock_adj_factor（复权因子）两类数据，不得将复权因子合并进行情表。
2. [Event-driven] WHEN 上层请求复权口径时，THE 系统 SHALL 通过 DataContext.adjustment_policy 在查询时动态计算前复权或后复权，而非预计算覆盖原始未复权值。
3. [Unwanted-behavior] IF 复权因子缺失或断点，THEN THE 系统 SHALL 在查询结果中标记 quality_status=WARNING 或拒绝返回而非伪造连续价格。
4. [Ubiquitous] THE 系统 SHALL 保证未复权行情记录的内容不被任何复权计算改写。

**basis_refs**: [TASKBOOK-§6.复权, NFR-§3.4]

**required_evidence**:
- EVREQ-1: stock_daily 与 stock_adj_factor 表分离的迁移证据
- EVREQ-2: 动态复权计算函数及其单测
- EVREQ-3: 复权因子断点被标记/拒绝的测试

**not_done_when**:
- 行情表中已混入复权后价格
- 复权计算覆盖了未复权原值

---

#### REQ-CORE-008 财务修订历史版本保留

**用户故事**：作为回测研究者，我希望财务数据的修订历史被多版本保留而非覆盖，以便我能复现任一历史时点的真实可用财务视图。

**类型**：MUST

**覆盖**：S2-011

**验收标准**：
1. [Event-driven] WHEN 来源发布同一报告期（如 2025Q3）的修订数据时，THE 系统 SHALL 创建新 CleanRecordVersion 而非 UPDATE 已有记录。
2. [Ubiquitous] THE 系统 SHALL 在每个财务 CLEAN 记录上保留 report_period、announce_time、available_at、revision_version、valid_from、valid_to、source_version 共 7 个版本字段。
3. [State-driven] WHILE 查询指定 as_of_time 的财务数据时，THE 系统 SHALL 仅返回 valid_from ≤ as_of_time 且 available_at ≤ as_of_time_cutoff 的版本。
4. [Unwanted-behavior] IF 实现尝试通过 UPDATE/DELETE 覆盖已发布财务版本，THEN THE 系统 SHALL 拒绝并审计。

**basis_refs**: [TASKBOOK-§6.财务, NFR-§3.3, COREOBJ-§4.4]

**required_evidence**:
- EVREQ-1: 同一报告期多版本共存的集成测试日志
- EVREQ-2: 时点查询返回正确版本的测试
- EVREQ-3: 覆盖尝试被拒绝的约束测试

**not_done_when**:
- 修订数据通过 UPDATE 覆盖
- 缺少 announce_time 或 revision_version

---

#### REQ-CORE-009 CLEAN 回测时间约束（available_at ≤ as_of_time）

**用户故事**：作为回测研究者，我希望回测读取 CLEAN 数据时严格只读 available_at ≤ as_of_time 的版本，以便避免未来函数污染。

**类型**：MUST

**覆盖**：S2-011

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 在所有回测/研究路径的 CLEAN 查询中强制附加 `available_at <= as_of_time` 条件。
2. [Event-driven] WHEN DataContext 设定 as_of_time 与 available_at_cutoff 时，THE 系统 SHALL 取二者中较小值作为查询上限。
3. [Unwanted-behavior] IF 任一查询路径绕过 available_at 约束读取未来数据，THEN THE 系统 SHALL 在防未来测试中被识别为失败。
4. [Ubiquitous] THE 系统 SHALL 在已知未来函数数量上保持为 0。

**basis_refs**: [TASKBOOK-§6.财务, NFR-§3.1]

**required_evidence**:
- EVREQ-1: DataContext/查询层强制附加约束的代码与测试
- EVREQ-2: 防未来测试套件全部通过的日志

**not_done_when**:
- 仅在文档要求而代码未强制
- 存在任一未来函数读取路径

---

#### REQ-CORE-010 FAILED 数据发布阻断

**用户故事**：作为数据治理者，我希望 quality_status=FAILED 的 CLEAN 数据不能发布到正式 DataSnapshot，以便保证研究输入的数据质量底线。

**类型**：MUST

**覆盖**：S2-012

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 拒绝把 quality_status=FAILED 的 CLEAN 记录纳入任何 READY 状态的 DataSnapshot。
2. [Event-driven] WHEN DataSnapshot 构建过程遇到 FAILED 记录时，THE 系统 SHALL 跳过并记录 skipped_failed_count，不得静默包含。
3. [Unwanted-behavior] IF 实现尝试通过质量豁免（WAIVED）绕过 FAILED 阻断，THEN THE 系统 SHALL 要求明确批准人、原因并审计，且豁免后记录仍须可识别。
4. [Ubiquitous] THE 系统 SHALL 保证未通过质量门禁直接发布的记录数为 0。

**basis_refs**: [TASKBOOK-§6.质量, NFR-§3.1]

**required_evidence**:
- EVREQ-1: FAILED 记录被排除的集成测试
- EVREQ-2: skipped_failed_count 字段的迁移与日志
- EVREQ-3: WAIVED 路径审计记录的测试

**not_done_when**:
- FAILED 记录可被默认发布
- WAIVED 无审计

---

#### REQ-CORE-011 WARNING 发布策略

**用户故事**：作为数据治理者，我希望 quality_status=WARNING 的 CLEAN 数据是否发布由可配置的质量策略决定，以便在不同研究场景下平衡覆盖度与严格度。

**类型**：MUST

**覆盖**：S2-013

**验收标准**：
1. [Optional-feature] WHERE 质量策略配置 publish_warning=true，THE 系统 SHALL 允许 WARNING 记录进入 DataSnapshot 但在结果中标记 quality_status。
2. [Optional-feature] WHERE 质量策略配置 publish_warning=false，THE 系统 SHALL 把 WARNING 记录排除出 DataSnapshot。
3. [Event-driven] WHEN 任一 WARNING 记录被发布或排除时，THE 系统 SHALL 在 DataSnapshot 元数据中统计 warning_published_count 与 warning_excluded_count。
4. [Ubiquitous] THE 系统 SHALL 在查询结果中显式返回每条数据的 quality_status，使上层能识别 WARNING 数据。

**basis_refs**: [TASKBOOK-§6.质量, NFR-§3.1]

**required_evidence**:
- EVREQ-1: 两种策略下的发布行为测试
- EVREQ-2: 计数字段与查询结果元数据的迁移证据

**not_done_when**:
- WARNING 始终发布或始终排除而无策略开关
- 查询结果不暴露 quality_status

---

#### REQ-CORE-012 DataGap 补采验证闭环

**用户故事**：作为运维人员，我希望 DataGap 在补采完成后必须经验证才能关闭，以便避免假关闭。

**类型**：MUST

**覆盖**：S2-013

**验收标准**：
1. [Event-driven] WHEN DataGap 进入 BACKFILLING 完成后，THE 系统 SHALL 不允许直接跳到 CLOSED，必须经过 VERIFIED 中间态。
2. [State-driven] WHILE DataGap 处于 VERIFIED 状态，THE 系统 SHALL 已记录补采前后行数对账、Checksum 对账和质量门禁结果。
3. [Unwanted-behavior] IF 验证证据缺失或对账不一致，THEN THE 系统 SHALL 把 DataGap 退回 BACKFILLING 或置为 UNRESOLVABLE，不得标记 CLOSED。
4. [Ubiquitous] THE 系统 SHALL 保证 DataGap 关闭前必须经过补采或明确确认无法取得。

**basis_refs**: [TASKBOOK-§4.C2, COREOBJ-§9.3, NFR-§3.2]

**required_evidence**:
- EVREQ-1: 状态机 VERIFIED 中间态的迁移证据
- EVREQ-2: 对账不一致被退回的集成测试
- EVREQ-3: CLOSED 前必有验证证据的约束测试

**not_done_when**:
- DataGap 可从 BACKFILLING 直接跳到 CLOSED
- CLOSED 时无对账记录

---

### C. Lineage 与审计（REQ-CORE-013 — REQ-CORE-015）

---

#### REQ-CORE-013 lineage_edge 基础表

**用户故事**：作为数据审计者，我希望通过正式的 lineage_edge 表查询 RAW→CLEAN→QUALITY 之间的直接关系，以便在不依赖服务层遍历的情况下完成血缘追溯。

**类型**：MUST

**覆盖**：S2-014

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 在 lineage schema 下新建 lineage_edge 表，每条记录表达 (source_object_type, source_object_id) → (target_object_type, target_object_id) 的直接血缘关系，并附带 edge_type、created_at、trace_id 字段。
2. [Event-driven] WHEN RawBatch 被 CLEAN 处理消费时，THE 系统 SHALL 写入 RAW→CLEAN 的 lineage_edge；WHEN CleanBatch 通过质量检查时，THE 系统 SHALL 写入 CLEAN→QUALITY 的 lineage_edge。
3. [Event-driven] WHEN 查询某对象的上下游时，THE 系统 SHALL 能在单次递归查询内返回 N 跳血缘（p95 ≤ 3 秒）。
4. [Unwanted-behavior] IF lineage_edge 缺失或断裂，THEN THE 系统 SHALL 在 Lineage 测试中被识别为失败。

**basis_refs**: [TASKBOOK-§4.C2、§8, COREOBJ-§3、§19]

**required_evidence**:
- EVREQ-1: lineage_edge 表迁移（CREATE TABLE + 索引）
- EVREQ-2: RAW→CLEAN→QUALITY 写入 edge 的集成测试
- EVREQ-3: 上下游递归查询的性能测试（p95 ≤ 3s）

**not_done_when**:
- 仅靠服务层遍历查询而无正式表
- lineage schema 仍为空

---

#### REQ-CORE-014 AuditEvent 关键状态变化留痕

**用户故事**：作为合规审计者，我希望所有关键状态变化和高风险动作都被记录到 AuditEvent，以便事后追溯责任与原因。

**类型**：MUST

**覆盖**：S2-015

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 在以下事件 100% 写入 AuditEvent：登录与身份变化、配置变化、数据源启停、任务取消与人工重跑、质量豁免、数据发布与失效、策略版本激活、风控规则变化、信号发布与取消、用户决策、备份恢复、数据迁移、stable 迁移、Worker LOST、Lease 接管、run_type 修复、版本激活、质量豁免。
2. [Event-driven] WHEN 任一上述事件发生时，THE 系统 SHALL 写入 event_type、object_type、object_id、old_status、new_status、actor_type、actor_id、reason、trace_id、run_id、environment_id、occurred_at、metadata 共 13 个字段。
3. [Unwanted-behavior] IF 任一上述事件未写入 AuditEvent，THEN THE 系统 SHALL 在审计完整性测试中被识别为失败。
4. [Ubiquitous] THE 系统 SHALL 保证 100% 的关键状态变化进入 AuditEvent。

**basis_refs**: [TASKBOOK-§4.C2, COREOBJ-§17.1, NFR-§10]

**required_evidence**:
- EVREQ-1: AuditEvent 字段扩展的迁移证据
- EVREQ-2: 各事件类型写入测试（每个事件至少 1 个用例）
- EVREQ-3: 完整性回归测试日志

**not_done_when**:
- 仅有部分事件被记录
- 字段缺失或可空

---

#### REQ-CORE-015 AuditEvent 只追加

**用户故事**：作为合规审计者，我希望 AuditEvent 表历史事件不可被修改或删除，以便审计记录具备法律与运维可信度。

**类型**：MUST

**覆盖**：S2-015

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 把 audit.audit_event 表约束为只追加（通过 DB 权限、触发器或应用层强制），禁止 UPDATE 与 DELETE。
2. [Unwanted-behavior] IF 实现尝试 UPDATE 或 DELETE 历史 AuditEvent，THEN THE 系统 SHALL 拒绝并审计（在新建事件中记录该尝试）。
3. [Event-driven] WHEN 需要修正历史事件语义时，THE 系统 SHALL 通过追加新事件（带 supersedes_event_id）表达，而非修改原事件。
4. [Ubiquitous] THE 系统 SHALL 保证 AuditEvent 历史事件被静默修改或删除的数量为 0。

**basis_refs**: [COREOBJ-§17.1, NFR-§10]

**required_evidence**:
- EVREQ-1: 只追加约束（触发器或权限）的迁移证据
- EVREQ-2: UPDATE/DELETE 被拒绝的测试
- EVREQ-3: supersedes_event_id 追加修正机制的测试

**not_done_when**:
- 表允许 UPDATE/DELETE
- 修正通过覆盖原事件实现

---

### D. DataContext 与 DataSnapshot（REQ-CORE-016 — REQ-CORE-020）

---

#### REQ-CORE-016 DataContext 不读取 RAW

**用户故事**：作为架构治理者，我希望 DataContext 严格只读取已发布的 CLEAN 数据，以便保持 RAW 与研究层之间的隔离边界。

**类型**：MUST

**覆盖**：S2-016

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 保证 DataContext 模块（app/datacontext/）只引用 clean、quality、meta、lineage schema，不引用任何 raw schema 表。
2. [Unwanted-behavior] IF DataContext 实现尝试访问 RAW 表，THEN THE 系统 SHALL 在静态检查或测试中被识别为失败。
3. [Ubiquitous] THE 系统 SHALL 保证 RAW 数据进入 DataContext 路径的次数为 0。
4. [Event-driven] WHEN DataContext 初始化时，THE 系统 SHALL 通过配置或代码结构强制其数据源白名单仅含 CLEAN 已发布数据。

**basis_refs**: [TASKBOOK-§9, NFR-§14]

**required_evidence**:
- EVREQ-1: app/datacontext/ 模块结构证据
- EVREQ-2: 静态依赖检查（如 import linter）通过日志
- EVREQ-3: DataContext 不访问 RAW 的回归测试

**not_done_when**:
- DataContext 在异常分支读取了 RAW
- 仅靠口头约束而无静态/运行时检查

---

#### REQ-CORE-017 DataContext 查询能力

**用户故事**：作为研究/回测使用者，我希望通过 DataContext 进行单股、股票池、全市场、时间区间和事件窗口查询，以便覆盖我所有研究场景。

**类型**：MUST

**覆盖**：S2-016

**验收标准**：
1. [Event-driven] WHEN 调用 DataContext 指定 security_scope 为单股时，THE 系统 SHALL 返回该股在 as_of_time 与 available_at_cutoff 约束下的数据。
2. [Event-driven] WHEN 调用 DataContext 指定 security_scope 为股票池时，THE 系统 SHALL 接受 StockPoolVersion 引用并返回其成员的数据。
3. [Event-driven] WHEN 调用 DataContext 指定 market_scope=FULL_MARKET 时，THE 系统 SHALL 返回全市场（按 DataItem 范围）数据，但禁止扫描整张分钟表（须走分区/索引）。
4. [Event-driven] WHEN 调用 DataContext 指定 event_window 时，THE 系统 SHALL 返回事件前后指定窗口内的对齐数据。
5. [Event-driven] WHEN 调用 DataContext 指定 time_range 时，THE 系统 SHALL 返回该时间区间内的数据。

**basis_refs**: [TASKBOOK-§4.C3, COREOBJ-§10.1]

**required_evidence**:
- EVREQ-1: DataContext 5 种查询模式的接口签名
- EVREQ-2: 每种模式至少 1 个集成测试
- EVREQ-3: 全市场查询不扫描整张分钟表的执行计划证据

**not_done_when**:
- 缺少任一查询模式
- 全市场查询走全表扫描

---

#### REQ-CORE-018 DataContext 多频率数据对齐

**用户故事**：作为量化研究者，我希望 DataContext 支持日、周、月、分钟、财务和事件数据按业务时间对齐，以便我能进行跨频率因子计算。

**类型**：MUST

**覆盖**：S2-016

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 支持 frequency ∈ {daily, weekly, monthly, minute, financial, event} 共 6 种频率的数据查询。
2. [Event-driven] WHEN 一次查询涉及多个频率时，THE 系统 SHALL 按业务时间（business_time）对齐返回，并明确标注每条记录的频率。
3. [Unwanted-behavior] IF 对齐规则导致数据歧义（如分钟未聚合到日），THEN THE 系统 SHALL 在结果中标记 alignment_note 而非静默返回。
4. [Ubiquitous] THE 系统 SHALL 在周/月聚合时遵循交易日历（trade_calendar）而非自然日历。

**basis_refs**: [TASKBOOK-§4.C3, NFR-§3.4]

**required_evidence**:
- EVREQ-1: 6 种频率查询的接口与测试
- EVREQ-2: 多频率对齐用例的集成测试
- EVREQ-3: 交易日历对齐规则的测试

**not_done_when**:
- 缺少任一频率支持
- 周/月聚合按自然日历

---

#### REQ-CORE-019 DataSnapshot 不可变

**用户故事**：作为回测研究者，我希望 READY 状态的 DataSnapshot 核心内容不可被覆盖，以便我引用的回测输入具备长期复现性。

**类型**：MUST

**覆盖**：S2-017

**验收标准**：
1. [State-driven] WHILE DataSnapshot 处于 READY 状态，THE 系统 SHALL 拒绝对其核心内容（data_item_versions、content_fingerprint、as_of_time、available_at_cutoff）的任何修改。
2. [Event-driven] WHEN DataSnapshot 需要修正时，THE 系统 SHALL 通过创建新 DataSnapshot（带 supersedes_snapshot_id）或置 INVALIDATED 表达，而非原地修改。
3. [Ubiquitous] THE 系统 SHALL 在每个 DataSnapshot 上记录 content_fingerprint（内容指纹）用于完整性校验。
4. [Unwanted-behavior] IF 实现尝试修改 READY 状态 DataSnapshot，THEN THE 系统 SHALL 拒绝并审计。

**basis_refs**: [TASKBOOK-§4.C3, COREOBJ-§10.2、§4.4]

**required_evidence**:
- EVREQ-1: DataSnapshot 模型与迁移
- EVREQ-2: READY 不可修改的约束测试
- EVREQ-3: content_fingerprint 校验机制的测试

**not_done_when**:
- READY 后仍可 UPDATE
- 缺少 content_fingerprint

---

#### REQ-CORE-020 DataSnapshot 输入可复现与查询一致

**用户故事**：作为回测研究者，我希望同一 DataSnapshot 的输入可复现且重复查询返回一致结果，以便我能验证回测结果差异来自策略而非数据。

**类型**：MUST

**覆盖**：S2-017

**验收标准**：
1. [Event-driven] WHEN DataSnapshot 构建时，THE 系统 SHALL 记录其依赖的所有 CleanBatch、CleanRecordVersion、quality_policy_version、as_of_time、available_at_cutoff 共 5 类输入引用。
2. [Event-driven] WHEN 同一 DataSnapshot 被多次查询时，THE 系统 SHALL 返回完全一致的结果（行数、内容、顺序按约定稳定）。
3. [Event-driven] WHEN 重新构建 DataSnapshot（相同输入与规则版本）时，THE 系统 SHALL 产出相同 content_fingerprint。
4. [Unwanted-behavior] IF 同一 Snapshot 重复查询结果不一致，THEN THE 系统 SHALL 在 Snapshot 一致性测试中被识别为失败。

**basis_refs**: [TASKBOOK-§4.C3, COREOBJ-§10.2]

**required_evidence**:
- EVREQ-1: 5 类输入引用字段的迁移证据
- EVREQ-2: 重复查询一致性测试
- EVREQ-3: 重建相同 fingerprint 的测试

**not_done_when**:
- 缺少输入引用
- 重复查询结果漂移

---

### E. 防未来函数（REQ-CORE-021 — REQ-CORE-024）

---

#### REQ-CORE-021 防未来函数时间语义模式

**用户故事**：作为量化研究者，我希望研究模式、策略模式和回测模式具有明确的时间语义，以便在不同场景下避免未来函数污染。

**类型**：MUST

**覆盖**：S2-018

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 定义 research_mode、strategy_mode、backtest_mode 共 3 种时间语义模式，并明确每种模式对 as_of_time 与 available_at_cutoff 的处理规则。
2. [State-driven] WHILE 处于 backtest_mode 时，THE 系统 SHALL 严格使用历史时点数据，禁止读取任何 available_at > as_of_time 的数据。
3. [State-driven] WHILE 处于 research_mode 时，THE 系统 SHALL 允许使用当前最新可用数据，但须在结果中标注 latest_available_at。
4. [Unwanted-behavior] IF 任一模式违反其时间语义，THEN THE 系统 SHALL 在防未来测试中被识别为失败。

**basis_refs**: [TASKBOOK-§4.C3, NFR-§3.3]

**required_evidence**:
- EVREQ-1: 3 种模式的定义文档与代码枚举
- EVREQ-2: 每种模式至少 1 个集成测试
- EVREQ-3: 模式违反被识别的测试

**not_done_when**:
- 模式未在代码中枚举
- backtest_mode 读取了未来数据

---

#### REQ-CORE-022 发布时间与可用时间分离

**用户故事**：作为数据治理者，我希望数据"发布到平台"的时间与"对研究可用"的时间分离记录，以便按业务规则延迟公开（如财报静默期）。

**类型**：MUST

**覆盖**：S2-018

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 在 CLEAN 记录上同时记录 published_at（发布到平台时间）与 available_at（对研究可用时间），且二者独立可配置。
2. [Event-driven] WHEN DataContext 设定 available_at_cutoff 时，THE 系统 SHALL 使用 available_at 而非 published_at 作为查询上限。
3. [Optional-feature] WHERE 业务规则要求静默期（如财报公告后 T+N 才可用），THE 系统 SHALL 通过 DataItem.availability_rule 表达 N，并在 CLEAN 写入时计算 available_at = published_at + N。
4. [Unwanted-behavior] IF 实现使用 published_at 替代 available_at 作为查询上限，THEN THE 系统 SHALL 在防未来测试中被识别为失败。

**basis_refs**: [TASKBOOK-§6.CLEAN, NFR-§3.3]

**required_evidence**:
- EVREQ-1: published_at 与 available_at 分离字段的迁移证据
- EVREQ-2: 静默期计算的测试
- EVREQ-3: available_at 作为查询上限的测试

**not_done_when**:
- 仅有一个时间字段
- 查询用 published_at 而非 available_at

---

#### REQ-CORE-023 历史股票池与历史状态按时点读取

**用户故事**：作为回测研究者，我希望回测使用历史时点的股票池成员和历史状态（如停牌、涨跌停、退市），而非当前最新状态，以便回测结果真实。

**类型**：MUST

**覆盖**：S2-018

**验收标准**：
1. [Event-driven] WHEN 回测引用 StockPoolVersion 时，THE 系统 SHALL 读取该版本 effective_at 时点的成员快照，而非当前 StockPool 成员。
2. [Event-driven] WHEN 回测需要某时点的证券状态（停牌、涨跌停、退市）时，THE 系统 SHALL 通过 stock_suspend、stock_limit_price 等表按时点查询，而非使用当前状态。
3. [Unwanted-behavior] IF 实现使用当前股票池或当前状态替代历史时点数据，THEN THE 系统 SHALL 在防未来测试中被识别为失败。
4. [Ubiquitous] THE 系统 SHALL 保证历史回测使用当前成员替代历史成员的次数为 0。

**basis_refs**: [TASKBOOK-§4.C3, COREOBJ-§12.2, NFR-§3.1]

**required_evidence**:
- EVREQ-1: StockPoolVersion 时点读取的测试
- EVREQ-2: 历史证券状态时点查询的测试
- EVREQ-3: 防未来测试套件覆盖此场景的日志

**not_done_when**:
- 回测使用当前股票池成员
- 历史状态查询无时点约束

---

#### REQ-CORE-024 防未来测试套件

**用户故事**：作为质量保证者，我希望有一套覆盖所有防未来场景的测试套件，以便持续守护时间语义边界。

**类型**：MUST

**覆盖**：S2-018

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 提供防未来测试套件，覆盖 backtest_mode、available_at 约束、published_at/available_at 分离、历史股票池、历史状态、复权因子时点共 6 类场景。
2. [Ubiquitous] THE 系统 SHALL 保证防未来测试套件全部通过（100% pass rate）。
3. [Unwanted-behavior] IF 任一防未来测试失败，THEN THE 系统 SHALL 阻断 stable 发布。
4. [Ubiquitous] THE 系统 SHALL 保证已知未来函数数量为 0。

**basis_refs**: [TASKBOOK-§8, NFR-§3.1、§15]

**required_evidence**:
- EVREQ-1: 防未来测试套件代码与目录
- EVREQ-2: 全部通过的测试日志（真实 PG/TimescaleDB 环境）
- EVREQ-3: CI/CD 或本地运行入口

**not_done_when**:
- 测试仅用 Mock
- 任一测试未通过

---

### F. 统一查询 API（REQ-CORE-025 — REQ-CORE-028）

---

#### REQ-CORE-025 统一查询 API 数据覆盖

**用户故事**：作为上层模块开发者，我希望通过统一查询 API 查询日线、分钟、财务和事件数据，而不必理解底层表结构。

**类型**：MUST

**覆盖**：S2-019

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 在 /api/v1 下提供数据查询路由，支持 daily、minute、financial、event 共 4 类数据的查询。
2. [Event-driven] WHEN 查询请求到达时，THE 系统 SHALL 通过 DataContext 执行查询，并在响应中包含 data_source、quality_status、available_at、schema_version 共 4 类元数据说明。
3. [Ubiquitous] THE 系统 SHALL 保证查询路由不直接访问 RAW 表（通过 DataContext 强制）。
4. [Event-driven] WHEN 查询返回多频率数据时，THE 系统 SHALL 在每条记录上标注 frequency。

**basis_refs**: [TASKBOOK-§9, NFR-§6、§14]

**required_evidence**:
- EVREQ-1: /api/v1 查询路由的实现与 OpenAPI 契约
- EVREQ-2: 4 类数据查询的集成测试
- EVREQ-3: 响应元数据字段的契约测试

**not_done_when**:
- 缺少任一数据类型查询
- 响应缺少来源/质量/可用时间说明

---

#### REQ-CORE-026 查询结果元数据说明

**用户故事**：作为研究者，我希望查询结果明确说明数据来源、质量和可用时间，以便我评估结果可信度。

**类型**：MUST

**覆盖**：S2-019

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 在每个查询响应中包含 metadata 段，至少说明 data_source、quality_policy_version、available_at_cutoff、schema_version、rule_version。
2. [Event-driven] WHEN 查询命中 WARNING 数据时，THE 系统 SHALL 在响应中标注每条记录的 quality_status。
3. [Event-driven] WHEN 查询命中复权数据时，THE 系统 SHALL 在响应中标注 adjustment_policy 与复权因子来源。
4. [Unwanted-behavior] IF 查询结果缺少元数据说明，THEN THE 系统 SHALL 在 API 契约测试中被识别为失败。

**basis_refs**: [TASKBOOK-§9, NFR-§3]

**required_evidence**:
- EVREQ-1: 响应 schema 含 metadata 段的契约证据
- EVREQ-2: WARNING/复权标注的测试

**not_done_when**:
- 响应仅返回数据而无元数据
- WARNING 数据未标注

---

#### REQ-CORE-027 API 不执行长任务与查询超时

**用户故事**：作为 API 使用者，我希望查询请求不会长时间阻塞，超时后能明确返回，以便 API 服务稳定。

**类型**：MUST

**覆盖**：S2-019

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 保证 /api/v1 数据查询路由不执行长任务（如全量回采、批量计算）；长任务必须返回 task_id 异步执行。
2. [Optional-feature] THE 系统 SHALL 为每个查询配置 <query_timeout: 30 秒>（可配置）超时上限，超时后返回 504 或约定错误码。
3. [Unwanted-behavior] IF 查询超过超时上限，THEN THE 系统 SHALL 中止查询并释放连接，不得继续占用数据库连接。
4. [Ubiquitous] THE 系统 SHALL 保证 API 错误响应不泄露明文密钥、Token 或内部堆栈细节。

**basis_refs**: [TASKBOOK-§9、§11, NFR-§6、§9.2]

**required_evidence**:
- EVREQ-1: 查询超时配置与中止机制的测试
- EVREQ-2: 长任务返回 task_id 的契约测试
- EVREQ-3: 错误响应脱敏的测试

**not_done_when**:
- API 同步执行长任务
- 错误响应泄露密钥

---

#### REQ-CORE-028 运维查询不扫描整张分钟表

**用户故事**：作为运维人员，我希望运维类查询（如数据水位、缺口统计）不扫描整张分钟表，以便保护数据库性能。

**类型**：MUST

**覆盖**：S2-019

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 保证运维查询路由（如水位、缺口、质量统计）使用 DataWatermark 汇总表或索引视图，而非全表扫描 raw_stock_minute / clean_stock_minute。
2. [Event-driven] WHEN 运维查询命中分钟维度时，THE 系统 SHALL 走分区裁剪与索引，且执行计划不含 Seq Scan on clean_stock_minute。
3. [Unwanted-behavior] IF 运维查询执行计划包含整张分钟表扫描，THEN THE 系统 SHALL 在性能测试中被识别为失败。
4. [Ubiquitous] THE 系统 SHALL 保证运维查询 p95 ≤ 1 秒（在 svr3 4 CPU、正确索引、无其他全量重任务条件下）。

**basis_refs**: [TASKBOOK-§9, NFR-§6]

**required_evidence**:
- EVREQ-1: 运维查询路由的执行计划（EXPLAIN ANALYZE）
- EVREQ-2: 性能测试日志（p95 ≤ 1s）
- EVREQ-3: 全表扫描被识别的测试

**not_done_when**:
- 运维查询全表扫描分钟表
- 性能不达标且无优化证据

---

### G. 环境与运维（REQ-CORE-029 — REQ-CORE-033）

---

#### REQ-CORE-029 数据库迁盘脚本

**用户故事**：作为运维人员，我希望有完整的数据库迁盘脚本与预检，以便把数据库从系统盘迁到 SSD 而不丢数据。

**类型**：MUST

**覆盖**：S2-020

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 提供数据库迁盘脚本（含预检、停止、复制、启动、验证、回滚共 6 个阶段）。
2. [Event-driven] WHEN 用户执行迁盘脚本时，THE 系统 SHALL 输出完整可复制的命令序列，不自动执行 stable 不可逆操作。
3. [Event-driven] WHEN 迁盘预检失败（如目标目录空间不足、权限不对、PG 版本不匹配）时，THE 系统 SHALL 中止并报告原因。
4. [Ubiquitous] THE 系统 SHALL 提供回滚步骤，使迁盘失败后能恢复到原系统盘状态。
5. [Ubiquitous] THE 系统 SHALL 不自动对 stable 执行迁盘、删旧卷、开放端口、替换正式数据库、扩大分钟历史共 5 类高风险动作。

**basis_refs**: [TASKBOOK-§4.C4、§11, NFR-§8、§17]

**required_evidence**:
- EVREQ-1: 迁盘脚本文件与 6 阶段说明
- EVREQ-2: 预检失败的测试日志
- EVREQ-3: 回滚步骤的演练记录（server-test 环境）

**not_done_when**:
- 脚本自动执行 stable 不可逆操作
- 缺少回滚步骤

---

#### REQ-CORE-030 分钟数据压缩、归档与恢复基准

**用户故事**：作为运维人员，我希望对分钟数据建立压缩、归档与恢复基准，以便控制存储增长并保证归档可恢复。

**类型**：MUST

**覆盖**：S2-021

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 在 TimescaleDB hypertable 上为 clean_stock_minute 配置压缩策略，并记录压缩前后空间占用与压缩比。
2. [Event-driven] WHEN 分钟数据达到归档阈值时，THE 系统 SHALL 提供归档脚本生成归档文件，并附带 Checksum。
3. [Event-driven] WHEN 归档文件被恢复时，THE 系统 SHALL 通过 Checksum 校验完整性，并验证恢复后行数与原始一致。
4. [Ubiquitous] THE 系统 SHALL 在迁盘、压缩、归档和恢复完成前禁止扩大全市场分钟历史。
5. [Ubiquitous] THE 系统 SHALL 保证归档前后记录数与 Checksum 一致（差异为 0）。

**basis_refs**: [TASKBOOK-§4.C4, NFR-§3.2、§8]

**required_evidence**:
- EVREQ-1: 压缩策略配置与压缩比基准
- EVREQ-2: 归档脚本与 Checksum 证据
- EVREQ-3: 恢复后行数与 Checksum 对账日志

**not_done_when**:
- 无压缩策略
- 归档无 Checksum 或恢复不一致

---

#### REQ-CORE-031 server-test 独立环境

**用户故事**：作为质量保证者，我希望有一个与 stable 完全隔离的 server-test 环境，以便安全执行破坏性测试与迁盘演练。

**类型**：MUST

**覆盖**：S2-022

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 提供独立 docker-compose 配置（如 compose-server-test.yml），与 stable 完全隔离：独立数据库实例、独立端口、独立数据卷、独立网络。
2. [Ubiquitous] THE 系统 SHALL 保证 server-test 与 stable 不共享任何凭据、配置或数据卷。
3. [Event-driven] WHEN server-test 启动时，THE 系统 SHALL 不影响 stable 运行（不共用进程、不抢占端口）。
4. [Unwanted-behavior] IF server-test 误连 stable 数据库，THEN THE 系统 SHALL 通过配置校验拒绝连接。

**basis_refs**: [TASKBOOK-§4.C4、§9, NFR-§9.1、§17]

**required_evidence**:
- EVREQ-1: compose-server-test.yml 文件与端口/卷/网络配置
- EVREQ-2: server-test 启动不影响 stable 的测试
- EVREQ-3: 配置校验拒绝误连的测试

**not_done_when**:
- server-test 与 stable 共享数据库或卷
- server-test 启动抢占 stable 端口

---

#### REQ-CORE-032 数据库全量备份脚本

**用户故事**：作为运维人员，我希望有数据库全量备份脚本，且备份文件含 Checksum 与时间戳，以便满足 RPO 目标。

**类型**：MUST

**覆盖**：S2-023

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 提供数据库全量备份脚本（如 pg_dump 或基础备份）。
2. [Ubiquitous] THE 系统 SHALL 在每个备份文件上记录时间、版本、大小与 Checksum 共 4 个属性。
3. [Ubiquitous] THE 系统 SHALL 保证至少保留一个服务器外副本后才能认定生产（备份空间不与主数据库共用唯一故障点）。
4. [Ubiquitous] THE 系统 SHALL 保证备份文件不含未加密明文密钥。
5. [Ubiquitous] THE 系统 SHALL 满足配置/策略/风控/信号/用户决策/审计类数据 RPO ≤ 4 小时，市场数据 RPO ≤ 24 小时。

**basis_refs**: [TASKBOOK-§4.C4, NFR-§12]

**required_evidence**:
- EVREQ-1: 备份脚本文件
- EVREQ-2: 备份文件 4 属性记录的证据
- EVREQ-3: 服务器外副本配置的证据
- EVREQ-4: 备份不含明文密钥的扫描测试

**not_done_when**:
- 备份无 Checksum 或时间戳
- 备份与主库共用唯一故障点
- 备份含明文密钥

---

#### REQ-CORE-033 数据库恢复脚本与独立库恢复验证

**用户故事**：作为运维人员，我希望有数据库恢复脚本，并能验证恢复到独立数据库后应用可正常工作，以便满足 RTO 目标。

**类型**：MUST

**覆盖**：S2-023

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 提供新数据库恢复脚本，能从备份文件恢复到独立 PostgreSQL 实例。
2. [Event-driven] WHEN 恢复完成后，THE 系统 SHALL 验证 Alembic 版本正确、关键表行数一致、Checksum 一致共 3 项。
3. [Event-driven] WHEN 应用连接恢复库时，THE 系统 SHALL 通过健康检查（API /health 返回 200、Scheduler 心跳正常、Worker 不误连 stable）。
4. [Ubiquitous] THE 系统 SHALL 满足配置/策略/风控/信号/用户决策/审计类数据 RTO ≤ 4 小时，市场数据 RTO ≤ 24 小时。
5. [Unwanted-behavior] IF 恢复库被 stable 误连，THEN THE 系统 SHALL 通过配置校验拒绝。

**basis_refs**: [TASKBOOK-§4.C4, NFR-§12.3]

**required_evidence**:
- EVREQ-1: 恢复脚本文件
- EVREQ-2: 恢复后 3 项验证的日志
- EVREQ-3: 应用健康检查的日志
- EVREQ-4: 每月至少一次恢复演练的记录

**not_done_when**:
- 恢复后 Alembic 版本不一致
- 应用无法连接或健康检查失败

---

### H. 测试与验收（REQ-CORE-034 — REQ-CORE-035）

---

#### REQ-CORE-034 集成测试套件覆盖

**用户故事**：作为质量保证者，我希望有一套完整的单元、数据库集成、Alembic、契约、故障恢复、幂等、防未来、Lineage、备份恢复测试，以便系统性地守护数据底座质量。

**类型**：MUST

**覆盖**：S2-024

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 提供以下 10 类测试：单元测试、数据库集成测试、Alembic 空库升级测试、现有库升级预检、API 契约测试、故障和恢复测试、幂等测试、防未来测试、Lineage 测试、备份恢复测试。
2. [Ubiquitous] THE 系统 SHALL 保证所有数据库相关测试在真实 PostgreSQL 16 / TimescaleDB 2.28.3 上运行，不得仅用 Mock/SQLite/内存对象。
3. [Ubiquitous] THE 系统 SHALL 保证 Alembic 空库从零升级到 head 成功，且当前库从 0012 升级到新 head 成功。
4. [Ubiquitous] THE 系统 SHALL 保证普通业务代码行覆盖率 ≥ 80%，核心状态机/风控/执行模块分支覆盖率 ≥ 90%。
5. [Ubiquitous] THE 系统 SHALL 保证以下场景 100% 覆盖：幂等、状态机合法流转、防未来、财务修订、质量发布门禁、风控旁路阻断、用户决策与信号分离、权限隔离、重复订单防护、备份恢复、迁移升级。
6. [Unwanted-behavior] IF 任一测试类型缺失或失败，THEN THE 系统 SHALL 阻断 stable 发布。

**basis_refs**: [TASKBOOK-§8, NFR-§15]

**required_evidence**:
- EVREQ-1: 10 类测试目录与运行入口
- EVREQ-2: 真实 PG/TimescaleDB 环境的测试运行日志
- EVREQ-3: Alembic 空库升级与现有库升级的日志
- EVREQ-4: 覆盖率报告

**not_done_when**:
- 任一测试类型缺失
- 数据库测试仅用 Mock/SQLite
- 覆盖率不达标

---

#### REQ-CORE-035 代表性真实数据端到端验收

**用户故事**：作为项目验收者，我希望有覆盖 10 个 DataItem 全链路的端到端测试，以便验证数据底座真实可用。

**类型**：MUST

**覆盖**：S2-025

**验收标准**：
1. [Ubiquitous] THE 系统 SHALL 提供端到端测试，至少覆盖 trade_calendar、stock_basic、stock_daily、stock_adj_factor、stock_daily_basic、stock_suspend、stock_limit_price、stock_minute、financial_income、financial_indicator 共 10 个 DataItem。
2. [Ubiquitous] THE 系统 SHALL 保证端到端链路覆盖：采集 → RAW → CLEAN → QUALITY → Lineage → Snapshot → DataContext → API 共 8 个阶段。
3. [Event-driven] WHEN 端到端测试运行时，THE 系统 SHALL 在真实 PG/TimescaleDB 上执行，并记录每个用例的：用例 ID、关联 S2 任务、环境、代码提交、镜像 Digest、迁移版本、测试数据范围、命令、期望、实际、日志、结论共 12 项。
4. [Ubiquitous] THE 系统 SHALL 保证端到端结论只允许 PASS / FAIL / BLOCKED，不允许"基本通过"；stable 操作未执行时最多为 BLOCKED / WAITING_USER_EXECUTION。
5. [Ubiquitous] THE 系统 SHALL 保证未执行的 stable 操作标记为 WAITING_USER_EXECUTION。

**basis_refs**: [ACCEPTANCE-§2.H、§3、§4]

**required_evidence**:
- EVREQ-1: 端到端测试代码与运行入口
- EVREQ-2: 10 个 DataItem × 8 阶段的测试矩阵
- EVREQ-3: 12 项证据记录模板与填充实例
- EVREQ-4: 最终结论（PASS/FAIL/BLOCKED）文档

**not_done_when**:
- 测试仅用 Mock 数据
- 结论写"基本通过"
- stable 操作被自动执行

---

## 5. 非功能性需求（NFR 摘要）

> 以下为已确认 NFR 的关键指标摘要，详细见 `docs/02_可行性研究与资源评估/08_非功能需求与服务目标.md`。

### 5.1 数据正确性（强制 100%）

| 指标 | 目标 |
|---|---:|
| 正式业务主键唯一性 | 100% |
| 正式外键和对象引用完整性 | 100% |
| 正式批次可追溯来源 | 100% |
| 版本对象被静默覆盖 | 0 |
| 已知未来函数 | 0 |
| 未通过质量门禁直接发布 | 0 |
| test 数据进入 stable | 0 |

### 5.2 数据时效性

- 95% 的日常增量任务在来源可用后 <task_create_sla: 15 分钟>（可配置）内被创建
- 95% 的日频增量在来源可用后 <task_complete_sla_95: 2 小时>（可配置）内完成
- 99% 的日频增量在来源可用后 <task_complete_sla_99: 4 小时>（可配置）内完成

### 5.3 任务可靠性

- 幂等重跑产生不可控重复：0
- 任务无终态且无 Lease/心跳：0
- 失败原因不可查询：0
- 重试覆盖原 Attempt：0
- 任务终态回到 RUNNING：0
- 业务状态仅存在内存：0

### 5.4 查询性能（svr3 4 CPU、正确索引、无其他全量重任务）

| 场景 | p95 目标 |
|---|---:|
| 健康检查 | ≤ 300 ms |
| 任务状态和详情 | ≤ 1 s |
| 单股票 10 年日线 | ≤ 2 s |
| 100 只股票 5 年日线 | ≤ 5 s |
| 单股票 1 年 1 分钟 | ≤ 5 s |
| 单次对象上游或下游追溯 | ≤ 3 s |
| 常用元数据目录 | ≤ 1 s |

### 5.5 安全

- Git 中明文密钥：0
- 镜像中明文密钥：0
- 日志中明文密钥：0
- API 错误中明文密钥：0
- test 与 stable 凭据不同
- Token 支持轮换

### 5.6 容量

- 稳定数据盘保持至少 30% 可用空间
- 任一挂载点使用率达 70% 预警、80% 阻止新大规模初始化、90% 停止非必要写入
- 系统盘不承载长期全市场分钟增长

### 5.7 备份恢复（RPO/RTO）

| 数据类别 | RPO | RTO |
|---|---:|---:|
| 配置/策略/风控/信号/用户决策/审计 | ≤ 4 小时 | ≤ 4 小时 |
| 可重新采集的市场数据 | ≤ 24 小时 | ≤ 24 小时 |
| 回测和报告制品 | ≤ 24 小时 | ≤ 24 小时 |
| Git 代码和文档 | 以远程主分支为准 | ≤ 2 小时 |

## 6. 配置点清单

| 配置项 | 默认值 | 所属 REQ |
|---|---|---|
| worker_lost_threshold | 10 分钟 | REQ-CORE-002 |
| recovery_sla | 15 分钟 | REQ-CORE-002 |
| publish_warning | true（按 DataItem 可配置） | REQ-CORE-011 |
| query_timeout | 30 秒 | REQ-CORE-027 |
| task_create_sla | 15 分钟 | NFR-§4.1 |
| task_complete_sla_95 | 2 小时 | NFR-§4.2 |
| task_complete_sla_99 | 4 小时 | NFR-§4.2 |
| availability_rule（静默期 N） | 按 DataItem 配置 | REQ-CORE-022 |

## 7. 依赖关系

| 上游 REQ | 下游 REQ | 依赖类型 |
|---|---|---|
| REQ-CORE-001 | REQ-CORE-005、REQ-CORE-006 | DataItem 元数据是 RAW/CLEAN 的基础 |
| REQ-CORE-002 | REQ-CORE-014 | LOST 触发审计 |
| REQ-CORE-005 | REQ-CORE-006、REQ-CORE-013 | RAW 来源是 CLEAN 与 lineage 的基础 |
| REQ-CORE-006 | REQ-CORE-007、REQ-CORE-008、REQ-CORE-009 | CLEAN 基础属性支撑复权/财务/时间约束 |
| REQ-CORE-006 | REQ-CORE-010、REQ-CORE-011 | 质量状态依赖 CLEAN 属性 |
| REQ-CORE-013 | REQ-CORE-019 | lineage 支撑 Snapshot 输入可复现 |
| REQ-CORE-016 | REQ-CORE-017、REQ-CORE-018、REQ-CORE-025 | DataContext 是查询 API 的基础 |
| REQ-CORE-019 | REQ-CORE-021、REQ-CORE-024 | Snapshot 是防未来的基础 |
| REQ-CORE-031 | REQ-CORE-029、REQ-CORE-030、REQ-CORE-032、REQ-CORE-033 | server-test 是运维脚本验证前置 |

## 8. 完成判定

只有以下全部具备，本 WI 才能进入 verification_done：

- 31 个 MUST 需求全部有真实 PG/TimescaleDB 环境的验证证据
- Alembic 迁移从 0012 升级到新 head 成功（空库与现有库两条路径）
- 端到端 10 个 DataItem × 8 阶段测试矩阵结论为 PASS
- stable 不可逆操作生成完整命令并标记 WAITING_USER_EXECUTION
- 路线图与任务总表更新

仅完成设计或代码不能标记 DONE。
