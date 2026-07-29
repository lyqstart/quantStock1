# Change Classification: 第2步数据底座

## 分类对象

本次变更的预期最终语义影响：在现有 P3/P4 数据采集与治理基础上，新增 P5 DataContext 统一查询能力、lineage_edge 正式基础表、DataSnapshot 不可变输入快照、防未来函数规则、统一查询 API，以及 server-test 环境和数据库备份恢复脚本。

## 分类字段

| 字段 | 值 | 依据 |
|---|---|---|
| requirement_changed | true | 新增 DataContext 查询契约需求、防未来函数需求、DataSnapshot 不可变需求 |
| acceptance_criteria_changed | true | 新增防未来测试通过、FAILED 不可发布、Snapshot 不可变等验收标准 |
| business_rule_changed | true | 新增 available_at 约束规则、防未来函数规则、质量发布门禁规则 |
| data_semantics_changed | true | DataSnapshot 语义、lineage_edge 语义、查询时间语义 |
| api_contract_changed | true | 新增 /api/v1 数据查询路由契约 |
| design_changed | true | 新增 DataContext 模块设计、lineage_edge 表设计、DataSnapshot 模型设计 |
| module_boundary_changed | false | 仍在 CORE 模块内，新增子模块不改变模块边界 |
| architecture_changed | false | 保持模块化单体 + PostgreSQL 任务队列架构不变 |
| contract_registry_only | false | 不只是契约登记 |
| data_migration_needed | true | 需要新 Alembic 迁移创建 lineage_edge 和 data_snapshot 表 |
| code_change_needed | true | 需要新增 DataContext、查询 API、测试、脚本 |
| unknowns | [] | 所有事实已由代码分析确认 |

## 分类结论

本次变更为 **需求变更路径（requirement_change_path）**，涉及需求、设计、数据库结构和代码实现。

- 不适用 code_only_fast_path（有需求、设计和数据语义变化）
- 不适用 contract_change（不只是契约登记）
- 不适用 architecture_change（不改变模块边界和架构）
- 不适用 spec_migration（不是 legacy 规格迁移）
