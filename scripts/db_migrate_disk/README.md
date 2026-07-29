# 数据库迁盘脚本

> **WAITING_USER_EXECUTION**: 所有 stable 迁盘操作必须由运维人员手动确认执行，脚本不自动执行任何不可逆操作。

## 概述

本目录包含数据库迁盘（将 PostgreSQL 数据从系统盘迁移到数据盘）的完整脚本套件，遵循 6 阶段流程：

```
预检 → 停止 → 备份 → 复制/恢复 → 启动验证 → 回滚（如需）
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `precheck.sh` | 预检脚本：检查 PG 版本、数据库大小、磁盘空间、压缩状态、连接数 |
| `migrate.sh` | 迁盘计划生成器：输出完整命令序列，标记 WAITING_USER_EXECUTION |
| `rollback.sh` | 回滚脚本：恢复到迁盘前状态 |

## 使用方法

### 1. 预检

在迁盘前运行预检，确认所有前置条件满足：

```bash
# 使用默认配置（server-test 环境）
bash scripts/db_migrate_disk/precheck.sh

# 指定数据库连接
PG_HOST=127.0.0.1 PG_PORT=15432 PG_DB=quantstock1_test \
PG_USER=quantstock1_test PGPASSWORD=test_password_only \
bash scripts/db_migrate_disk/precheck.sh
```

预检项：
- PostgreSQL 版本（必须 16）
- TimescaleDB 扩展版本
- Alembic 当前迁移版本
- 数据库大小
- 目标磁盘剩余空间（默认 ≥ 2GB）
- TimescaleDB 压缩状态
- 活跃连接数

### 2. 生成迁盘计划

```bash
# 生成命令序列（不执行）
bash scripts/db_migrate_disk/migrate.sh

# 显式 dry-run
bash scripts/db_migrate_disk/migrate.sh --dry-run
```

脚本输出包含 8 个步骤的完整命令序列，每条高风险命令前标注 `WAITING_USER_EXECUTION`。

### 3. 执行迁盘

**手动执行** migrate.sh 输出的每一条 `WAITING_USER_EXECUTION` 命令，逐步确认。

关键顺序：
1. 运行预检
2. 停止服务
3. 全量备份（pg_dump + checksum）
4. 创建新 volume
5. restore 到新 volume
6. 更新 compose 配置
7. 重启并验证
8. 清理旧资源（最后，双重确认）

### 4. 回滚

如果验证失败，执行回滚：

```bash
bash scripts/db_migrate_disk/rollback.sh
```

回滚步骤：
1. 停止服务
2. 恢复原始 compose 配置
3. 重启到旧 volume
4. 验证旧数据可用
5. （可选）从备份恢复
6. 清理失败的新 volume

## 演练环境

所有迁盘演练在 `server-test` 环境（`compose.test.yml`）进行，**严禁**在 stable 环境直接执行。

```bash
# 启动 server-test 环境
docker compose -f compose.test.yml up -d --wait

# 在 server-test 上演练
PG_PORT=15432 PG_DB=quantstock1_test bash scripts/db_migrate_disk/precheck.sh
```

## 高风险操作清单（不自动执行）

1. 迁盘（volume 切换）
2. 删除旧 volume（不可逆）
3. 开放端口
4. 替换正式数据库
5. 扩大全市场分钟历史

以上操作均标记 `WAITING_USER_EXECUTION`，必须人工确认。

## 日志

所有脚本日志写入 `/tmp/db_migrate_*.log`：
- 预检日志：`/tmp/db_migrate_precheck.log`
- 迁盘日志：`/tmp/db_migrate_run.log`
- 回滚日志：`/tmp/db_migrate_rollback.log`
