# 数据库备份

> **WAITING_USER_EXECUTION**: 对 stable 执行备份时，必须由运维人员确认执行。

## 概述

全量数据库备份脚本，使用 `pg_dump --format=custom` 生成备份文件，附带 SHA256 checksum 和 manifest 清单。

## 备份属性

每份备份包含 4 项关键属性：

| 属性 | 说明 |
|------|------|
| 时间戳 | UTC 时间，格式 `YYYYMMDDTHHMMSSZ` |
| PG 版本 | PostgreSQL 服务端版本 |
| 大小 | 备份文件字节数 |
| checksum | SHA256 校验和 |

## 使用方法

### 执行备份

```bash
# 基本用法（备份到指定目录）
bash scripts/db_backup/full_backup.sh --target /path/to/backups

# 在 server-test 环境演练
bash scripts/db_backup/full_backup.sh --target /tmp/test_backup

# 指定数据库连接
PG_HOST=127.0.0.1 PG_PORT=15432 PG_DB=quantstock1_test \
PG_USER=quantstock1_test PGPASSWORD=test_password_only \
bash scripts/db_backup/full_backup.sh --target /tmp/test_backup
```

### Docker 模式

通过 Docker Compose 执行备份：

```bash
DOCKER_COMPOSE=compose.dev.yml \
bash scripts/db_backup/full_backup.sh --target /backups
```

## 保留策略

- 默认保留最近 **7** 份备份（`retention_count`）
- 超出保留数量的最旧备份自动删除（含 `.sha256`）
- 可通过 `--retention N` 或环境变量 `RETENTION_COUNT` 调整

## 备份文件结构

```
backups/
├── quantstock1_test_20260729T120000Z.dump        # pg_dump custom 格式
├── quantstock1_test_20260729T120000Z.dump.sha256  # SHA256 checksum
├── manifest_20260729T120000Z.json                  # 备份清单
└── manifest.json                                   # 备份策略模板
```

## manifest.json 字段

```json
{
  "backup_format": "pg_dump custom",
  "retention_count": 7,
  "checksum_algorithm": "sha256",
  "include_timescaledb": true
}
```

## RPO 策略

| 数据类型 | RPO |
|----------|-----|
| 配置/审计数据 | ≤ 4 小时 |
| 市场数据 | ≤ 24 小时 |

建议配置 cron 定时执行备份。

## 服务器外副本

至少保留一个**服务器外副本**（off-site copy），防止单点故障：

```bash
# 示例：同步到远程存储
rsync -avz /path/to/backups/ user@remote:/backups/quantstock1/
```

## 安全说明

- 备份不含明文密钥（`pg_dump` 排除含密钥的配置表）
- `PGPASSWORD` 通过环境变量传递，不写入命令历史
- checksum 文件用于恢复前完整性校验

## 日志

备份日志写入 `/tmp/db_backup_full.log`。
