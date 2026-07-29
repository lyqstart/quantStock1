# Tasks — 第2步文档收尾（WI-0002 quick_change / code_only_fast_path）

> 写入范围：仅 8 个 docs 文件，无业务代码、无数据库、无 stable/server-test、无 main 合并
> 任务数：2（≤3，不触发升级）
> 规格影响：无（no spec impact，candidate_manifest.entries=[]，merge_report.status=not_applicable）
> refs 依据：本 WI 文档收尾登记的是 REQ-CORE-035（真实数据端到端验收）/ REQ-CORE-034（集成测试套件覆盖）/ DD-CORE-021（集成测试套件与端到端验收）在 server-test 真实环境的验收通过结论；不为 spec 新增/修改任何条目。

---

### TASK-WI-0002-001 登记决策与变更记录

**context_block**（executor 必读）：
- **What**: 更新决策记录与变更记录两个 docs 文件，登记第2步真实验收通过事实与 WI-0001 SpecForge 治理结论（在 docs 内追加 DEC-031~034、CHG-015 条目——这些是文档登记内容，非 spec 决策）
- **Why**: 第2步已在 server-test 真实 PostgreSQL 16.14 + TimescaleDB 2.28.3 通过验收（290 passed/0 failed/0 skipped），即 REQ-CORE-035（S2-025 真实数据验收）通过，需把真实事实登记进治理文档，使路线图可推进至第3步
- **Refs**: REQ-CORE-035（代表性真实数据端到端验收 / S2-025）、DD-CORE-021（集成测试套件与端到端验收）
- **Where**:
  - read_files: [docs/00_项目管理/02_项目决策记录.md, docs/00_项目管理/03_项目变更记录.md]
  - allowed_write_files: [docs/00_项目管理/02_项目决策记录.md, docs/00_项目管理/03_项目变更记录.md]
  - forbidden_files: [requirements.md, design.md, tasks.md, trace_delta.md, app/, migrations/, tests/, scripts/, compose.test.yml, .specforge/project/, stable, server-test, main]
- **Current Implementation**:
  - 相关入口文件：docs/00_项目管理/02_项目决策记录.md（最新决策到 DEC-030，基线非 d40ca76）、docs/00_项目管理/03_项目变更记录.md（最新变更未含 CHG-015）
  - 当前行为：第2步状态标记为"实施中"，未登记真实验收通过
  - 已确认依据：DESIGN（路线图 + CORE 设计 DD-CORE-021）+ CODE_OBSERVED（WI-0001 真实 server-test 产物）
- **Constraints**:
  - 只编辑上述 2 个 docs 文件，不触碰业务代码/迁移/测试/脚本/配置/stable/server-test/main
  - 不伪造 WI-0001 为 closed；如实记录停在 verification_done 及原因（引用 DEC-032/033）
  - 真实数字必须与 WI-0001 产物一致：290 passed、0 failed、0 skipped、head=0015_audit_gap_rawev、base→0015 升级 / 0015→0012 降级 / 0012→0015 重新升级均通过、全量备份+SHA256+独立库恢复通过
  - 不新增/不修改任何测试、不改任何验收标准（只登记已通过事实）

编辑指令：
1. 决策记录：文件头基线改为 d40ca76；在决策清单 DEC-030 后追加 DEC-031~034：
   - DEC-031 第2步数据底座真实验收通过（已确认，依据：server-test真实PG/TimescaleDB；影响：290 passed/0 failed/0 skipped，迁移升降级、备份SHA256、独立库恢复全部通过）
   - DEC-032 WI-0001因外部SpecForge close_gate缺陷停在verification_done（已确认；不视为quantStock1未通过，不伪造closed）
   - DEC-033 SpecForge close_gate缺陷在SpecForge项目单独修复（已确认；本仓库不改业务代码绕过）
   - DEC-034 第2步业务代码基线固化为d40ca76（已确认；收尾只提交文档与治理证据）
   并在"关键决策详细说明"中为 DEC-031~034 各写一个详细说明小节（含真实数字：290 passed、head=0015_audit_gap_rawev、base→0015升级/0015→0012降级/0012→0015重新升级通过、全量备份+SHA256+独立库恢复通过）。
2. 变更记录：文件头基线改为 d40ca76；追加 CHG-015（2026-07-29，第2步数据底座收尾完成，第2步实施中→第2步真实验收通过进入第3步，S2-001—S2-025全部完成，WI-0001因SpecForge工具缺陷停在verification_done，提交d40ca76）；在当前有效基线代码块追加"数据底座：第2步（P3—P5）已完成 / 研究回测：第3步（P6—P8）待开始"。

- **Done When Code**: docs/00_项目管理/02_项目决策记录.md 与 03_项目变更记录.md 被修改并包含新决策/变更条目
- **Done When Behavior**: 决策记录含 DEC-031~034 与真实数字；变更记录含 CHG-015 与第3步待开始；两文件基线均为 d40ca76
- **Done When Evidence**: 下列 verification_commands 全部退出码 0
- **out_of_scope**: 业务代码、数据库、迁移、测试、stable/server-test 执行、main 合并、WI-0001 状态变更、spec（requirements/design）修改

- **refs**: [REQ-CORE-035, DD-CORE-021]
- **depends_on**: []
- files_to_modify: [docs/00_项目管理/02_项目决策记录.md, docs/00_项目管理/03_项目变更记录.md]
- **verification_commands**:
  - integration:
    - `findstr /C:"DEC-031" "docs/00_项目管理/02_项目决策记录.md"`
    - `findstr /C:"DEC-032" "docs/00_项目管理/02_项目决策记录.md"`
    - `findstr /C:"DEC-033" "docs/00_项目管理/02_项目决策记录.md"`
    - `findstr /C:"DEC-034" "docs/00_项目管理/02_项目决策记录.md"`
    - `findstr /C:"290 passed" "docs/00_项目管理/02_项目决策记录.md"`
    - `findstr /C:"0015_audit_gap_rawev" "docs/00_项目管理/02_项目决策记录.md"`
    - `findstr /C:"CHG-015" "docs/00_项目管理/03_项目变更记录.md"`
    - `findstr /C:"d40ca76" "docs/00_项目管理/03_项目变更记录.md"`

---

### TASK-WI-0002-002 更新文档状态与路线图收尾

**context_block**（executor 必读）：
- **What**: 更新 6 个 docs 文件（实施检查点、实施记录、验收记录、部署说明、任务总表、路线图），把第2步状态由"实施中/WAITING_USER_EXECUTION"改为"真实验收通过"，并把路线图推进至第3步
- **Why**: 第2步已在 server-test 真实环境通过全部验收（REQ-CORE-034 集成测试套件 290 passed + REQ-CORE-035 真实数据端到端验收），文档需反映真实结论并衔接第3步 P6—P8 研究与回测
- **Refs**: REQ-CORE-035（真实数据端到端验收 / S2-025）、REQ-CORE-034（集成测试套件覆盖 / S2-024）、DD-CORE-021（集成测试套件与端到端验收）
- **Where**:
  - read_files: [docs/05_开发实施/20_第2步实施检查点与证据清单.md, docs/05_开发实施/21_第2步数据底座实施记录.md, docs/06_测试验证/11_第2步数据底座验收记录.md, docs/07_部署上线/01_第2步部署迁盘备份恢复说明.md, docs/00_项目管理/07_统一开发任务总表.md, docs/00_项目管理/00_A股量化分析平台建设路线图.md]
  - allowed_write_files: [docs/05_开发实施/20_第2步实施检查点与证据清单.md, docs/05_开发实施/21_第2步数据底座实施记录.md, docs/06_测试验证/11_第2步数据底座验收记录.md, docs/07_部署上线/01_第2步部署迁盘备份恢复说明.md, docs/00_项目管理/07_统一开发任务总表.md, docs/00_项目管理/00_A股量化分析平台建设路线图.md]
  - forbidden_files: [requirements.md, design.md, tasks.md, trace_delta.md, app/, migrations/, tests/, scripts/, compose.test.yml, .specforge/project/, stable, server-test, main]
- **Current Implementation**:
  - 相关入口文件：上述 6 个 docs 文件，第2步相关章节当前状态多为 WAITING_USER_EXECUTION 或"实施中"
  - 当前行为：任务总表 S2-001—S2-025 未全部 DONE；路线图当前状态停在第2步，版本非 V2.2
  - 已确认依据：DESIGN（路线图 + CORE 设计 DD-CORE-021）+ CODE_OBSERVED（WI-0001 真实 server-test 产物）
- **Constraints**:
  - 只编辑上述 6 个 docs 文件，不触碰业务代码/迁移/测试/脚本/配置/.specforge/project/stable/server-test/main
  - stable 相关命令保持 WAITING_USER_EXECUTION 不改（仅文档登记，不执行 stable 迁移）
  - 如实记录 WI-0001 停在 verification_done（引用 DEC-032/033），含 SEMANTIC_CLOSURE_INPUT_STALE 说明
  - 真实数字必须一致：290 passed、0 failed、0 skipped、head=0015_audit_gap_rawev、升降级循环、备份SHA256、独立库恢复
  - 不新增/不修改任何测试与验收标准

编辑指令：
1. 实施检查点(20)：基线改d40ca76、状态改"第2步真实验收通过（server-test 真实PostgreSQL 16.14 + TimescaleDB 2.28.3）"；C1—C5状态全PASS并填真实证据；C1清单的- [ ]全改- [x]；C2/C3/C4/C5表WAITING_USER_EXECUTION全改PASS；追加"真实数据库验证结论（server-test）"章节和"SpecForge治理结论（WI-0001）"章节（含SEMANTIC_CLOSURE_INPUT_STALE说明，引用DEC-032/033）。
2. 实施记录(21)：Base commit改d40ca76；验证状态表三行WAITING_USER_EXECUTION改PASS并更新说明；追加"6.真实验证结论（server-test）"章节。
3. 验收记录(11)：验收环境改server-test（PostgreSQL 16.14 + TimescaleDB 2.28.3）；第2节标题WAITING_USER_EXECUTION改PASS；已知限制表替换为真实结果；验收结论表替换为全PASS（含SpecForge治理行）；追加"5.第2步验收结论"章节。
4. 部署说明(07)：在第1节前新增"0.server-test真实执行结果（第2步验收）"章节（290 passed、head=0015、升降级循环、备份SHA256、独立库恢复）；stable相关命令保持WAITING_USER_EXECUTION不改。
5. 任务总表(07)：基线改d40ca76；S2-001—S2-025状态全改DONE；第9节当前任务代码块替换为"已完成S1、S2全部；当前第3步待开始"；第10节WI-0001状态改verification_done（引用DEC-032），追加"真实验证结论（server-test）"子章节。
6. 路线图(00)：版本V2.1→V2.2；当前状态改"第2步真实验收通过，当前事项进入第3步P6—P8研究与回测"；P3/P4/P5状态改"已完成"并追加第2步结论；第8.2表更新STEP2文档状态为已完成并追加27/28/29行；第9节当前推进位置整体替换为"第3步研究与回测"。

- **Done When Code**: 上述 6 个 docs 文件被修改；与 TASK-001 合计 8 个 docs 文件均含 d40ca76
- **Done When Behavior**: 实施检查点 C1—C5 全 PASS；任务总表 S2-025 为 DONE；路线图含 V2.2 且当前推进位置为第3步
- **Done When Evidence**: 下列 verification_commands 全部退出码 0
- **out_of_scope**: 业务代码、数据库、迁移、测试新增/修改、stable 实际执行、server-test 执行、main 合并、WI-0001 状态变更、spec（requirements/design）修改

- **refs**: [REQ-CORE-035, REQ-CORE-034, DD-CORE-021]
- **depends_on**: []
- files_to_modify: [docs/05_开发实施/20_第2步实施检查点与证据清单.md, docs/05_开发实施/21_第2步数据底座实施记录.md, docs/06_测试验证/11_第2步数据底座验收记录.md, docs/07_部署上线/01_第2步部署迁盘备份恢复说明.md, docs/00_项目管理/07_统一开发任务总表.md, docs/00_项目管理/00_A股量化分析平台建设路线图.md]
- **verification_commands**:
  - integration:
    - `findstr /C:"d40ca76" "docs/05_开发实施/20_第2步实施检查点与证据清单.md"`
    - `findstr /C:"d40ca76" "docs/05_开发实施/21_第2步数据底座实施记录.md"`
    - `findstr /C:"d40ca76" "docs/06_测试验证/11_第2步数据底座验收记录.md"`
    - `findstr /C:"d40ca76" "docs/07_部署上线/01_第2步部署迁盘备份恢复说明.md"`
    - `findstr /C:"d40ca76" "docs/00_项目管理/07_统一开发任务总表.md"`
    - `findstr /C:"d40ca76" "docs/00_项目管理/00_A股量化分析平台建设路线图.md"`
    - `findstr /C:"290 passed" "docs/05_开发实施/20_第2步实施检查点与证据清单.md"`
    - `findstr /C:"V2.2" "docs/00_项目管理/00_A股量化分析平台建设路线图.md"`
    - `findstr /C:"DONE" "docs/00_项目管理/07_统一开发任务总表.md"`

---

## 共同边界
- 不触碰 app/、migrations/、tests/、scripts/、compose.test.yml、.importlinter、pyproject.toml、.env*、.specforge/project/、main、stable、server-test
- WI-0001 保持 verification_done
- 两 task 文件无交集，可并行