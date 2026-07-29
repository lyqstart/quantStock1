# Intake: 第2步数据底座开发 (S2-001—S2-025)

## 用户原始目标

用户要求连续完成 quantStock1 项目第2步数据底座开发，覆盖 S2-001 至 S2-025 共 25 项任务，对应路线图 P3（数据源与采集）、P4（数据治理与分层存储）、P5（DataContext 与统一查询）三个阶段。

## 权威输入来源

- `docs/00_项目管理/08_第2步数据底座统一实施任务书.md` — 完整任务定义
- `docs/06_测试验证/10_第2步数据底座验收计划.md` — 验收标准和证据要求
- `docs/00_项目管理/07_统一开发任务总表.md` — S2-001—S2-025 任务清单
- `docs/02_可行性研究与资源评估/03—08` — 核心对象、架构、技术选型和 NFR

## 当前已验证基线（C1 分析结果）

| 维度 | 事实 |
|---|---|
| 应用版本 | 0.9.4 |
| Python | >=3.11,<3.12 |
| 数据库 | PostgreSQL 16 + TimescaleDB 2.28.3 |
| 迁移链 | 0001—0012（head: 0012_p4_minute_governance）|
| 业务表 | ~46（meta 4, ops 12, raw 11, clean 14, quality 4, audit 1）|
| DataItem | 10 项已种子化 |
| 采集状态机 | CollectTask/CollectRun/RequestSlice/SliceAttempt 完整 |
| RAW | RawBatch + 9 类型化表，含 request_hash/content_hash |
| CLEAN | CleanBatch + 14 类型化表，含 available_at/quality_status/version |
| 质量 | QualityRun/QualityIssue/DataGap/IssueTaskLink 完整 |
| API 路由 | lineage, ops, system（无数据查询路由）|

## 主要功能缺口（需新增开发）

1. **lineage_edge 基础表**（S2-014）— 当前仅有服务层遍历，无正式 lineage_edge 表
2. **DataContext 模块**（S2-016）— 完全不存在，需新建 app/datacontext/
3. **DataSnapshot**（S2-017）— 不存在，需新建模型和迁移
4. **防未来函数规则**（S2-018）— 不存在，需新建规则和测试
5. **统一查询 API**（S2-019）— 不存在，需新建数据查询路由
6. **server-test 配置**（S2-022）— 不存在，需新建独立测试 compose
7. **数据库迁盘脚本**（S2-020）— 不存在
8. **备份恢复脚本**（S2-023）— 不存在
9. **DataItem 元数据补齐**（S2-002）— business_time_field/history_start/update_mode 等字段部分为空

## 硬约束

1. 所有数据库结构变化必须进入新的 Alembic 迁移（从 0013 开始）
2. 数据库功能必须使用真实 PostgreSQL/TimescaleDB 验证
3. 不引入 Celery、Redis 核心状态、Kafka、RabbitMQ、微服务或 Kubernetes
4. API 不执行长任务
5. DataContext 不读取 RAW
6. 旧 quantStock 不成为在线依赖
7. 不修改已执行历史迁移
8. 不提交、不推送
9. 不自动修改 stable 数据库、端口、数据卷或网络
10. 不自动扩大全市场分钟历史
11. 需要用户执行的 stable 操作生成完整可复制命令

## 首批 DataItem（已种子化）

trade_calendar, stock_basic, stock_daily, stock_adj_factor, stock_daily_basic, stock_suspend, stock_limit_price, stock_minute, financial_income, financial_indicator

## 五个检查点

- C1: S2-001 基线与差距（分析完成）
- C2: S2-002—S2-015 采集与治理
- C3: S2-016—S2-019 查询与防未来
- C4: S2-020—S2-023 环境、迁盘、容量和恢复
- C5: S2-024—S2-025 集成、部署和验收
