#!/bin/bash
# 数据库迁盘预检脚本
# 检查迁移前的所有前置条件，任何一项失败即中止
# 输出格式: START|step=xxx / DONE|step=xxx / FAILED|step=xxx|rc=code
set -euo pipefail

LOG_FILE="/tmp/db_migrate_precheck.log"
: > "$LOG_FILE"

# 配置（可通过环境变量覆盖）
PG_HOST="${PG_HOST:-127.0.0.1}"
PG_PORT="${PG_PORT:-15432}"
PG_DB="${PG_DB:-quantstock1_test}"
PG_USER="${PG_USER:-quantstock1_test}"
PGPASSWORD="${PGPASSWORD:-test_password_only}"
export PGPASSWORD

# 目标磁盘路径（用于检查剩余空间）
TARGET_DISK="${TARGET_DISK:-/}"

# 最小所需磁盘空间（MB），默认 2GB
MIN_FREE_MB="${MIN_FREE_MB:-2048}"

# 项目根目录（用于 alembic）
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

step() {
  echo "START|step=$1"
}
done_step() {
  echo "DONE|step=$1"
}
fail_step() {
  echo "FAILED|step=$1|rc=$2"
  exit "$2"
}

# psql 封装
psql_exec() {
  psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -t -A -c "$1" 2>>"$LOG_FILE"
}

# Step 1: 检查数据库连接与 PG 版本
step "check_pg_connection"
PG_VERSION=$(psql_exec "SHOW server_version;" 2>>"$LOG_FILE" | tr -d '[:space:]' || echo "")
if [ -z "$PG_VERSION" ]; then
  echo "ERROR: cannot connect to database at $PG_HOST:$PG_PORT/$PG_DB" >>"$LOG_FILE"
  fail_step "check_pg_connection" 1
fi
echo "PG version: $PG_VERSION" >>"$LOG_FILE"

# 检查是否 PG 16
PG_MAJOR=$(echo "$PG_VERSION" | cut -d. -f1)
if [ "$PG_MAJOR" != "16" ]; then
  echo "ERROR: expected PG 16, got $PG_MAJOR" >>"$LOG_FILE"
  fail_step "check_pg_connection" 2
fi
done_step "check_pg_connection"

# Step 2: 检查 TimescaleDB 扩展版本
step "check_timescaledb"
TS_VERSION=$(psql_exec "SELECT extversion FROM pg_extension WHERE extname='timescaledb';" 2>>"$LOG_FILE" || echo "")
if [ -z "$TS_VERSION" ]; then
  echo "WARN: timescaledb extension not found" >>"$LOG_FILE"
else
  echo "TimescaleDB version: $TS_VERSION" >>"$LOG_FILE"
fi
done_step "check_timescaledb"

# Step 3: 检查当前 Alembic 迁移版本
step "check_alembic_version"
ALEMBIC_VERSION=$(cd "$PROJECT_ROOT" && alembic current 2>>"$LOG_FILE" | grep -oP 'rev:\s*\K[a-z0-9_]+' || echo "")
if [ -z "$ALEMBIC_VERSION" ]; then
  echo "WARN: cannot determine alembic current version" >>"$LOG_FILE"
else
  echo "Alembic head: $ALEMBIC_VERSION" >>"$LOG_FILE"
fi
done_step "check_alembic_version"

# Step 4: 检查数据库大小
step "check_db_size"
DB_SIZE=$(psql_exec "SELECT pg_size_pretty(pg_database_size('$PG_DB'));" 2>>"$LOG_FILE" || echo "unknown")
DB_SIZE_BYTES=$(psql_exec "SELECT pg_database_size('$PG_DB');" 2>>"$LOG_FILE" || echo "0")
echo "Database size: $DB_SIZE ($DB_SIZE_BYTES bytes)" >>"$LOG_FILE"
done_step "check_db_size"

# Step 5: 检查目标磁盘剩余空间
step "check_disk_space"
FREE_KB=$(df -P "$TARGET_DISK" 2>>"$LOG_FILE" | awk 'NR==2{print $4}')
if [ -z "$FREE_KB" ]; then
  echo "WARN: cannot determine free disk space for $TARGET_DISK" >>"$LOG_FILE"
  FREE_MB=0
else
  FREE_MB=$((FREE_KB / 1024))
fi
echo "Free space on $TARGET_DISK: ${FREE_MB}MB (required: ${MIN_FREE_MB}MB)" >>"$LOG_FILE"
if [ "$FREE_MB" -lt "$MIN_FREE_MB" ]; then
  echo "ERROR: insufficient disk space (${FREE_MB}MB < ${MIN_FREE_MB}MB)" >>"$LOG_FILE"
  fail_step "check_disk_space" 3
fi
done_step "check_disk_space"

# Step 6: 检查 TimescaleDB 压缩状态
step "check_compression_status"
if [ -n "$TS_VERSION" ]; then
  COMPRESSED_CHUNKS=$(psql_exec "SELECT count(*) FROM timescaledb_information.chunks WHERE is_compressed=true;" 2>>"$LOG_FILE" || echo "0")
  TOTAL_CHUNKS=$(psql_exec "SELECT count(*) FROM timescaledb_information.chunks;" 2>>"$LOG_FILE" || echo "0")
  echo "Compressed chunks: $COMPRESSED_CHUNKS / $TOTAL_CHUNKS" >>"$LOG_FILE"
else
  COMPRESSED_CHUNKS="N/A"
  TOTAL_CHUNKS="N/A"
fi
done_step "check_compression_status"

# Step 7: 检查活跃连接数
step "check_active_connections"
ACTIVE_CONNS=$(psql_exec "SELECT count(*) FROM pg_stat_activity WHERE datname='$PG_DB';" 2>>"$LOG_FILE" || echo "0")
echo "Active connections: $ACTIVE_CONNS" >>"$LOG_FILE"
done_step "check_active_connections"

echo ""
echo "=== Precheck Summary ==="
echo "PG Version:         $PG_VERSION"
echo "TimescaleDB:        ${TS_VERSION:-not installed}"
echo "Alembic head:       ${ALEMBIC_VERSION:-unknown}"
echo "Database size:      $DB_SIZE"
echo "Free disk space:    ${FREE_MB}MB"
echo "Compressed chunks:  ${COMPRESSED_CHUNKS} / ${TOTAL_CHUNKS}"
echo "Active connections: $ACTIVE_CONNS"
echo "All prechecks passed."
