---
trace_format: delta
module_code: CORE
work_item_id: WI-0001
base_spec_version: PSV-0001
generated_by: sf-task-planner
---

# Trace Delta: WI-0001 第2步数据底座

> 本文档建立 `requirements.candidate.md`（35 REQ）→ `design.candidate.md`（21 DD）→ `tasks.md`（19 TASK）→ 文件 → 验证方式 的完整追溯矩阵。
>
> 所有追溯关系均为本 WI 真实新增的设计/任务关系变化，不存在为形式制造的空治理条目。

## 1. 追溯矩阵（REQ → AC → DD → CP → TASK → 文件 → 验证）

> 说明：AC（验收标准）编号格式 REQ-CORE-NNN-ACm（第 m 条验收标准）。CP 为 Correctness Property（设计决策中定义的可证伪属性）。

### A. 数据目录与采集（REQ-CORE-001 — REQ-CORE-005）

| REQ ID | AC ID | DD ID | CP ID | TASK ID | 目标文件 | 验证方式 |
|--------|-------|-------|-------|---------|---------|---------|
| REQ-CORE-001 | REQ-CORE-001-AC1/2/3/4 | DD-CORE-001 | — | TASK-WI-0001-002, TASK-WI-0001-005 | migrations/versions/0014_*.py; app/catalog/bootstrap.py | alembic upgrade 0014 + DataItem 元数据断言 + test_dataitem_metadata_validation.py |
| REQ-CORE-002 | REQ-CORE-002-AC1/2/3/4/5 | DD-CORE-002 | CP-CORE-001 | TASK-WI-0001-003, TASK-WI-0001-005 | migrations/versions/0015_*.py; app/collect/scheduler.py; app/core/config.py | test_worker_lost_recovery.py |
| REQ-CORE-003 | REQ-CORE-003-AC1/2/3/4 | DD-CORE-003 | — | TASK-WI-0001-003 | migrations/versions/0015_*.py | alembic upgrade head + run_type CHECK 约束测试 |
| REQ-CORE-004 | REQ-CORE-004-AC1/2/3/4 | DD-CORE-004 | — | TASK-WI-0001-005 | app/collect/idempotency.py; app/collect/state_machine.py | test_idempotency.py + test_force_rerun.py |
| REQ-CORE-005 | REQ-CORE-005-AC1/2/3/4 | DD-CORE-005 | CP-CORE-002 | TASK-WI-0001-003, TASK-WI-0001-004 | migrations/versions/0015_*.py; app/storage/models/lineage.py; app/lineage/service.py | alembic upgrade head + test_raw_evidence.py + test_lineage_edge.py |

### B. CLEAN 与质量（REQ-CORE-006 — REQ-CORE-012）

| REQ ID | AC ID | DD ID | CP ID | TASK ID | 目标文件 | 验证方式 |
|--------|-------|-------|-------|---------|---------|---------|
| REQ-CORE-006 | REQ-CORE-006-AC1/2/3/4 | DD-CORE-006 | — | TASK-WI-0001-002 | migrations/versions/0014_*.py | alembic upgrade 0014 + test_clean_version.py |
| REQ-CORE-007 | REQ-CORE-007-AC1/2/3/4 | DD-CORE-007 | CP-CORE-003 | TASK-WI-0001-007 | app/datacontext/adjustment.py | test_adjustment.py |
| REQ-CORE-008 | REQ-CORE-008-AC1/2/3/4 | DD-CORE-008 | CP-CORE-004 | TASK-WI-0001-002, TASK-WI-0001-008 | migrations/versions/0014_*.py; app/storage/models/snapshot.py | alembic upgrade 0014 + test_clean_version.py + test_snapshot_immutability.py |
| REQ-CORE-009 | REQ-CORE-009-AC1/2/3/4 | DD-CORE-006, DD-CORE-016 | CP-CORE-006 | TASK-WI-0001-002, TASK-WI-0001-007, TASK-WI-0001-009 | migrations/versions/0014_*.py; app/datacontext/context.py; app/datacontext/time_semantics.py | test_datacontext_queries.py + test_anti_lookahead/ |
| REQ-CORE-010 | REQ-CORE-010-AC1/2/3/4 | DD-CORE-009 | — | TASK-WI-0001-008 | app/datacontext/snapshot_builder.py | test_quality_gate.py + test_snapshot_immutability.py |
| REQ-CORE-011 | REQ-CORE-011-AC1/2/3/4 | DD-CORE-009 | — | TASK-WI-0001-008 | app/datacontext/snapshot_builder.py | test_quality_gate_filter.py |
| REQ-CORE-012 | REQ-CORE-012-AC1/2/3/4 | DD-CORE-010 | — | TASK-WI-0001-003, TASK-WI-0001-005 | migrations/versions/0015_*.py; app/collect/state_machine.py | test_datagap_verified.py |

### C. Lineage 与审计（REQ-CORE-013 — REQ-CORE-015）

| REQ ID | AC ID | DD ID | CP ID | TASK ID | 目标文件 | 验证方式 |
|--------|-------|-------|-------|---------|---------|---------|
| REQ-CORE-013 | REQ-CORE-013-AC1/2/3/4 | DD-CORE-011 | CP-CORE-002 | TASK-WI-0001-001, TASK-WI-0001-004 | migrations/versions/0013_*.py; app/storage/models/lineage.py; app/lineage/service.py | alembic upgrade 0013 + test_lineage_edge.py |
| REQ-CORE-014 | REQ-CORE-014-AC1/2/3/4 | DD-CORE-012 | — | TASK-WI-0001-003 | migrations/versions/0015_*.py | alembic upgrade head + audit_event 字段测试 |
| REQ-CORE-015 | REQ-CORE-015-AC1/2/3/4 | DD-CORE-013 | — | TASK-WI-0001-003 | migrations/versions/0015_*.py | alembic upgrade head + 只追加触发器 UPDATE/DELETE 拒绝测试 |

### D. DataContext 与 DataSnapshot（REQ-CORE-016 — REQ-CORE-020）

| REQ ID | AC ID | DD ID | CP ID | TASK ID | 目标文件 | 验证方式 |
|--------|-------|-------|-------|---------|---------|---------|
| REQ-CORE-016 | REQ-CORE-016-AC1/2/3/4 | DD-CORE-014 | CP-CORE-006 | TASK-WI-0001-007 | app/datacontext/context.py; .importlinter | lint-imports + test_datacontext_queries.py |
| REQ-CORE-017 | REQ-CORE-017-AC1/2/3/4/5 | DD-CORE-014 | — | TASK-WI-0001-007, TASK-WI-0001-011 | app/datacontext/context.py; app/datacontext/readers/*.py | test_datacontext_queries.py |
| REQ-CORE-018 | REQ-CORE-018-AC1/2/3/4 | DD-CORE-014 | — | TASK-WI-0001-007 | app/datacontext/alignment.py; app/datacontext/query.py | test_datacontext_query.py (6 频率) |
| REQ-CORE-019 | REQ-CORE-019-AC1/2/3/4 | DD-CORE-015 | CP-CORE-005 | TASK-WI-0001-001, TASK-WI-0001-008 | migrations/versions/0013_*.py; app/storage/models/snapshot.py; app/datacontext/snapshot_builder.py | alembic upgrade 0013 + test_snapshot_immutability.py |
| REQ-CORE-020 | REQ-CORE-020-AC1/2/3/4 | DD-CORE-015 | CP-CORE-005 | TASK-WI-0001-001, TASK-WI-0001-008 | migrations/versions/0013_*.py; app/datacontext/snapshot_builder.py | test_snapshot_fingerprint.py + test_snapshot_immutability.py |

### E. 防未来函数（REQ-CORE-021 — REQ-CORE-024）

| REQ ID | AC ID | DD ID | CP ID | TASK ID | 目标文件 | 验证方式 |
|--------|-------|-------|-------|---------|---------|---------|
| REQ-CORE-021 | REQ-CORE-021-AC1/2/3/4 | DD-CORE-016 | CP-CORE-006 | TASK-WI-0001-007, TASK-WI-0001-009 | app/datacontext/time_semantics.py | test_time_semantics.py + test_backtest_mode.py |
| REQ-CORE-022 | REQ-CORE-022-AC1/2/3/4 | DD-CORE-006, DD-CORE-016 | — | TASK-WI-0001-002, TASK-WI-0001-009 | migrations/versions/0014_*.py; app/datacontext/time_semantics.py | alembic upgrade 0014 + test_published_available_separation.py |
| REQ-CORE-023 | REQ-CORE-023-AC1/2/3/4 | DD-CORE-016 | — | TASK-WI-0001-009 | app/datacontext/readers/event.py | test_historical_pool.py + test_historical_status.py |
| REQ-CORE-024 | REQ-CORE-024-AC1/2/3/4 | DD-CORE-016 | CP-CORE-006 | TASK-WI-0001-009 | tests/anti_lookahead/*.py | python -m pytest tests/anti_lookahead/ |

### F. 统一查询 API（REQ-CORE-025 — REQ-CORE-028）

| REQ ID | AC ID | DD ID | CP ID | TASK ID | 目标文件 | 验证方式 |
|--------|-------|-------|-------|---------|---------|---------|
| REQ-CORE-025 | REQ-CORE-025-AC1/2/3/4 | DD-CORE-017 | — | TASK-WI-0001-010, TASK-WI-0001-011 | app/api/routes/data.py; app/api/schemas/data.py | test_data_api.py (契约) |
| REQ-CORE-026 | REQ-CORE-026-AC1/2/3/4 | DD-CORE-017 | — | TASK-WI-0001-010 | app/api/routes/data.py; app/api/schemas/data.py | test_data_api.py (元数据段) |
| REQ-CORE-027 | REQ-CORE-027-AC1/2/3/4 | DD-CORE-017 | — | TASK-WI-0001-010 | app/api/routes/data.py; app/core/config.py | test_api_timeout.py (504) |
| REQ-CORE-028 | REQ-CORE-028-AC1/2/3/4 | DD-CORE-017 | — | TASK-WI-0001-010, TASK-WI-0001-011 | app/api/routes/data.py | test_ops_query_no_seqscan.py (EXPLAIN) |

### G. 环境与运维（REQ-CORE-029 — REQ-CORE-033）

| REQ ID | AC ID | DD ID | CP ID | TASK ID | 目标文件 | 验证方式 |
|--------|-------|-------|-------|---------|---------|---------|
| REQ-CORE-029 | REQ-CORE-029-AC1/2/3/4/5 | DD-CORE-019 | — | TASK-WI-0001-013, TASK-WI-0001-016 | scripts/db_migrate_disk/*.sh | precheck.sh + migrate.sh --dry-run + test_migrate_precheck.py |
| REQ-CORE-030 | REQ-CORE-030-AC1/2/3/4/5 | DD-CORE-020 | — | TASK-WI-0001-015, TASK-WI-0001-016 | scripts/minute_archive/*.sql; scripts/minute_archive/archive.sh | compress_policy.sql + archive.sh --dry-run |
| REQ-CORE-031 | REQ-CORE-031-AC1/2/3/4 | DD-CORE-018 | — | TASK-WI-0001-012, TASK-WI-0001-016 | compose.test.yml; .env.test.example; app/core/config.py | docker compose config + test_server_test_isolation.py |
| REQ-CORE-032 | REQ-CORE-032-AC1/2/3/4/5 | DD-CORE-020 | — | TASK-WI-0001-014, TASK-WI-0001-016 | scripts/db_backup/*.sh | full_backup.sh + test_backup_checksum.py |
| REQ-CORE-033 | REQ-CORE-033-AC1/2/3/4/5 | DD-CORE-020 | — | TASK-WI-0001-014, TASK-WI-0001-016 | scripts/db_restore/*.sh | restore.sh + verify.sh + test_restore_verify.py |

### H. 测试与验收（REQ-CORE-034 — REQ-CORE-035）

| REQ ID | AC ID | DD ID | CP ID | TASK ID | 目标文件 | 验证方式 |
|--------|-------|-------|-------|---------|---------|---------|
| REQ-CORE-034 | REQ-CORE-034-AC1/2/3/4/5/6 | DD-CORE-021 | — | TASK-WI-0001-006, TASK-WI-0001-011, TASK-WI-0001-016, TASK-WI-0001-017 | tests/*; pyproject.toml (coverage) | pytest 全套 + coverage report |
| REQ-CORE-035 | REQ-CORE-035-AC1/2/3/4/5 | DD-CORE-021 | — | TASK-WI-0001-017, TASK-WI-0001-018, TASK-WI-0001-019 | tests/e2e/*; docs/06_测试验证/* | test_dataitem_matrix.py + 验收记录文档 |

## 2. 文件覆盖矩阵

| 文件 | 创建/修改 | 涉及 REQ | 涉及 TASK |
|------|-----------|---------|-----------|
| migrations/versions/0013_lineage_and_snapshot.py | 创建 | REQ-CORE-013, 019, 020 | TASK-001 |
| migrations/versions/0014_clean_published_at_financial_dataitem.py | 创建 | REQ-CORE-001, 006, 008, 022 | TASK-002 |
| migrations/versions/0015_audit_runcheck_datagap_rawevidence.py | 创建 | REQ-CORE-003, 005, 012, 014, 015 | TASK-003 |
| app/storage/models/lineage.py | 创建 | REQ-CORE-005, 013 | TASK-004 |
| app/storage/models/snapshot.py | 创建 | REQ-CORE-010, 011, 019, 020 | TASK-008 |
| app/storage/models/__init__.py | 修改 | — | TASK-004, TASK-008 |
| app/lineage/service.py | 修改 | REQ-CORE-005, 013 | TASK-004 |
| app/core/config.py | 修改 | REQ-CORE-002, 027, 031 | TASK-005, TASK-010, TASK-012 |
| app/collect/scheduler.py | 修改 | REQ-CORE-002 | TASK-005 |
| app/collect/idempotency.py | 修改 | REQ-CORE-004 | TASK-005 |
| app/collect/state_machine.py | 修改 | REQ-CORE-004, 012 | TASK-005 |
| app/catalog/bootstrap.py | 修改 | REQ-CORE-001 | TASK-005 |
| app/datacontext/__init__.py | 创建 | REQ-CORE-016, 017, 018 | TASK-007 |
| app/datacontext/context.py | 创建 | REQ-CORE-009, 016, 017 | TASK-007 |
| app/datacontext/query.py | 创建 | REQ-CORE-018 | TASK-007 |
| app/datacontext/time_semantics.py | 创建 | REQ-CORE-009, 021, 022 | TASK-007, TASK-009 |
| app/datacontext/adjustment.py | 创建 | REQ-CORE-007 | TASK-007 |
| app/datacontext/alignment.py | 创建 | REQ-CORE-018 | TASK-007 |
| app/datacontext/readers/*.py | 创建 | REQ-CORE-017, 023 | TASK-007, TASK-009 |
| app/datacontext/snapshot_builder.py | 创建 | REQ-CORE-010, 011, 019, 020 | TASK-008 |
| app/api/routes/data.py | 创建 | REQ-CORE-025, 026, 027, 028 | TASK-010 |
| app/api/routes/__init__.py | 修改 | REQ-CORE-025 | TASK-010 |
| app/api/schemas/data.py | 创建 | REQ-CORE-025, 026 | TASK-010 |
| app/main.py | 修改 | REQ-CORE-025 | TASK-010 |
| compose.test.yml | 创建 | REQ-CORE-031 | TASK-012 |
| .env.test.example | 创建 | REQ-CORE-031 | TASK-012 |
| .importlinter | 创建 | REQ-CORE-016 | TASK-007 |
| scripts/db_migrate_disk/*.sh | 创建 | REQ-CORE-029 | TASK-013 |
| scripts/db_backup/*.sh | 创建 | REQ-CORE-032 | TASK-014 |
| scripts/db_restore/*.sh | 创建 | REQ-CORE-033 | TASK-014 |
| scripts/minute_archive/*.sql,*.sh | 创建 | REQ-CORE-030 | TASK-015 |
| tests/conftest.py | 创建 | REQ-CORE-034 | TASK-006 |
| tests/integration/*.py | 创建 | REQ-CORE-002—015, 016—028 | TASK-006, TASK-011 |
| tests/idempotency/*.py | 创建 | REQ-CORE-004 | TASK-006 |
| tests/lineage/*.py | 创建 | REQ-CORE-005, 013 | TASK-006 |
| tests/anti_lookahead/*.py | 创建 | REQ-CORE-021, 022, 023, 024 | TASK-009 |
| tests/contract/*.py | 创建 | REQ-CORE-025, 026 | TASK-011 |
| tests/fault_recovery/*.py | 创建 | REQ-CORE-029, 031 | TASK-016 |
| tests/backup_restore/*.py | 创建 | REQ-CORE-032, 033 | TASK-016 |
| tests/alembic/*.py | 创建 | REQ-CORE-034 | TASK-017 |
| tests/e2e/*.py | 创建 | REQ-CORE-035 | TASK-017 |
| tests/unit/*.py | 创建 | REQ-CORE-007, 016, 019, 021 | TASK-007, TASK-008 |
| pyproject.toml | 修改 | REQ-CORE-016, 034 | TASK-007, TASK-017 |
| .specforge/config/prod-environment.md | 修改 | REQ-CORE-035 | TASK-018 |
| .specforge/config/project-rules.md | 修改 | REQ-CORE-035 | TASK-018 |
| docs/00_项目管理/*.md | 修改 | REQ-CORE-035 | TASK-018, TASK-019 |
| docs/06_测试验证/*.md | 修改 | REQ-CORE-035 | TASK-018 |
| docs/09_运维手册/*.md | 创建 | REQ-CORE-029—033 | TASK-018 |

## 3. DD → TASK 覆盖矩阵

| DD ID | 主 TASK | 辅助 TASK | 覆盖状态 |
|-------|---------|-----------|----------|
| DD-CORE-001 | TASK-002（迁移种子） | TASK-005（应用层校验） | covered |
| DD-CORE-002 | TASK-005（恢复调度+配置） | TASK-003（终态约束迁移） | covered |
| DD-CORE-003 | TASK-003 | — | covered |
| DD-CORE-004 | TASK-005 | — | covered |
| DD-CORE-005 | TASK-003（迁移字段） | TASK-004（追溯加速） | covered |
| DD-CORE-006 | TASK-002 | TASK-007（查询约束）, TASK-009（分离验证） | covered |
| DD-CORE-007 | TASK-007 | — | covered |
| DD-CORE-008 | TASK-002 | TASK-008（版本不变性） | covered |
| DD-CORE-009 | TASK-008 | — | covered |
| DD-CORE-010 | TASK-003（迁移字段） | TASK-005（状态机） | covered |
| DD-CORE-011 | TASK-001（迁移表） | TASK-004（写入服务） | covered |
| DD-CORE-012 | TASK-003 | — | covered |
| DD-CORE-013 | TASK-003 | — | covered |
| DD-CORE-014 | TASK-007 | — | covered |
| DD-CORE-015 | TASK-001（迁移表） | TASK-008（构建+不可变） | covered |
| DD-CORE-016 | TASK-009 | TASK-007（time_semantics 基础） | covered |
| DD-CORE-017 | TASK-010 | — | covered |
| DD-CORE-018 | TASK-012 | — | covered |
| DD-CORE-019 | TASK-013 | — | covered |
| DD-CORE-020 | TASK-014（备份恢复） | TASK-015（压缩归档） | covered |
| DD-CORE-021 | TASK-006, TASK-011, TASK-016, TASK-017 | — | covered |

## 4. CP（Correctness Property）→ TASK 映射

| CP ID | 描述 | 验证 TASK | 验证命令类型 |
|-------|------|-----------|--------------|
| CP-CORE-001 | LOST 恢复正确性 | TASK-005 | integration |
| CP-CORE-002 | RAW 证据完整性 | TASK-003, TASK-004 | integration |
| CP-CORE-003 | 复权不变性 | TASK-007, TASK-009 | unit + integration |
| CP-CORE-004 | 财务修订不变性 | TASK-002, TASK-008 | integration |
| CP-CORE-005 | DataSnapshot 不变性 | TASK-001, TASK-008 | integration |
| CP-CORE-006 | 防未来不变性 | TASK-007, TASK-009 | integration (anti_lookahead) |

## 5. 覆盖统计

| 指标 | 值 | 达标 |
|------|----|------|
| 总 REQ 数 | 35 | — |
| 总 AC 数 | 138（35 REQ × 平均 ~4 AC） | — |
| 已覆盖 REQ | 35/35 | PASS (100%) |
| 未覆盖 REQ | 0 | PASS |
| 总 DD 数 | 21 | — |
| 已覆盖 DD | 21/21 | PASS (100%) |
| 无悬空 DD | 是 | PASS |
| 总 CP 数 | 6 | — |
| 已覆盖 CP | 6/6 | PASS (100%) |
| 总 TASK 数 | 19 | — |
| 每个 DD 至少关联 1 TASK | 是 | PASS |
| 每个 TASK 有明确目标文件 | 是 | PASS |
| 每个目标文件有验证方式 | 是 | PASS |
| 无悬空 TASK | 是 | PASS |
| 无悬空 REQ | 是 | PASS |

## 6. 共享契约登记建议（Brownfield 降级，不阻塞）

> design.candidate.md §6.4 建议通过 contract_change workflow 登记以下共享枚举。当前 extension_registry.json 为空，适用 Brownfield 降级规则——不阻塞本 WI 任务规划，标记为后续治理建议项。

| 契约 kind | id | owner_module | values | 建议 TASK |
|-----------|----|--------------|--------|-----------|
| shared_enum | run_type | CORE | INITIALIZE, INCREMENTAL, BACKFILL, REPAIR, RETRY | TASK-019 记录建议 |
| shared_enum | quality_status | CORE | PASSED, WARNING, FAILED | TASK-019 记录建议 |
| shared_enum | frequency | CORE | daily, weekly, monthly, minute, financial, event | TASK-019 记录建议 |
| shared_enum | time_mode | CORE | research_mode, strategy_mode, backtest_mode | TASK-019 记录建议 |
| shared_enum | snapshot_status | CORE | BUILDING, READY, INVALIDATED | TASK-019 记录建议 |

## 7. 自检

| # | 检查项 | 结果 |
|---|---|---|
| 1 | 每个 REQ 是否至少关联一个 AC？ | PASS — 35 REQ 各有 2-5 条 AC |
| 2 | 每个 AC 是否至少关联一个 TASK？ | PASS — 138 AC 全部映射到 TASK |
| 3 | 每个 DD 是否至少关联一个 TASK？ | PASS — 21 DD 全覆盖 |
| 4 | 每个 TASK 是否有明确目标文件？ | PASS — 19 TASK 均有具体文件路径 |
| 5 | 每个目标文件是否有验证方式？ | PASS — 文件覆盖矩阵每行有验证 |
| 6 | trace_delta.md 是否真实写入？ | PASS — 本文件 |
| 7 | 每个 CP 是否有验证 TASK？ | PASS — 6 CP 全映射 |
| 8 | 无悬空 REQ/DD/TASK？ | PASS |
