# 数据库恢复

> **WAITING_USER_EXECUTION**: 恢复操作会覆盖目标数据库，必须由运维人员确认执行。

## 概述

从 `pg_dump --format=custom` 备份恢复数据库，并进行完整性验证。

恢复验证 3 项核心指标：
1. **Alembic 版本**一致
2. **关键表行数**合理
3. **checksum**一致

## 文件说明

| 文件 | 说明 |
|------|------|
| `restore.sh` | 恢复脚本：校验 checksum → 建库 → pg_restore → 健康检查 |
| `verify.sh` | 验证脚本：表数量 → 关键表行数 → hypertable → Alembic 版本 |

## 使用方法

### 恢复数据库

```bash
# Dry-run（预览恢复计划，不执行）
bash scripts/db_restore/restore.sh --backup /tmp/test_backup/test.dump --dry-run

# 实际恢复（WAITING_USER_EXECUTION）
bash scripts/db_restore/restore.sh --backup /tmp/test_backup/test.dump
```

恢复流程：
1. 验证备份文件存在
2. 校验 SHA256 checksum
3. 创建目标数据库（如不存在）
4. 执行 `pg_restore`
5. 验证 Alembic 版本
6. 基本健康检查（`SELECT 1`）

### 验证恢复结果

```bash
# 验证当前数据库（不与备份对账）
bash scripts/db_restore/verify.sh

# 验证并与备份 checksum 对账
bash scripts/db_restore/verify.sh --backup /tmp/test_backup/test.dump
```

验证项：
- 应用表数量（排除 pg_catalog / information_schema）
- 关键表行数（meta.data_item / clean.security_master / clean.trade_calendar / clean.stock_daily）
- TimescaleDB hypertable 数量（含 stock_minute）
- Alembic 版本号
- 备份文件 checksum（如指定 --backup）

## 恢复后健康检查

恢复完成后，启动应用并检查健康端点：

```bash
# 启动 server-test
docker compose -f compose.test.yml up -d --wait

# 检查应用健康（应返回 200）
curl -s http://127.0.0.1:18001/health
```

## RTO 策略

| 数据类型 | RTO |
|----------|-----|
| 配置/审计数据 | ≤ 4 小时 |
| 市场数据 | ≤ 24 小时 |

## 配置校验

应用启动时检查 `QUANTSTOCK1_ENV`，若连接非对应环境的数据库则拒绝启动。恢复到 server-test 环境时：

```bash
# .env.test 配置
QUANTSTOCK1_DATABASE_URL=postgresql+psycopg://quantstock1_test:test_password_only@localhost:15432/quantstock1_test
QUANTSTOCK1_ENV=test
```

## 日志

- 恢复日志：`/tmp/db_restore.log`
- 验证日志：`/tmp/db_restore_verify.log`

## 完整备份恢复演练

```bash
# 1. 备份
bash scripts/db_backup/full_backup.sh --target /tmp/test_backup

# 2. 恢复（dry-run）
bash scripts/db_restore/restore.sh --backup /tmp/test_backup/*.dump --dry-run

# 3. 恢复（实际）
bash scripts/db_restore/restore.sh --backup /tmp/test_backup/*.dump

# 4. 验证
bash scripts/db_restore/verify.sh --backup /tmp/test_backup/*.dump
```

建议每月至少执行一次完整演练。
