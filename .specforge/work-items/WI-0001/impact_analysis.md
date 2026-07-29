# Impact Analysis: 第2步数据底座

## 受影响模块

### 1. app/storage/models/ — 数据模型层
- **新增** lineage_edge 模型（S2-014）
- **新增** data_snapshot 模型（S2-017）
- **修改** 无（不修改现有模型，只新增）

### 2. app/datacontext/ — 新模块（S2-016）
- **新建** DataContext 统一查询模块
- 只读取 clean 层已发布数据
- 执行 available_at 约束
- 支持单股、范围、全市场查询
- 支持日、分钟、财务、事件数据

### 3. app/api/routes/ — API 路由
- **新增** data.py 查询路由（S2-019）
- 日线、分钟、财务、事件查询
- 返回数据语义（来源、质量、时间）
- 不执行长任务

### 4. app/lineage/ — 血缘服务
- **扩展** lineage_edge 表支持（S2-014）
- RAW→CLEAN→QUALITY 直接关系可查
- lineage_edge 上下游可查

### 5. migrations/ — Alembic 迁移
- **新增** 0013 迁移：lineage_edge + data_snapshot 表
- **新增** 0014 迁移：DataItem 元数据补齐（如需要）

### 6. tests/ — 测试
- **新增** DataContext 测试
- **新增** 防未来函数测试
- **新增** lineage_edge 测试
- **新增** DataSnapshot 不可变测试
- **新增** 查询 API 测试
- **新增** 备份恢复测试

### 7. 部署脚本
- **新增** server-test compose 配置（S2-022）
- **新增** 数据库迁盘脚本（S2-020）
- **新增** 备份恢复脚本（S2-023）

## 风险评估

| 风险 | 等级 | 缓解 |
|---|---|---|
| 新迁移破坏现有库 | 中 | 先在 server-test 空库验证 |
| DataContext 查询性能 | 低 | 复用现有索引和分区 |
| 防未来规则遗漏 | 中 | 全量测试覆盖 |
| stable 操作误执行 | 高 | 脚本标记 WAITING_USER_EXECUTION |

## 可复用能力

- 采集状态机（CollectTask/Run/Slice/Attempt）— 已完整
- RAW/CLEAN 模型 — 已完整
- 质量模型（QualityRun/Issue/DataGap）— 已完整
- 血缘服务遍历 — 已存在，需补充 lineage_edge 表
- Tushare 适配器 — 已存在
- API 框架 — 已存在

## 必须修改/新增能力

- lineage_edge 表和模型 — 新增
- DataContext 模块 — 新增
- DataSnapshot 模型和表 — 新增
- 防未来函数规则 — 新增
- 统一查询 API 路由 — 新增
- server-test 环境 — 新增
- 迁盘/备份/恢复脚本 — 新增
