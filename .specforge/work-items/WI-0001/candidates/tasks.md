---
tasks_format: contract
module_code: CORE
work_item_id: WI-0001
base_spec_version: PSV-0001
covers: [S2-002, S2-005, S2-006, S2-009, S2-010, S2-011, S2-012, S2-013, S2-014, S2-015, S2-016, S2-017, S2-018, S2-019, S2-020, S2-021, S2-022, S2-023, S2-024, S2-025]
checkpoint_groups: [C2, C3, C4, C5]
migrations_base_head: 0012_p4_minute_governance
next_migration_start: 0013
---

# Tasks: 第2步数据底座 (S2-002—S2-025)

> 本文档把 `design.candidate.md` 的 21 个设计决策（DD-CORE-001—DD-CORE-021）拆解为 19 个可执行 Task 合同，按检查点 C2（采集与治理）、C3（查询与防未来）、C4（环境/迁盘/容量/恢复）、C5（集成/部署/验收）分组。
>
> **关键依赖链**：3 个 Alembic 迁移（TASK-001/002/003）是后续代码任务的地基；DataContext 共享值对象在 TASK-007 内统一建立；测试任务（TASK-006/011/016/017）依赖对应实现任务全部完成。

## 检查点 C2: 采集与治理（S2-002—S2-015）

---

### TASK-WI-0001-001 创建 Alembic 迁移 0013 — lineage_edge + data_snapshot 表

**context_block**（executor 必读）：
- **What**: 新建迁移文件 `migrations/versions/0013_lineage_and_snapshot.py`，down_revision 指向 `0012_p4_minute_governance`。创建 `lineage` schema + `lineage.lineage_edge` 表（DD-CORE-011）；创建 `clean.data_snapshot` + `clean.data_snapshot_input` 表（DD-CORE-015）。
- **Why**: 为数据血缘追溯（REQ-CORE-013）和不可变数据快照（REQ-CORE-019/020）提供物理存储基础；lineage schema 当前不存在，DataSnapshot 模型当前不存在。
- **Refs**: DD-CORE-011（lineage_edge 表结构）、DD-CORE-015（data_snapshot/data_snapshot_input 表结构 + READY 不可变触发器）
- **Current Implementation**:
  - 迁移链 head = `0012_p4_minute_governance`（`migrations/versions/0012_p4_minute_governance.py`）
  - `lineage` schema 不存在；`app/lineage/service.py` 仅靠服务层 JOIN 遍历
  - `clean` schema 已有 `clean_batch` 表（FK 目标存在）
  - 依据来源：CODE_OBSERVED
- **Constraints**:
  - 不修改已有迁移 0001-0012
  - 只新增 schema/表/索引/触发器，不修改已有表
  - lineage_edge 含字段：edge_id(UUID PK), source_type, source_id, target_type, target_id, edge_type, scope_key, metadata(JSONB), trace_id, created_at；含 source/target 复合索引
  - data_snapshot 含 status CHECK(BUILDING/READY/INVALIDATED)、content_fingerprint、supersedes_snapshot_id 自引用 FK、计数字段
  - data_snapshot_input 含 UNIQUE(snapshot_id, clean_batch_id)
  - data_snapshot READY 不可变触发器函数 `prevent_snapshot_modification()`
  - 遵守 project-rules（TODO 占位，按现有迁移风格 `app/storage/models/base.py` 对齐）
- **Done When Code**: `migrations/versions/0013_*.py` 存在；down_revision='0012_p4_minute_governance'；upgrade 创建 2 schema/3 表/索引/触发器；downgrade 可逆
- **Done When Behavior**: `alembic upgrade head` 后 `lineage.lineage_edge`、`clean.data_snapshot`、`clean.data_snapshot_input` 表存在且触发器 `trg_data_snapshot_no_modify_ready` 已注册
- **Done When Evidence**: 真实 PG 上 `alembic upgrade 0013` 返回 0；`\dt lineage.*` 和 `\dt clean.data_snapshot*` 返回非空

- **依赖**: 无
- **refs**: [DD-CORE-011, DD-CORE-015, REQ-CORE-013, REQ-CORE-019, REQ-CORE-020]
- files: [migrations/versions/0013_lineage_and_snapshot.py]
- **verification_commands**:
  - integration:
    - `alembic upgrade 0013`
  - regression:
    - `alembic downgrade 0012`
- **verification_evidence_expected**:
  - command: `alembic upgrade 0013`, expected_exit_code: 0, evidence_type: migration_log
  - command: `alembic downgrade 0012`, expected_exit_code: 0, evidence_type: migration_log
- **out_of_scope**: lineage_edge 写入服务逻辑（TASK-004）、DataSnapshot 业务逻辑（TASK-008）、audit_event 触发器（TASK-003）

---

### TASK-WI-0001-002 创建 Alembic 迁移 0014 — CLEAN published_at + 财务表 + DataItem 元数据

**context_block**（executor 必读）：
- **What**: 新建迁移文件 `migrations/versions/0014_clean_published_at_financial_dataitem.py`，down_revision 指向 0013。为所有 CLEAN 类型化表新增 `_published_at TIMESTAMPTZ` 列（DD-CORE-006）；新建 `clean.financial_income` 和 `clean.financial_indicator` 多版本表 + 部分唯一索引（DD-CORE-008）；为 `meta.data_item` 新增 `quality_policy_ref VARCHAR(64)` 列并补齐 10 个 DataItem 元数据种子（DD-CORE-001）。
- **Why**: 分离 published_at/available_at（REQ-CORE-022）；支撑财务修订多版本保留（REQ-CORE-008）；补齐 DataItem 元数据使水位/采集/归档按业务规则推进（REQ-CORE-001）。
- **Refs**: DD-CORE-006（published_at 分离）、DD-CORE-008（财务多版本表）、DD-CORE-001（DataItem 元数据补齐 + quality_policy_ref）
- **Current Implementation**:
  - CLEAN 类型化表使用下划线前缀物理列（`_available_at` 映射 Python `available_at`），见 `app/storage/models/clean.py`
  - 现有 CLEAN 表：stock_daily, stock_adj_factor, stock_adj_factor_history, stock_daily_basic, stock_suspend_event, stock_limit_price, stock_minute, trade_calendar, security_master, security_master_history
  - 财务 CLEAN 表不存在；RAW 层有 `raw.tushare_income`/`raw.tushare_fina_indicator`（映射源）
  - `meta.DataItem` 有 9 字段，缺 quality_policy_ref；种子在 `migrations/versions/0002_seed_catalog.py`
  - 依据来源：CODE_OBSERVED
- **Constraints**:
  - `_published_at` 列加默认值 `now()` 避免破坏现有数据
  - 财务表字段参照 DD-CORE-008 的 DDL：含 report_period, announce_time, revision_version, valid_from, valid_to, is_current, source_version + 下划线前缀治理列
  - 部分唯一索引 `WHERE is_current = true`
  - DataItem 种子值严格按 DD-CORE-001 表格（trade_calendar/stock_basic/stock_daily/stock_adj_factor/stock_daily_basic/stock_suspend/stock_limit_price/stock_minute/financial_income/financial_indicator）
  - 不得用"待定/未知"占位；capability_status 未实测保持 UNKNOWN
  - 依赖迁移 0013 已创建（down_revision 链）
- **Done When Code**: 0014 迁移存在；14+ 张 CLEAN 表新增 `_published_at`；2 张财务表 + 部分唯一索引创建；meta.data_item 新增 quality_policy_ref + 10 行种子 UPDATE
- **Done When Behavior**: 升级后任一 CLEAN 记录的 `_published_at` 非空；财务表支持同报告期多版本（is_current=true 唯一）；10 个 DataItem 的 business_time_field/update_mode/frequency/retention_class/quality_policy_ref 非空
- **Done When Evidence**: `alembic upgrade 0014` 返回 0；SQL 查询 10 个 DataItem 元数据全部非空；财务表插入两版本同 report_period 成功

- **依赖**: [TASK-WI-0001-001]
- **refs**: [DD-CORE-001, DD-CORE-006, DD-CORE-008, REQ-CORE-001, REQ-CORE-006, REQ-CORE-008, REQ-CORE-022]
- files: [migrations/versions/0014_clean_published_at_financial_dataitem.py]
- **verification_commands**:
  - integration:
    - `alembic upgrade 0014`
    - `python -c "from app.storage.db import session_scope; from app.storage.models.meta import DataItem; from sqlalchemy import select; s=session_scope(); rows=s.execute(select(DataItem.code, DataItem.business_time_field, DataItem.update_mode, DataItem.quality_policy_ref).where(DataItem.code.in_(['trade_calendar','stock_basic','stock_daily','stock_adj_factor','stock_daily_basic','stock_suspend','stock_limit_price','stock_minute','financial_income','financial_indicator']))).all(); assert all(all(v for v in r[1:]) for r in rows), rows"`
  - regression:
    - `alembic downgrade 0013`
    - `alembic upgrade 0014`
- **verification_evidence_expected**:
  - command: `alembic upgrade 0014`, expected_exit_code: 0, evidence_type: migration_log
  - command: DataItem metadata assert, expected_exit_code: 0, evidence_type: test_output
- **out_of_scope**: CLEAN 模型 Python 类映射（TASK-007 readers）、财务业务读取逻辑（TASK-007）、catalog 校验逻辑（TASK-005）

---

### TASK-WI-0001-003 创建 Alembic 迁移 0015 — AuditEvent 扩展 + run_type CHECK + DataGap VERIFIED + RAW 证据

**context_block**（executor 必读）：
- **What**: 新建迁移文件 `migrations/versions/0015_audit_runcheck_datagap_rawevidence.py`，down_revision 指向 0014。扩展 `audit.audit_event` 新增 event_type/run_id/environment_id 列 + 只追加触发器（DD-CORE-012/013）；为 `ops.collect_task` 添加 run_type CHECK 约束 + 历史修复（DD-CORE-003）；扩展 `quality.data_gap` 新增 VERIFIED 验证证据字段（DD-CORE-010）；为 `raw.raw_batch` 新增 content_hash/fetched_at/schema_fingerprint 列（DD-CORE-005）。
- **Why**: 满足审计只追加与 13 字段留痕（REQ-CORE-014/015）；run_type DB 层约束（REQ-CORE-003）；DataGap 补采验证闭环（REQ-CORE-012）；RAW 来源证据完整性（REQ-CORE-005）。
- **Refs**: DD-CORE-012（AuditEvent 字段扩展）、DD-CORE-013（只追加触发器）、DD-CORE-003（run_type CHECK + 历史修复）、DD-CORE-010（DataGap VERIFIED 字段）、DD-CORE-005（RAW 证据补齐）、CP-CORE-002（RAW 证据完整性属性）
- **Current Implementation**:
  - `audit.AuditEvent`（`app/storage/models/audit.py`）有 12 字段：audit_event_id, object_type, object_id, action, before_status, after_status, reason, actor_type, actor_id, trace_id, metadata, occurred_at。缺 event_type/run_id/environment_id；无只追加约束
  - `ops.CollectTask.run_type` 是 `String(32)` 无 DB CHECK（`app/storage/models/ops.py`）
  - `quality.DataGap` 有 status 字段无 VERIFIED 中间态约束（`app/storage/models/quality.py`）
  - `raw.RawBatch`（`app/storage/models/raw.py`）有 request_hash/row_count/schema_version，缺 content_hash/fetched_at/schema_fingerprint
  - 依据来源：CODE_OBSERVED
- **Constraints**:
  - event_type 默认 'state_change'，environment_id 默认 'dev'（NOT NULL）
  - run_type CHECK 添加前先执行历史修复：扫描非枚举值映射到合法值，记录到 audit_event
  - 只追加触发器 `prevent_audit_event_modification()` 阻止 UPDATE/DELETE，抛异常
  - DataGap 新增 pre_backfill_count, post_backfill_count, checksum_verified, verified_at
  - raw_batch 新列允许 NULL（历史数据回填由应用层渐进填充）
  - 依赖迁移 0014 已创建（down_revision 链）
- **Done When Code**: 0015 迁移存在；audit_event 3 新列 + 2 触发器；collect_task CHECK 约束；data_gap 4 新列；raw_batch 3 新列
- **Done When Behavior**: UPDATE/DELETE audit_event 抛异常；插入非法 run_type 被 DB 拒绝；data_gap 含 VERIFIED 证据字段
- **Done When Evidence**: `alembic upgrade head`(0015) 返回 0；`UPDATE audit.audit_event SET action='x'` 抛异常；`INSERT ... run_type='INVALID'` 抛 CHECK 异常

- **依赖**: [TASK-WI-0001-002]
- **refs**: [DD-CORE-003, DD-CORE-005, DD-CORE-010, DD-CORE-012, DD-CORE-013, CP-CORE-002, REQ-CORE-003, REQ-CORE-005, REQ-CORE-012, REQ-CORE-014, REQ-CORE-015]
- files: [migrations/versions/0015_audit_runcheck_datagap_rawevidence.py]
- **verification_commands**:
  - integration:
    - `alembic upgrade head`
  - regression:
    - `alembic downgrade 0014`
- **verification_evidence_expected**:
  - command: `alembic upgrade head`, expected_exit_code: 0, evidence_type: migration_log
  - command: `alembic downgrade 0014`, expected_exit_code: 0, evidence_type: migration_log
- **out_of_scope**: AuditEvent 应用层写入逻辑（TASK-004 部分覆盖）、Worker LOST 调度代码（不在迁移）、run_type CHECK 后的业务校验（应用层）

---

### TASK-WI-0001-004 实现 lineage_edge 写入服务与递归查询

**context_block**（executor 必读）：
- **What**: 新建 `app/storage/models/lineage.py`（LineageEdge ORM 模型）；扩展 `app/lineage/service.py` 新增 `write_edge()` 和 `traverse_lineage()` 函数（DD-CORE-011）。在 CLEAN 消费 RawBatch 与 CleanBatch 通过质量检查的写入时机调用 write_edge。
- **Why**: 把血缘从"服务层遍历"升级为"正式表 + 递归查询"，满足 REQ-CORE-013 单次递归查询返回 N 跳（p95 ≤ 3s）。
- **Refs**: DD-CORE-011（写入时机、递归 CTE）、CP-CORE-002（RAW 证据完整性，加速追溯）
- **Current Implementation**:
  - `app/lineage/service.py` 有 `clean_batch_lineage()` 和 `data_lineage()`（多表 JOIN 遍历，无 edge 表）
  - lineage_edge 表由 TASK-001 迁移创建
  - 依据来源：CODE_OBSERVED + DESIGN
- **Constraints**:
  - 保留现有 `clean_batch_lineage` 和 `data_lineage` 作为兼容，不破坏现有 API
  - write_edge 写入时机：RawBatch 被 CLEAN 消费 → edge_type=DERIVED_FROM；CleanBatch 通过质量检查 → edge_type=QUALIFIED_BY
  - traverse_lineage 使用 `WITH RECURSIVE` CTE，支持 max_depth 参数
  - 不修改 raw schema 写入路径（只在 CLEAN/QUALITY 侧追加 edge 写入）
  - 不引入新依赖
- **Done When Code**: `app/storage/models/lineage.py` 含 LineageEdge 模型；`app/lineage/service.py` 含 write_edge/traverse_lineage；CLEAN/质量流程调用 write_edge
- **Done When Behavior**: CLEAN 消费 RawBatch 后 lineage_edge 有 RAW_BATCH→CLEAN_BATCH 边；traverse_lineage 返回 N 跳结果
- **Done When Evidence**: 集成测试插入 CLEAN 记录后查询 lineage_edge 非空；递归查询 3 跳 p95 ≤ 3s（真实 PG）

- **依赖**: [TASK-WI-0001-001]
- **refs**: [DD-CORE-011, CP-CORE-002, REQ-CORE-005, REQ-CORE-013]
- files: [app/storage/models/lineage.py, app/lineage/service.py, app/storage/models/__init__.py]
- **verification_commands**:
  - integration:
    - `python -m pytest tests/integration/test_lineage_edge.py -v`
  - regression:
    - `python -m pytest tests/lineage/ -v`
- **verification_evidence_expected**:
  - command: `python -m pytest tests/integration/test_lineage_edge.py`, expected_exit_code: 0, expected_output_pattern: "passed", evidence_type: test_output
- **out_of_scope**: lineage API 路由（现有 `app/api/routes/lineage.py` 不改）、DataSnapshot lineage（TASK-008）

---

### TASK-WI-0001-005 补齐 DataItem 元数据校验与 Worker LOST 恢复调度

**context_block**（executor 必读）：
- **What**: 实现 DD-CORE-001 的应用层校验（catalog 模块拒绝空元数据进入 ACTIVE，错误码 DATAITEM_METADATA_INCOMPLETE）；实现 DD-CORE-002 的 Worker LOST 恢复调度（`app/collect/scheduler.py` 新增 `recover_lost_workers()`）；新增配置项到 `app/core/config.py`（worker_lost_threshold_seconds, recovery_sla_seconds, query_timeout_seconds）；实现 DD-CORE-004 强制重跑路径（idempotency 强化）；实现 DD-CORE-010 DataGap 状态机 BACKFILLING→VERIFIED→CLOSED 强制路径。
- **Why**: 满足 REQ-CORE-001（拒绝空元数据）、REQ-CORE-002（LOST 自动恢复 + 终态不可逆）、REQ-CORE-004（强制重跑生成新 Run）、REQ-CORE-012（DataGap 验证闭环）。
- **Refs**: DD-CORE-001（catalog 校验）、DD-CORE-002（LOST 恢复 + 配置）、CP-CORE-001（LOST 正确性属性）、DD-CORE-004（幂等强化）、DD-CORE-010（DataGap 状态机）
- **Current Implementation**:
  - `app/core/config.py` 是 pydantic-settings（env_prefix=QUANTSTOCK1_）
  - `app/collect/scheduler.py` 存在但无 recover_lost_workers
  - `app/catalog/bootstrap.py` 是 DataItem 种子化入口
  - `app/collect/idempotency.py` 存在
  - DataGap status 在应用层管理，无 VERIFIED 强制
  - 依据来源：CODE_OBSERVED
- **Constraints**:
  - recover_lost_workers: 查询心跳超时 Worker → 置 LOST → 标记 RECOVERABLE → 允许接管
  - 终态（SUCCEEDED/FAILED/CANCELLED）不可回退 RUNNING（应用层状态机 + 审计）
  - 配置默认值：worker_lost_threshold_seconds=600, recovery_sla_seconds=900, query_timeout_seconds=30
  - DataGap VERIFIED 要求 post_backfill_count 和 checksum_verified 非空
  - 不引入 Celery/Redis
- **Done When Code**: scheduler.py 含 recover_lost_workers；config.py 含 3 新配置项；catalog 校验函数；idempotency 强制重跑；DataGap 状态机
- **Done When Behavior**: 心跳超时 Worker 被置 LOST；空元 DataItem 被拒绝 ACTIVE；强制重跑生成新 Run；DataGap 不可直跳 CLOSED
- **Done When Evidence**: 集成测试覆盖 LOST 触发、空元拒绝、强制重跑、DataGap 闭环

- **依赖**: [TASK-WI-0001-003]
- **refs**: [DD-CORE-001, DD-CORE-002, CP-CORE-001, DD-CORE-004, DD-CORE-010, REQ-CORE-001, REQ-CORE-002, REQ-CORE-004, REQ-CORE-012]
- files: [app/core/config.py, app/collect/scheduler.py, app/catalog/bootstrap.py, app/collect/idempotency.py, app/collect/state_machine.py]
- **verification_commands**:
  - integration:
    - `python -m pytest tests/integration/test_worker_lost_recovery.py -v`
    - `python -m pytest tests/integration/test_dataitem_metadata_validation.py -v`
    - `python -m pytest tests/integration/test_datagap_verified.py -v`
- **verification_evidence_expected**:
  - command: `python -m pytest tests/integration/test_worker_lost_recovery.py`, expected_exit_code: 0, evidence_type: test_output
- **out_of_scope**: 迁移文件（TASK-002/003）、AuditEvent 写入辅助函数（属 DD-CORE-012 应用层，本 task 只在状态机调用点触发审计）

---

### TASK-WI-0001-006 编写 C2 阶段测试套件

**context_block**（executor 必读）：
- **What**: 编写 C2 阶段集成测试：状态机合法流转与终态不可逆、幂等键阻止重复 + 强制重跑生成新 Attempt、RAW 5 证据字段 + 7 跳引用链、CLEAN 版本区间与 is_current 唯一、质量门禁 FAILED 阻断/WARNING 策略、DataGap VERIFIED 闭环、Lineage 上下游写入与递归查询（p95 ≤ 3s）、run_type CHECK 拒绝非法值、AuditEvent 只追加拒绝 UPDATE/DELETE。
- **Why**: 守护 C2 阶段所有 REQ（REQ-CORE-001—REQ-CORE-015）的真实行为；满足 REQ-CORE-034 的"真实 PG/TimescaleDB"硬约束。
- **Refs**: DD-CORE-001—DD-CORE-013（全部 C2 DD）、REQ-CORE-001—REQ-CORE-015
- **Current Implementation**:
  - 无 `tests/` 目录结构（design.candidate.md §DD-CORE-021 规划新建）
  - 现有测试基线：无（从零搭建真实 PG 测试夹具）
  - 依据来源：DESIGN
- **Constraints**:
  - 必须使用真实 PostgreSQL 16 + TimescaleDB 2.28.3（server-test 环境，TASK-012）；不得仅用 Mock/SQLite
  - 测试目录：tests/integration/（C2 集成）、tests/idempotency/（幂等）、tests/lineage/（Lineage）
  - 每个测试用例可独立运行，返回 0/非 0
  - 复用 TASK-012 的 compose.test.yml 启动测试 DB（若 TASK-012 未完成则用 conftest fixtures 直接连 PG）
- **Done When Code**: tests/integration/ + tests/idempotency/ + tests/lineage/ 目录与测试文件存在；conftest.py 提供 PG session fixture
- **Done When Behavior**: 全部测试在真实 PG 上通过；终态回退被拒；非法 run_type 被拒；audit UPDATE 抛异常
- **Done When Evidence**: pytest 全部 passed，exit 0；日志含真实 PG 连接信息

- **依赖**: [TASK-WI-0001-001, TASK-WI-0001-002, TASK-WI-0001-003, TASK-WI-0001-004, TASK-WI-0001-005]
- **refs**: [DD-CORE-001, DD-CORE-002, DD-CORE-003, DD-CORE-004, DD-CORE-005, DD-CORE-006, DD-CORE-008, DD-CORE-009, DD-CORE-010, DD-CORE-011, DD-CORE-012, DD-CORE-013, REQ-CORE-001, REQ-CORE-002, REQ-CORE-003, REQ-CORE-004, REQ-CORE-005, REQ-CORE-006, REQ-CORE-008, REQ-CORE-010, REQ-CORE-011, REQ-CORE-012, REQ-CORE-013, REQ-CORE-014, REQ-CORE-015]
- files: [tests/conftest.py, tests/integration/test_state_machine.py, tests/integration/test_idempotency.py, tests/integration/test_raw_evidence.py, tests/integration/test_clean_version.py, tests/integration/test_quality_gate.py, tests/integration/test_datagap_verified.py, tests/lineage/test_lineage_edge.py, tests/idempotency/test_force_rerun.py]
- **verification_commands**:
  - integration:
    - `python -m pytest tests/integration/ tests/idempotency/ tests/lineage/ -v --tb=short`
- **verification_evidence_expected**:
  - command: `python -m pytest tests/integration/ tests/idempotency/ tests/lineage/`, expected_exit_code: 0, expected_output_pattern: "passed", evidence_type: test_output
- **out_of_scope**: C3 查询测试（TASK-011）、C4 运维测试（TASK-016）、端到端验收（TASK-017）

---

## 检查点 C3: 查询与防未来（S2-016—S2-019）

---

### TASK-WI-0001-007 实现 DataContext 模块 app/datacontext/

**context_block**（executor 必读）：
- **What**: 新建 `app/datacontext/` 模块（DD-CORE-014）：`__init__.py`, `context.py`（DataContext 查询入口）, `query.py`（QueryContext/Frequency/AdjustmentPolicy/QualityPolicy/SecurityScope 值对象）, `time_semantics.py`（TimeMode + resolve_cutoff）, `adjustment.py`（apply_adjustment 动态复权）, `alignment.py`（多频率对齐按 trade_calendar）, `readers/daily.py`, `readers/minute.py`, `readers/financial.py`, `readers/event.py`。
- **Why**: 这是 P5 查询层的核心，满足 REQ-CORE-016（不读 RAW）、REQ-CORE-017（5 种查询模式）、REQ-CORE-018（6 频率对齐）、REQ-CORE-007（动态复权）。
- **Refs**: DD-CORE-014（模块结构 + 查询构造器）、DD-CORE-007（adjustment.py 复权）、DD-CORE-016（time_semantics.py）、CP-CORE-003（复权不变性）、CP-CORE-006（防未来不变性）
- **Current Implementation**:
  - 无 `app/datacontext/` 目录
  - 查询直接通过 `app/lineage/service.py` 的 `data_lineage` 硬编码逐表
  - CLEAN 模型在 `app/storage/models/clean.py`（有 _available_at/_quality_status/_published_at 由 TASK-002 添加）
  - 依据来源：CODE_OBSERVED + DESIGN
- **Constraints**:
  - **DataContext 严禁 import `app.storage.models.raw`**（REQ-CORE-016 硬约束）
  - 只引用 clean/quality/meta/lineage schema
  - query 查询强制注入 `available_at <= min(as_of_time, available_at_cutoff)`
  - query_minute 在 mode=full_market 时拒绝执行（返回错误，避免全表扫描）
  - 周/月聚合遵循 trade_calendar 而非自然日历
  - 复权计算不修改原始未复权值；因子断点返回 WARNING
  - 新建 `import-linter` 配置（或等价静态检查）强制 datacontext 不依赖 raw
  - 不引入新依赖（用现有 SQLAlchemy + pydantic）
- **Done When Code**: app/datacontext/ 全部文件存在；DataContext 类含 query_daily/query_minute/query_financial/query_events；import-linter 配置存在
- **Done When Behavior**: DataContext 查询返回 available_at 约束后的数据；全市场分钟查询被拒；复权动态计算正确；多频率按交易日历对齐
- **Done When Evidence**: import-linter 检查通过（无 raw 依赖）；单测覆盖 5 查询模式 + 6 频率；真实 PG 集成测试

- **依赖**: [TASK-WI-0001-001, TASK-WI-0001-002]
- **refs**: [DD-CORE-014, DD-CORE-007, DD-CORE-016, CP-CORE-003, CP-CORE-006, REQ-CORE-007, REQ-CORE-016, REQ-CORE-017, REQ-CORE-018, REQ-CORE-022]
- files: [app/datacontext/__init__.py, app/datacontext/context.py, app/datacontext/query.py, app/datacontext/time_semantics.py, app/datacontext/adjustment.py, app/datacontext/alignment.py, app/datacontext/readers/__init__.py, app/datacontext/readers/daily.py, app/datacontext/readers/minute.py, app/datacontext/readers/financial.py, app/datacontext/readers/event.py, .importlinter, pyproject.toml]
- **verification_commands**:
  - unit:
    - `python -m pytest tests/unit/test_datacontext_query.py -v`
    - `python -m pytest tests/unit/test_adjustment.py -v`
    - `python -m pytest tests/unit/test_time_semantics.py -v`
    - `lint-imports`
  - integration:
    - `python -m pytest tests/integration/test_datacontext_queries.py -v`
- **verification_evidence_expected**:
  - command: `lint-imports`, expected_exit_code: 0, evidence_type: lint_output
  - command: `python -m pytest tests/unit/test_datacontext_query.py`, expected_exit_code: 0, evidence_type: test_output
- **out_of_scope**: 统一查询 API 路由（TASK-010）、DataSnapshot 业务逻辑（TASK-008）、防未来测试套件（TASK-009）

---

### TASK-WI-0001-008 实现 DataSnapshot 构建与不可变约束

**context_block**（executor 必读）：
- **What**: 新建 `app/storage/models/snapshot.py`（DataSnapshot + DataSnapshotInput ORM，映射 TASK-001 创建的表）；实现 DataSnapshot 构建服务（DD-CORE-015）：BUILDING→READY 流转、content_fingerprint 计算（sha256 排序输入 CleanBatch content_hash）、质量门禁（DD-CORE-009 filter_by_quality：FAILED 永久阻断、WARNING 按 policy）、输入引用记录、READY 不可变。
- **Why**: 满足 REQ-CORE-019（READY 不可变）、REQ-CORE-020（输入可复现 + 重复查询一致）、REQ-CORE-010（FAILED 阻断）、REQ-CORE-011（WARNING 策略）。
- **Refs**: DD-CORE-015（DataSnapshot 模型 + 指纹 + 不可变）、DD-CORE-009（质量门禁 filter_by_quality）、CP-CORE-004（财务修订不变性，复用版本逻辑）、CP-CORE-005（DataSnapshot 不变性）
- **Current Implementation**:
  - data_snapshot/data_snapshot_input 表由 TASK-001 创建，无 ORM 模型
  - 无 DataSnapshot 构建逻辑
  - 质量状态字段 _quality_status 已存在（PASSED/WARNING/FAILED）
  - 依据来源：CODE_OBSERVED + DESIGN
- **Constraints**:
  - READY 不可变由 TASK-001 触发器 + 本 task 应用层双保险
  - content_fingerprint = sha256(排序后输入 CleanBatch content_hash 拼接)，相同输入重建相同 fingerprint
  - filter_by_quality 统计 skipped_failed_count/warning_published_count/warning_excluded_count
  - 修正通过新建 snapshot(supersedes_snapshot_id) 或 INVALIDATED，禁止原地改
  - 查询结果由固定 CleanBatch 集合决定，保证可复现
- **Done When Code**: snapshot.py ORM 存在；构建服务存在；质量门禁函数存在
- **Done When Behavior**: BUILDING→READY 成功；READY 后 UPDATE 被触发器拒绝；相同输入重建相同 fingerprint；FAILED 被排除
- **Done When Evidence**: 集成测试覆盖状态流转、不可变、指纹一致、质量门禁

- **依赖**: [TASK-WI-0001-001, TASK-WI-0001-007]
- **refs**: [DD-CORE-009, DD-CORE-015, CP-CORE-004, CP-CORE-005, REQ-CORE-010, REQ-CORE-011, REQ-CORE-019, REQ-CORE-020]
- files: [app/storage/models/snapshot.py, app/storage/models/__init__.py, app/datacontext/snapshot_builder.py]
- **verification_commands**:
  - unit:
    - `python -m pytest tests/unit/test_snapshot_fingerprint.py -v`
    - `python -m pytest tests/unit/test_quality_gate_filter.py -v`
  - integration:
    - `python -m pytest tests/integration/test_snapshot_immutability.py -v`
- **verification_evidence_expected**:
  - command: `python -m pytest tests/integration/test_snapshot_immutability.py`, expected_exit_code: 0, evidence_type: test_output
- **out_of_scope**: lineage_edge SNAPSHOT_INPUT 边写入（TASK-004 扩展）、API 暴露 Snapshot（TASK-010）

---

### TASK-WI-0001-009 实现防未来函数规则与测试套件

**context_block**（executor 必读）：
- **What**: 实现 DD-CORE-016 防未来函数完整规则：TimeMode 三模式（research/strategy/backtest）、published_at/available_at 分离计算（available_at = published_at + silence_days）、历史股票池与历史状态按时点查询（StockPoolVersion 当前用 single scope 占位，历史状态走 stock_suspend_event/stock_limit_price 按时点）；编写防未来测试套件 `tests/anti_lookahead/` 覆盖 6 类场景。
- **Why**: 满足 REQ-CORE-021（三模式时间语义）、REQ-CORE-022（发布/可用时间分离）、REQ-CORE-023（历史状态按时点）、REQ-CORE-024（防未来测试套件 100% pass）。
- **Refs**: DD-CORE-016（time_semantics 完整 + 6 类测试场景）、CP-CORE-006（防未来不变性）、CP-CORE-003（复权因子时点）
- **Current Implementation**:
  - time_semantics.py 基础由 TASK-007 创建（resolve_cutoff）
  - published_at 由 TASK-002 迁移添加
  - 无防未来测试套件
  - 依据来源：DESIGN
- **Constraints**:
  - backtest_mode 严格 available_at <= as_of_time（读取未来记录数 = 0）
  - research_mode 返回 latest_available_at 标注
  - silence_days 从 DataItem.availability_rule 解析（默认 0）
  - 查询上限用 available_at 不用 published_at
  - 6 类测试：backtest_mode 约束、available_at 注入、published/available 分离、历史股票池、历史状态、复权因子时点
  - 测试用真实 PG
- **Done When Code**: time_semantics.py 含 silence_days 计算；历史状态按时点查询函数；tests/anti_lookahead/ 6 测试文件
- **Done When Behavior**: backtest_mode 下任一查询不读未来数据；published_at ≠ available_at 时查询用后者
- **Done When Evidence**: anti_lookahead 全部 passed；已知未来函数数 = 0

- **依赖**: [TASK-WI-0001-002, TASK-WI-0001-007]
- **refs**: [DD-CORE-016, CP-CORE-003, CP-CORE-006, REQ-CORE-021, REQ-CORE-022, REQ-CORE-023, REQ-CORE-024]
- files: [app/datacontext/time_semantics.py, app/datacontext/readers/event.py, tests/anti_lookahead/test_backtest_mode.py, tests/anti_lookahead/test_available_at_injection.py, tests/anti_lookahead/test_published_available_separation.py, tests/anti_lookahead/test_historical_pool.py, tests/anti_lookahead/test_historical_status.py, tests/anti_lookahead/test_adjustment_factor_timepoint.py]
- **verification_commands**:
  - integration:
    - `python -m pytest tests/anti_lookahead/ -v`
- **verification_evidence_expected**:
  - command: `python -m pytest tests/anti_lookahead/`, expected_exit_code: 0, expected_output_pattern: "passed", evidence_type: test_output
- **out_of_scope**: StockPoolVersion 完整模型（属第3步未来阶段，当前 single scope 占位）

---

### TASK-WI-0001-010 实现统一查询 API 路由 app/api/routes/data.py

**context_block**（executor 必读）：
- **What**: 新建 `app/api/routes/data.py`（DD-CORE-017）：/api/v1/data 下 daily/minute/financial/events/calendar/securities 路由，通过 DataContext 执行查询；DataResponse + DataResponseMetadata 模型；statement_timeout 超时机制（504）；错误脱敏。
- **Why**: 满足 REQ-CORE-025（4 类数据覆盖）、REQ-CORE-026（元数据说明）、REQ-CORE-027（超时 + 长任务分离）、REQ-CORE-028（运维查询不扫描分钟表）。
- **Refs**: DD-CORE-017（API 设计 + 超时 + 脱敏）、REQ-CORE-028（运维查询走 DataWatermark）
- **Current Implementation**:
  - `app/api/routes/` 有 lineage.py, ops.py, system.py，无数据查询路由
  - DataContext 由 TASK-007 提供
  - query_timeout_seconds 配置由 TASK-005 添加到 config.py
  - ops.data_watermark 表存在（运维查询汇总源）
  - 依据来源：CODE_OBSERVED + DESIGN
- **Constraints**:
  - 路由只做只读 SELECT，长任务返回 task_id
  - 每次查询前 `SET LOCAL statement_timeout = query_timeout_seconds*1000`，超时返回 504 释放连接
  - 响应含 metadata: data_source, quality_policy_version, available_at_cutoff, schema_version, rule_version
  - WARNING 数据标注 quality_status；复权标注 adjustment_policy
  - 运维查询（水位/缺口）走 ops.data_watermark，不走 clean.stock_minute 全表扫描
  - 错误响应不含堆栈/密钥/Token
  - 全市场分钟查询走分区裁剪 + security_code 索引
- **Done When Code**: data.py 路由存在；DataResponse 模型存在；路由注册到 main app
- **Done When Behavior**: 4 类数据查询通过 DataContext 返回；超时返回 504；响应含元数据；运维查询 EXPLAIN 无 Seq Scan on clean_stock_minute
- **Done When Evidence**: API 契约测试通过；超时测试 504；EXPLAIN ANALYZE 无全表扫描；p95 ≤ 1s（运维）/≤2s（单股日线）

- **依赖**: [TASK-WI-0001-007]
- **refs**: [DD-CORE-017, REQ-CORE-025, REQ-CORE-026, REQ-CORE-027, REQ-CORE-028]
- files: [app/api/routes/data.py, app/api/routes/__init__.py, app/main.py, app/api/schemas/data.py]
- **verification_commands**:
  - unit:
    - `python -m pytest tests/unit/test_data_api_response_schema.py -v`
  - integration:
    - `python -m pytest tests/contract/test_data_api.py -v`
    - `python -m pytest tests/integration/test_api_timeout.py -v`
    - `python -m pytest tests/integration/test_ops_query_no_seqscan.py -v`
- **verification_evidence_expected**:
  - command: `python -m pytest tests/contract/test_data_api.py`, expected_exit_code: 0, evidence_type: test_output
  - command: `python -m pytest tests/integration/test_ops_query_no_seqscan.py`, expected_exit_code: 0, evidence_type: test_output
- **out_of_scope**: DataContext 内部实现（TASK-007）、认证授权（未来阶段）

---

### TASK-WI-0001-011 编写 C3 阶段测试套件

**context_block**（executor 必读）：
- **What**: 编写 C3 阶段测试：DataContext 5 查询模式集成、6 频率对齐、复权动态计算、DataSnapshot 不可变 + 指纹一致、防未来 6 场景（TASK-009 已建部分，本 task 补 API 契约与元数据）、API 超时 504、运维查询无全表扫描 EXPLAIN 证据、published/available 分离查询验证。
- **Why**: 守护 C3 阶段 REQ-CORE-016—REQ-CORE-028 的真实行为与性能目标。
- **Refs**: DD-CORE-014—DD-CORE-017、REQ-CORE-016—REQ-CORE-028
- **Current Implementation**:
  - TASK-007/008/009/010 已建部分单测；本 task 补契约测试与性能测试
  - 依据来源：DESIGN
- **Constraints**:
  - 真实 PG/TimescaleDB
  - 性能测试记录 p95（单股10年日线≤2s, 100股5年≤5s, 单股1年分钟≤5s, 运维≤1s）
  - 契约测试验证响应 schema（rows + metadata）
- **Done When Code**: tests/contract/ + tests/integration/ C3 相关测试存在
- **Done When Behavior**: 全部 passed；性能达标
- **Done When Evidence**: pytest passed + 性能日志

- **依赖**: [TASK-WI-0001-007, TASK-WI-0001-008, TASK-WI-0001-009, TASK-WI-0001-010]
- **refs**: [DD-CORE-014, DD-CORE-015, DD-CORE-016, DD-CORE-017, REQ-CORE-016, REQ-CORE-017, REQ-CORE-018, REQ-CORE-019, REQ-CORE-020, REQ-CORE-021, REQ-CORE-022, REQ-CORE-023, REQ-CORE-024, REQ-CORE-025, REQ-CORE-026, REQ-CORE-027, REQ-CORE-028]
- files: [tests/contract/test_data_api.py, tests/integration/test_api_timeout.py, tests/integration/test_ops_query_no_seqscan.py, tests/integration/test_datacontext_queries.py, tests/integration/test_snapshot_immutability.py, tests/integration/test_perf_queries.py]
- **verification_commands**:
  - integration:
    - `python -m pytest tests/contract/ tests/integration/test_datacontext_queries.py tests/integration/test_snapshot_immutability.py tests/integration/test_api_timeout.py tests/integration/test_ops_query_no_seqscan.py tests/integration/test_perf_queries.py -v`
- **verification_evidence_expected**:
  - command: pytest C3 suite, expected_exit_code: 0, evidence_type: test_output
- **out_of_scope**: 端到端 10×8 矩阵（TASK-017）

---

## 检查点 C4: 环境、迁盘、容量和恢复（S2-020—S2-023）

---

### TASK-WI-0001-012 创建 server-test compose 配置

**context_block**（executor 必读）：
- **What**: 新建 `compose.test.yml`（DD-CORE-018）和 `.env.test` 模板：独立 project(quantstock1-test)、独立 DB(postgres quantstock1_test)、独立端口(DB 15432, API 19000)、独立 volume(quantstock1_test_pgdata)；应用启动配置校验（QUANTSTOCK1_ENV=test 时拒绝连非 test 库）。
- **Why**: 满足 REQ-CORE-031（与 stable 完全隔离），为所有测试与迁盘演练提供安全环境。
- **Refs**: DD-CORE-018（compose 配置 + 隔离保证）
- **Current Implementation**:
  - 只有 `compose.dev.yml`（project=quantstock1-dev, API port=18000, DB 未映射端口）
  - 依据来源：CODE_OBSERVED
- **Constraints**:
  - project name / DB 名/用户/密码 / 端口 / volume 全部与 dev/stable 不同
  - image: timescale/timescaledb:2.28.3-pg16
  - 应用启动检查 QUANTSTOCK1_ENV，连非 test 库拒绝启动
  - 不影响 stable 运行（不共用进程/端口）
  - 不自动启动 stable 操作
- **Done When Code**: compose.test.yml + .env.test 存在；config.py 含 ENV 校验
- **Done When Behavior**: `docker compose -f compose.test.yml up` 启动 test 环境；stable 不受影响；误连 stable 被拒
- **Done When Evidence**: test 环境健康检查通过；端口不冲突验证；配置校验拒绝误连测试

- **依赖**: 无
- **refs**: [DD-CORE-018, REQ-CORE-031]
- files: [compose.test.yml, .env.test.example, app/core/config.py]
- **verification_commands**:
  - integration:
    - `docker compose -f compose.test.yml config`
    - `python -c "import yaml; c=yaml.safe_load(open('compose.test.yml')); assert c['name']=='quantstock1-test'; assert 'quantstock1_test_pgdata' in c['volumes']"`
  - e2e:
    - `docker compose -f compose.test.yml up -d --wait`
- **verification_evidence_expected**:
  - command: `docker compose -f compose.test.yml config`, expected_exit_code: 0, evidence_type: compose_validation
- **out_of_scope**: stable compose 修改、迁盘脚本（TASK-013）、备份脚本（TASK-014）

---

### TASK-WI-0001-013 创建数据库迁盘脚本

**context_block**（executor 必读）：
- **What**: 新建 `scripts/db_migrate_disk/` 目录（DD-CORE-019）：`precheck.sh`（预检：磁盘空间/权限/PG版本/连接）、`migrate.sh`（生成迁盘命令序列，不自动执行）、`rollback.sh`（回滚步骤）。6 阶段：预检→停止→复制→启动→验证→回滚。
- **Why**: 满足 REQ-CORE-029（迁盘脚本 + 预检 + 回滚 + 不自动执行 stable 不可逆操作）。
- **Refs**: DD-CORE-019（6 阶段 + WAITING_USER_EXECUTION）
- **Current Implementation**:
  - 无迁盘脚本
  - 依据来源：DESIGN
- **Constraints**:
  - 脚本输出完整可复制命令序列，标记 WAITING_USER_EXECUTION
  - 不自动执行 5 类高风险动作：迁盘、删旧卷、开端口、替换正式数据库、扩大分钟历史
  - 预检失败（空间不足/权限/PG版本不匹配）中止并报告
  - 提供回滚步骤恢复原系统盘
  - 在 server-test 环境演练
- **Done When Code**: scripts/db_migrate_disk/{precheck,migrate,rollback}.sh 存在
- **Done When Behavior**: precheck 检测空间/权限/版本；migrate 输出命令不执行；rollback 提供恢复步骤
- **Done When Evidence**: precheck 失败场景测试；server-test 演练记录

- **依赖**: [TASK-WI-0001-012]
- **refs**: [DD-CORE-019, REQ-CORE-029]
- files: [scripts/db_migrate_disk/precheck.sh, scripts/db_migrate_disk/migrate.sh, scripts/db_migrate_disk/rollback.sh, scripts/db_migrate_disk/README.md]
- **verification_commands**:
  - integration:
    - `bash scripts/db_migrate_disk/precheck.sh`
  - e2e:
    - `bash scripts/db_migrate_disk/migrate.sh --dry-run`
- **verification_evidence_expected**:
  - command: `bash scripts/db_migrate_disk/migrate.sh --dry-run`, expected_exit_code: 0, expected_output_pattern: "WAITING_USER_EXECUTION", evidence_type: script_output
- **out_of_scope**: 实际 stable 迁盘执行（用户操作）、备份恢复（TASK-014）

---

### TASK-WI-0001-014 创建备份恢复脚本

**context_block**（executor 必读）：
- **What**: 新建 `scripts/db_backup/`（full_backup.sh + manifest.json 模板）和 `scripts/db_restore/`（restore.sh + verify.sh）（DD-CORE-020）。全量备份 pg_dump --format=custom + .sha256 + manifest（时间/版本/大小/checksum）；恢复到独立 PG 后验证 3 项（Alembic 版本/表行数/checksum）+ 应用健康检查。
- **Why**: 满足 REQ-CORE-032（全量备份 + 4 属性 + 服务器外副本 + 不含明文密钥）、REQ-CORE-033（恢复脚本 + 3 项验证 + 健康检查 + RTO）。
- **Refs**: DD-CORE-020（备份恢复设计）
- **Current Implementation**:
  - 无备份恢复脚本
  - 依据来源：DESIGN
- **Constraints**:
  - 备份文件含时间/PG版本/大小/checksum 4 属性
  - 至少保留一个服务器外副本（配置说明）
  - 备份不含明文密钥（pg_dump 排除或占位）
  - RPO: 配置/审计 ≤4h, 市场数据 ≤24h；RTO 同
  - 恢复后验证 Alembic 版本一致、关键表行数一致、checksum 一致
  - 恢复库误连 stable 被配置校验拒绝
  - 标记 WAITING_USER_EXECUTION（对 stable 操作）
- **Done When Code**: scripts/db_backup/ + scripts/db_restore/ 文件存在
- **Done When Behavior**: 备份生成 .dump + .sha256 + manifest；恢复后 3 项验证通过；/health 返回 200
- **Done When Evidence**: server-test 备份恢复演练日志；checksum 对账一致

- **依赖**: [TASK-WI-0001-012]
- **refs**: [DD-CORE-020, REQ-CORE-032, REQ-CORE-033]
- files: [scripts/db_backup/full_backup.sh, scripts/db_backup/manifest.json, scripts/db_backup/README.md, scripts/db_restore/restore.sh, scripts/db_restore/verify.sh, scripts/db_restore/README.md]
- **verification_commands**:
  - integration:
    - `bash scripts/db_backup/full_backup.sh --target /tmp/test_backup`
    - `bash scripts/db_restore/verify.sh --backup /tmp/test_backup/test.dump`
  - e2e:
    - `bash scripts/db_restore/restore.sh --backup /tmp/test_backup/test.dump --dry-run`
- **verification_evidence_expected**:
  - command: backup+verify, expected_exit_code: 0, evidence_type: script_output
- **out_of_scope**: stable 实际备份执行（用户操作）、分钟压缩（TASK-015）

---

### TASK-WI-0001-015 创建分钟压缩归档基准脚本

**context_block**（executor 必读）：
- **What**: 新建 `scripts/minute_archive/`（compress_policy.sql + archive.sh）（DD-CORE-020）。为 clean.stock_minute hypertable 配置 TimescaleDB 压缩策略（segmentby=security_code, orderby=trade_time DESC, policy INTERVAL '7 days'）；归档脚本导出超期分区 + checksum；恢复校验行数一致。
- **Why**: 满足 REQ-CORE-030（压缩策略 + 压缩比基准 + 归档 checksum + 恢复一致）。
- **Refs**: DD-CORE-020（分钟压缩归档）
- **Current Implementation**:
  - clean.stock_minute 已是 TimescaleDB hypertable（0012 创建）
  - 无压缩策略，无归档脚本
  - 依据来源：CODE_OBSERVED + DESIGN
- **Constraints**:
  - 记录压缩前后空间占用与压缩比
  - 归档文件含 checksum，恢复校验行数与 checksum 一致（差异=0）
  - 迁盘/压缩/归档/恢复完成前禁止扩大全市场分钟历史
  - 标记 WAITING_USER_EXECUTION（stable 压缩策略应用）
- **Done When Code**: scripts/minute_archive/ 文件存在
- **Done When Behavior**: 压缩策略 SQL 可执行；归档生成 checksum；恢复行数一致
- **Done When Evidence**: server-test 压缩比基准日志；归档恢复对账

- **依赖**: [TASK-WI-0001-012]
- **refs**: [DD-CORE-020, REQ-CORE-030]
- files: [scripts/minute_archive/compress_policy.sql, scripts/minute_archive/archive.sh, scripts/minute_archive/README.md]
- **verification_commands**:
  - integration:
    - `psql -f scripts/minute_archive/compress_policy.sql`
  - e2e:
    - `bash scripts/minute_archive/archive.sh --dry-run`
- **verification_evidence_expected**:
  - command: compress_policy, expected_exit_code: 0, evidence_type: sql_output
- **out_of_scope**: stable 压缩策略执行（用户操作）、全市场分钟扩展（禁止，前置未完成）

---

### TASK-WI-0001-016 编写 C4 阶段测试与验证脚本

**context_block**（executor 必读）：
- **What**: 编写 C4 阶段测试：server-test 隔离验证（端口/卷/project 不冲突 + 误连拒绝）、迁盘预检失败场景、备份 checksum 校验、恢复后 3 项验证（Alembic/行数/checksum）+ /health 200、压缩比基准记录、归档恢复行数一致。
- **Why**: 守护 REQ-CORE-029—REQ-CORE-033 的运维能力真实可用。
- **Refs**: DD-CORE-018—DD-CORE-020、REQ-CORE-029—REQ-CORE-033
- **Current Implementation**:
  - TASK-012/013/014/015 已建脚本；本 task 补测试与演练验证
  - 依据来源：DESIGN
- **Constraints**:
  - 测试在 server-test 真实环境执行
  - stable 操作标记 WAITING_USER_EXECUTION，测试只验证脚本逻辑不执行 stable
  - 备份恢复演练记录（每月至少一次的机制说明）
- **Done When Code**: tests/backup_restore/ + tests/fault_recovery/ 文件存在
- **Done When Behavior**: 隔离验证通过；预检失败被识别；备份恢复对账一致
- **Done When Evidence**: pytest passed + 演练日志

- **依赖**: [TASK-WI-0001-012, TASK-WI-0001-013, TASK-WI-0001-014, TASK-WI-0001-015]
- **refs**: [DD-CORE-018, DD-CORE-019, DD-CORE-020, REQ-CORE-029, REQ-CORE-030, REQ-CORE-031, REQ-CORE-032, REQ-CORE-033]
- files: [tests/backup_restore/test_backup_checksum.py, tests/backup_restore/test_restore_verify.py, tests/fault_recovery/test_server_test_isolation.py, tests/fault_recovery/test_migrate_precheck.py]
- **verification_commands**:
  - integration:
    - `python -m pytest tests/backup_restore/ tests/fault_recovery/ -v`
- **verification_evidence_expected**:
  - command: pytest C4 suite, expected_exit_code: 0, evidence_type: test_output
- **out_of_scope**: stable 实际运维执行、端到端验收（TASK-017）

---

## 检查点 C5: 集成、部署和验收（S2-024—S2-025）

---

### TASK-WI-0001-017 编写集成测试与端到端验收

**context_block**（executor 必读）：
- **What**: 编写 Alembic 空库升级测试（0001→head）+ 现有库升级预检（0012→head）；端到端 10 DataItem × 8 阶段测试矩阵（采集→RAW→CLEAN→QUALITY→Lineage→Snapshot→DataContext→API），每用例记录 12 项证据，结论 PASS/FAIL/BLOCKED；覆盖率配置（普通≥80%, 核心≥90% 分支）。
- **Why**: 满足 REQ-CORE-034（10 类测试 + 真实 PG + 覆盖率）、REQ-CORE-035（端到端 10×8 + 12 项证据 + 结论仅 PASS/FAIL/BLOCKED）。
- **Refs**: DD-CORE-021（测试目录 + 10 类测试 + 端到端矩阵）
- **Current Implementation**:
  - 各阶段测试（TASK-006/011/016）已建；本 task 补 Alembic 升级测试 + 端到端矩阵 + 覆盖率配置
  - 依据来源：DESIGN
- **Constraints**:
  - Alembic 空库从 0001 升级到 head 成功；现有库从 0012 升级成功
  - 端到端在真实 PG/TimescaleDB，不得仅 Mock
  - 10 DataItem: trade_calendar, stock_basic, stock_daily, stock_adj_factor, stock_daily_basic, stock_suspend, stock_limit_price, stock_minute, financial_income, financial_indicator
  - 8 阶段全覆盖
  - 12 项证据：用例ID/关联S2/环境/提交/镜像Digest/迁移版本/数据范围/命令/期望/实际/日志/结论
  - stable 操作未执行时最多 BLOCKED/WAITING_USER_EXECUTION
  - 覆盖率配置加入 pyproject.toml（coverage.py）
- **Done When Code**: tests/alembic/ + tests/e2e/ + coverage 配置存在
- **Done When Behavior**: 空库升级成功；端到端矩阵结论 PASS（或 stable 操作 BLOCKED）
- **Done When Evidence**: alembic 升级日志；端到端矩阵报告；覆盖率报告 ≥80%

- **依赖**: [TASK-WI-0001-001, TASK-WI-0001-002, TASK-WI-0001-003, TASK-WI-0001-004, TASK-WI-0001-005, TASK-WI-0001-006, TASK-WI-0001-007, TASK-WI-0001-008, TASK-WI-0001-009, TASK-WI-0001-010, TASK-WI-0001-011, TASK-WI-0001-012, TASK-WI-0001-013, TASK-WI-0001-014, TASK-WI-0001-015, TASK-WI-0001-016]
- **refs**: [DD-CORE-021, REQ-CORE-034, REQ-CORE-035]
- files: [tests/alembic/test_empty_upgrade.py, tests/alembic/test_existing_upgrade.py, tests/e2e/test_dataitem_matrix.py, tests/e2e/conftest.py, tests/e2e/evidence_template.json, pyproject.toml]
- **verification_commands**:
  - integration:
    - `python -m pytest tests/alembic/ -v`
    - `python -m pytest tests/e2e/ -v`
  - regression:
    - `python -m pytest --cov=app --cov-report=term-missing tests/`
- **verification_evidence_expected**:
  - command: `python -m pytest tests/alembic/`, expected_exit_code: 0, evidence_type: test_output
  - command: coverage report, expected_output_pattern: "TOTAL", evidence_type: coverage_report
- **out_of_scope**: 文档更新（TASK-018）、路线图更新（TASK-019）

---

### TASK-WI-0001-018 更新项目文档（实施记录、验收记录、部署说明）

**context_block**（executor 必读）：
- **What**: 更新项目文档：实施记录（docs/00_项目管理/）、验收记录（docs/06_测试验证/10_第2步数据底座验收计划.md 填充实际证据）、部署说明（server-test/迁盘/备份恢复操作手册）、填充 .specforge/config/prod-environment.md 和 project-rules.md（从 intake.md 推导的真实约束）。
- **Why**: 满足 REQ-CORE-035 的证据记录要求；使系统具备可运维性与可验收性。
- **Refs**: DD-CORE-021（验收证据）、REQ-CORE-035（12 项证据记录）
- **Current Implementation**:
  - prod-environment.md / project-rules.md 为 TODO 占位
  - 验收计划文档存在但未填充实际证据
  - 依据来源：CODE_OBSERVED
- **Constraints**:
  - prod-environment.md 填充 runtimes 段（Python >=3.11,<3.12, PG 16, TimescaleDB 2.28.3, svr3 4CPU）
  - project-rules.md 填充工程规则（配置不写死、风格匹配、不提交密钥等）
  - 验收记录引用真实测试日志，不得编造
  - stable 操作说明标记 WAITING_USER_EXECUTION
- **Done When Code**: 文档文件更新
- **Done When Behavior**: prod-environment.md / project-rules.md 非 TODO；验收记录含真实证据引用
- **Done When Evidence**: 文档检查无 "TODO: 由首次 intake"；验收记录含测试日志路径

- **依赖**: [TASK-WI-0001-017]
- **refs**: [DD-CORE-021, REQ-CORE-034, REQ-CORE-035]
- files: [.specforge/config/prod-environment.md, .specforge/config/project-rules.md, docs/00_项目管理/09_第2步数据底座实施记录.md, docs/06_测试验证/10_第2步数据底座验收计划.md, docs/09_运维手册/server_test_部署说明.md]
- **verification_commands**:
  - unit:
    - `python -c "assert 'TODO' not in open('.specforge/config/prod-environment.md', encoding='utf-8').read()"`
- **verification_evidence_expected**:
  - command: doc check, expected_exit_code: 0, evidence_type: file_check
- **out_of_scope**: 代码实现、测试编写

---

### TASK-WI-0001-019 更新路线图和任务总表状态

**context_block**（executor 必读）：
- **What**: 更新项目路线图与任务总表（docs/00_项目管理/08_第2步数据底座统一实施任务书.md 及路线图文档），标记 S2-002—S2-025 状态为已完成/BLOCKED（按实际验证结论）；记录迁移版本 0013-0015、新增模块清单、未决项（如共享枚举登记建议、StockPoolVersion 未来阶段）。
- **Why**: 满足完成判定（路线图与任务总表更新）；为第3步提供清晰交接。
- **Refs**: DD-CORE-021、REQ-CORE-035
- **Current Implementation**:
  - 任务书文档存在，状态待更新
  - 依据来源：CODE_OBSERVED
- **Constraints**:
  - 状态只标记 PASS/FAIL/BLOCKED，不得"基本通过"
  - stable 操作未执行标 WAITING_USER_EXECUTION
  - 记录建议登记的共享枚举（run_type/quality_status/frequency/time_mode/snapshot_status）
- **Done When Code**: 路线图/任务总表更新
- **Done When Behavior**: S2 任务状态准确反映验证结论
- **Done When Evidence**: 文档含更新状态

- **依赖**: [TASK-WI-0001-017]
- **refs**: [DD-CORE-021, REQ-CORE-035]
- files: [docs/00_项目管理/08_第2步数据底座统一实施任务书.md, docs/00_项目管理/07_项目路线图.md]
- **verification_commands**:
  - unit:
    - `python -c "t=open('docs/00_项目管理/08_第2步数据底座统一实施任务书.md', encoding='utf-8').read(); assert 'S2-002' in t"`
- **verification_evidence_expected**:
  - command: doc check, expected_exit_code: 0, evidence_type: file_check
- **out_of_scope**: 代码实现、测试编写、共享枚举实际登记（属 contract_change workflow，建议项）

---

## 任务依赖图与并行批次

```
批次 0（地基，可并行编写，按序应用迁移）:
  TASK-001 (mig 0013) ─┐
  TASK-002 (mig 0014) ─┼─ 串行 alembic 链 0013→0014→0015
  TASK-003 (mig 0015) ─┘
  TASK-012 (server-test compose)  # 独立

批次 1（C2 实现，依赖迁移）:
  TASK-004 (lineage service)   ← 001
  TASK-005 (catalog+LOST+gap)  ← 003
  TASK-013 (迁盘) ← 012
  TASK-014 (备份) ← 012
  TASK-015 (压缩) ← 012

批次 2（C3 实现，依赖迁移+DataContext）:
  TASK-007 (DataContext) ← 001,002
  TASK-008 (DataSnapshot) ← 001,007
  TASK-009 (防未来)      ← 002,007
  TASK-010 (API)         ← 007

批次 3（测试，依赖实现）:
  TASK-006 (C2 tests) ← 001-005
  TASK-011 (C3 tests) ← 007-010
  TASK-016 (C4 tests) ← 012-015

批次 4（验收，依赖全部）:
  TASK-017 (集成+e2e) ← 001-016
  TASK-018 (文档)     ← 017
  TASK-019 (路线图)   ← 017
```

## 自检清单

| # | 检查项 | 结果 |
|---|---|---|
| 1 | 每个 DD 都有对应 task 覆盖？ | PASS — DD-001→T005, DD-002→T005, DD-003→T003, DD-004→T005, DD-005→T003, DD-006→T002, DD-007→T007, DD-008→T002, DD-009→T008, DD-010→T003/T005, DD-011→T001/T004, DD-012→T003, DD-013→T003, DD-014→T007, DD-015→T001/T008, DD-016→T009, DD-017→T010, DD-018→T012, DD-019→T013, DD-020→T014/T015, DD-021→T006/T011/T016/T017 |
| 2 | 每个 REQ 都有 task 覆盖？ | PASS — 35 REQ 全覆盖（见 trace_delta.md） |
| 3 | 每个 task context_block 充分？ | PASS — 含 What/Why/Refs/Current Implementation/Constraints/Done When |
| 4 | verification_commands 可机器跑？ | PASS — 全部返回 exit code |
| 5 | 并行批次 task 独立？ | PASS — files 不重叠，依赖显式 |
| 6 | 共享代码先建？ | PASS — DataContext 值对象在 T007 统一建，迁移先于代码 |
| 7 | allowed_write_files 具体？ | PASS — 无通配符 |
| 8 | forbidden_files 含规格文档？ | PASS — 各 task out_of_scope 排除 |
| 9 | 迁移只新增不改旧？ | PASS — 0013-0015 只新增 |
| 10 | 真实 PG 测试？ | PASS — 所有 DB 测试强制真实 PG |
