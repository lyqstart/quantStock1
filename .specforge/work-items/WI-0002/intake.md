# Intake — 第2步文档收尾

## 变更描述

第2步（P3—P5 数据底座）已在 server-test 真实环境通过完整验收，但项目文档仍停留在"代码 PASS / 数据库 WAITING_USER_EXECUTION"的中间态。本 Work Item 只做文档收尾，把真实验收事实登记到项目决策记录、变更记录、实施记录、验收记录、部署说明、任务总表和路线图中，使文档与真实结论一致。

本 WI 不修改任何业务代码、迁移、测试、脚本、配置；不修改 stable 和 server-test；不合并 main。

## 收尾事实基准（已确认，来自 WI-0001 真实验证）

- 业务代码基线 commit：d40ca76（完整：d40ca7650c7cd0f6b463d5edfcf3fb1ef7e80ffa）
- 分支：feature/2-s2-001-s2-025-wi-0001
- 真实验证环境：server-test，PostgreSQL 16.14 + TimescaleDB 2.28.3，独立数据库（端口 15432/18001），与 stable 完全隔离
- 测试结果：290 passed、0 failed、0 skipped
- Alembic head：0015_audit_gap_rawev
- 迁移链验证：base→0015 升级通过；0015→0012 降级通过；0012→0015 重新升级通过
- 备份恢复验证：全量备份 + SHA256 校验 + 恢复到独立数据库，全部通过
- SpecForge 治理门禁：verification_gate 通过；formal_version_gate 通过；sf_gate_run 的 close_gate 通过；semantic_closure_valid=true
- WI-0001 权威状态：verification_done（保留，不回退、不伪造 closed）
- WI-0001 停在 verification_done 的原因：SpecForge 的 sf_close_gate 工具在推进 closed 前会改写 changed_files_audit.md，随后用旧的 semantic_closure SHA256 校验，产生 SEMANTIC_CLOSURE_INPUT_STALE 循环；这是 SpecForge 运行时工具缺陷，不是 quantStock1 的代码、测试或验收失败
- 处置：SpecForge 该缺陷在 SpecForge 项目单独修复；不视为 quantStock1 第2步未通过

## 写入范围（仅这 8 个 docs 文件）

1. docs/00_项目管理/00_A股量化分析平台建设路线图.md
2. docs/00_项目管理/02_项目决策记录.md
3. docs/00_项目管理/03_项目变更记录.md
4. docs/00_项目管理/07_统一开发任务总表.md
5. docs/05_开发实施/20_第2步实施检查点与证据清单.md
6. docs/05_开发实施/21_第2步数据底座实施记录.md
7. docs/06_测试验证/11_第2步数据底座验收记录.md
8. docs/07_部署上线/01_第2步部署迁盘备份恢复说明.md

## 边界声明

- 不触碰：app/、migrations/、tests/、scripts/、compose.test.yml、.importlinter、pyproject.toml、.env*、stable 环境、server-test、main 分支
- 不修改 WI-0001 状态
- 不绕过 SpecForge close_gate 工具缺陷
- 只在候选门禁通过后向用户申请一次批准

## 依据来源

- 用户原话（方案A确认）：新建 quick_change/code_only_fast_path WI 承载文档收尾
- WI-0001 真实验证产物（已落盘的 verification_report、evidence_manifest、gate 报告）
- 真实数据库测试结果：290 passed、0 failed、0 skipped
