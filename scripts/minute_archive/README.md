# 分钟数据压缩归档

> **WAITING_USER_EXECUTION**: 压缩策略应用和 chunk 删除是 stable 操作，必须由运维人员确认执行。

## 概述

为 `clean.stock_minute` hypertable 配置 TimescaleDB 压缩策略，并归档超过保留期的压缩 chunk。

## 文件说明

| 文件 | 说明 |
|------|------|
| `compress_policy.sql` | TimescaleDB 压缩策略 SQL |
| `archive.sh` | 归档脚本：查询超期 chunk → 导出 → checksum → 验证 |

## 压缩策略

```sql
ALTER TABLE clean.stock_minute SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'security_code',
  timescaledb.compress_orderby = 'trade_time DESC'
);
SELECT add_compression_policy('clean.stock_minute', INTERVAL '30 days');
```

- **segmentby=security_code**: 按股票代码分段，匹配查询高频过滤条件
- **orderby=trade_time DESC**: 最新数据优先，提升近期查询性能
- **policy=30 days**: 自动压缩 30 天以上的数据 chunk

### 应用压缩策略

```bash
# 在 server-test 环境应用
psql -h 127.0.0.1 -p 15432 -U quantstock1_test -d quantstock1_test \
  -f scripts/minute_archive/compress_policy.sql

# 通过 Docker
docker compose -f compose.test.yml exec db psql -U quantstock1_test -d quantstock1_test \
  -f /scripts/minute_archive/compress_policy.sql
```

### 记录压缩基准

应用压缩策略后，记录压缩前后空间占用：

```sql
-- 压缩前
SELECT hypertable_name,
       pg_size_pretty(hypertable_size(format('%I','clean','stock_minute')::regclass)) AS total_size
FROM timescaledb_information.hypertables
WHERE hypertable_name = 'stock_minute';

-- 压缩后（手动触发压缩后）
SELECT chunk_name, pg_size_pretty(before_compression_total_bytes) AS before,
       pg_size_pretty(after_compression_total_bytes) AS after
FROM timescaledb_information.chunks
WHERE hypertable_name = 'stock_minute' AND is_compressed = true;
```

## 归档脚本

### 预览将归档的 chunk

```bash
bash scripts/minute_archive/archive.sh --dry-run
```

### 导出并归档

```bash
# 导出超过 365 天的压缩 chunk
bash scripts/minute_archive/archive.sh --export /path/to/archive --retention-days 365
```

归档流程：
1. 查询超过保留期的压缩 chunk
2. 导出每个 chunk 到 `.sql.gz` 文件
3. 计算 SHA256 checksum
4. 验证导出完整性
5. 输出 drop_chunks 命令（WAITING_USER_EXECUTION）

### 删除已归档 chunk

**仅在确认归档完整性后执行**：

```sql
-- 确认归档 checksum 正确后，手动执行
SELECT drop_chunks('stock_minute', TIMESTAMP '2025-01-01');
```

## 恢复校验

从归档恢复时，校验行数和 checksum 一致（差异 = 0）：

```bash
# 解压并恢复
gunzip <archive_file>.sql.gz | psql -h <host> -d <db>

# 校验行数一致
psql -c "SELECT count(*) FROM clean.stock_minute WHERE trade_time < '<cutoff>';"
```

## 约束

在以下操作完成前，**禁止**扩大全市场分钟历史：
- 迁盘完成（TASK-013）
- 压缩策略应用
- 归档脚本验证
- 备份恢复演练通过（TASK-014）

## 日志

归档日志写入 `/tmp/minute_archive.log`。
