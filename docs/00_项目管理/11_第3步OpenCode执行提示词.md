# 第3步OpenCode执行提示词

继续quantStock1第3步研究与回测开发。

仓库：

```text
D:\code\temp\quantStock1
```

远程：

```text
https://github.com/lyqstart/quantstock1.git
remote：yc
branch：main
```

正式基线：

```text
b0463bee7df45a4795b9e013d053ef19fd95afe2
```

目标：

```text
连续完成S3-001—S3-016
对应P6、P7、P8
```

开始前完整读取：

```text
AGENTS.md
docs/00_项目管理/00_A股量化分析平台建设路线图.md
docs/00_项目管理/01_项目文档与讨论管理规则.md
docs/00_项目管理/02_项目决策记录.md
docs/00_项目管理/03_项目变更记录.md
docs/00_项目管理/04_开发补丁与真实验证规则.md
docs/00_项目管理/05_六步加速执行计划.md
docs/00_项目管理/06_全项目验收指标.md
docs/00_项目管理/07_统一开发任务总表.md
docs/00_项目管理/10_第3步研究与回测统一实施任务书.md
docs/06_测试验证/12_第3步研究与回测验收计划.md
docs/02_可行性研究与资源评估/03_核心业务对象与生命周期.md
docs/02_可行性研究与资源评估/04_全链路状态与追溯模型.md
docs/02_可行性研究与资源评估/05_系统总体架构.md
docs/02_可行性研究与资源评估/06_技术选型与决策依据.md
docs/02_可行性研究与资源评估/07_环境与部署拓扑.md
docs/02_可行性研究与资源评估/08_非功能需求与服务目标.md
docs/05_开发实施/21_第2步数据底座实施记录.md
docs/06_测试验证/11_第2步数据底座验收记录.md
docs/07_部署上线/01_第2步部署迁盘备份恢复说明.md
```

再读取当前代码、迁移、测试、Compose、SpecForge正式规格和全部相关文档。

执行规则：

1. 证据先行，先重建b0463be真实代码和数据库基线。
2. 新建本步骤自己的feature_spec / requirement_change_path Work Item。
3. 不处理、不回退、不关闭WI-0001和WI-0002。
4. 候选门禁通过后只停一次，请求用户批准。
5. 用户批准后连续完成C2、C3、C4和C5，不在检查点之间等待确认。
6. 已有能力优先复用，不重复建设DataContext、DataSnapshot、Lineage、任务Lease和审计。
7. 所有数据库结构变化进入新Alembic迁移，不修改0015及以前迁移。
8. Feature、Analysis、StockPoolVersion、StrategyVersion和BacktestRun正式版本不可覆盖。
9. DataContext和研究模块不得读取RAW。
10. API不得执行Feature计算或回测长任务。
11. 不使用eval、exec或数据库裸脚本运行正式策略。
12. 不引入Celery、Redis核心队列、Kafka、RabbitMQ、微服务或Kubernetes。
13. 不让旧quantStock成为在线依赖。
14. 不自动修改stable数据库、端口、网络、数据卷和正式任务。
15. 不扩大全市场分钟历史。
16. 数据库测试使用真实PostgreSQL 16和TimescaleDB。
17. 真实A股验收不得使用数日玩具数据，回测区间不少于3年。
18. 市场规则、费用和涨跌停规则按交易所、板块、证券状态和生效日期版本化，不允许写死一套永久常量。
19. 默认回测不得使用同一收盘价同时产生信号并成交。
20. 策略收益不是验收条件。
21. 不提交、不推送、不合并main。
22. sf_safe_bash在Windows存在chcp注入问题时，使用已经验证的安全调用方式或SpecForge注册工具，不得降低测试要求。
23. SpecForge close_gate再次发生已登记缺陷时，记录事实并停止循环，不在本项目修复SpecForge。

连续检查点：

```text
C1：真实基线与S3差距
C2：S3-001—S3-005 Feature和Analysis
C3：S3-006—S3-009 StockPool、Strategy和ResearchTask
C4：S3-010—S3-015 回测、撮合、账务、比较和性能
C5：S3-016 真实数据库和真实A股端到端验收
```

C1必须形成逐项差距矩阵，不得把设计目标写成现有事实。

C2最低完成：

```text
FeatureDefinition
FeatureVersion
FeatureDependency
FeatureRun
FeatureResultSet
首批8个公共Feature
AnalysisDefinition
AnalysisVersion
AnalysisRun
AnalysisResultSet
首批5类分析器
```

C3最低完成：

```text
StockPoolDefinition
StockPoolVersion
StockPoolMember
StrategyDefinition
StrategyImplementation
StrategyVersion
StrategyParameterSnapshot
ResearchTask
Research Worker
```

C4最低完成：

```text
MarketRuleVersion
CostModelVersion
FillPolicyVersion
Order
Fill
Trade
PositionLot
PositionDaily
CashLedger
PortfolioDaily
BacktestRun
Backtest指标
StrategyComparison
```

C5必须在svr3独立目录：

```text
/mnt/1t_back/project/quantstock1-step3-test
```

执行：

- Alembic空库升级；
- 0015现有库升级；
- PostgreSQL和TimescaleDB版本核实；
- 两组回归测试；
- 第3步全部数据库测试；
- 不少于3年的真实A股日线闭环；
- 同输入重复运行结果一致；
- 不同参数版本策略比较；
- 性能和容量基准；
- 服务健康检查；
- 备份恢复回归。

本地代码完成、需要将分支送到服务器验证时，允许停止一次，向用户输出一段完整PowerShell命令，用于：

```text
检查分支
检查b0463be基线
git diff --check
提交
推送yc功能分支
```

用户执行后，继续server-test，不再重新分析。

最终必须更新：

```text
docs/05_开发实施/22_第3步实施检查点与证据清单.md
docs/05_开发实施/23_第3步研究与回测实施记录.md
docs/06_测试验证/13_第3步研究与回测验收记录.md
docs/07_部署上线/02_第3步ResearchWorker部署说明.md
docs/00_项目管理/00_A股量化分析平台建设路线图.md
docs/00_项目管理/02_项目决策记录.md
docs/00_项目管理/03_项目变更记录.md
docs/00_项目管理/07_统一开发任务总表.md
```

最终只报告：

1. 完成的S3任务；
2. 未完成或阻塞任务；
3. 新增对象和迁移；
4. 修改文件；
5. 本地测试通过、失败、跳过数量；
6. 真实数据库测试通过、失败、跳过数量；
7. 真实A股端到端区间和数据规模；
8. 防未来和复现结果；
9. 回测资金持仓对账结果；
10. 性能基准；
11. SpecForge Work Item状态；
12. 需要用户执行的一段完整命令；
13. git status --short；
14. 建议提交标题。

不要给零散方案，不要让用户选择架构路径。
