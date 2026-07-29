#!/bin/bash
# 数据库恢复后验证脚本
# 验证项: 表数量、关键表行数、TimescaleDB hypertable、Alembic 版本
#
# 用法:
#   bash verify.sh --backup /path/to/file.dump   # 与备份 checksum 对账
#   bash verify.sh                                # 仅验证当前数据库
#
# 输出格式: START|step=xxx / DONE|step=xxx / FAILED|step=xxx|rc=code
set -euo pipefail

LOG_FILE="/tmp/db_restore_verify.log"
: > "$LOG_FILE"

# 参数解析
BACKUP_FILE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --backup) BACKUP_FILE="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# 数据库配置
PG_HOST="${PG_HOST:-127.0.0.1}"
PG_PORT="${PG_PORT:-15432}"
PG_DB="${PG_DB:-quantstock1_test}"
PG_USER="${PG_USER:-quantstock1_test}"
PGPASSWORD="${PGPASSWORD:-test_password_only}"
export PGPASSWORD

step() { echo "START|step=$1"; }
done_step() { echo "DONE|step=$1"; }
fail_step() { echo "FAILED|step=$1|rc=$2"; exit "$2"; }

psql_exec() {
  psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -t -A -c "$1" 2>>"$LOG_FILE"
}

# Step 1: 检查表数量
step "check_table_count"
TABLE_COUNT=$(psql_exec "SELECT count(*) FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema') AND table_type='BASE TABLE';" 2>>"$LOG_FILE" || echo "0")
echo "Table count: $TABLE_COUNT" >>"$LOG_FILE"
if [ "$TABLE_COUNT" -lt 1 ]; then
  echo "WARN: no application tables found" >>"$LOG_FILE"
fi
done_step "check_table_count"

# Step 2: 检查关键表行数
step "check_key_table_rows"
echo "Key table row counts:" >>"$LOG_FILE"
for table in "meta.data_item" "clean.security_master" "clean.trade_calendar" "clean.stock_daily"; do
  SCHEMA=$(echo "$table" | cut -d. -f1)
  NAME=$(echo "$table" | cut -d. -f2)
  ROWS=$(psql_exec "SELECT count(*) FROM \"$SCHEMA\".\"$NAME\";" 2>>"$LOG_FILE" || echo "N/A")
  echo "  $table: $ROWS rows" >>"$LOG_FILE"
  echo "  $table: $ROWS rows"
done
done_step "check_key_table_rows"

# Step 3: 检查 TimescaleDB hypertable
step "check_hypertables"
HYPER_COUNT=$(psql_exec "SELECT count(*) FROM timescaledb_information.hypertables;" 2>>"$LOG_FILE" || echo "0")
echo "Hypertables: $HYPER_COUNT" >>"$LOG_FILE"
MINUTE_HT=$(psql_exec "SELECT count(*) FROM timescaledb_information.hypertables WHERE hypertable_name='stock_minute';" 2>>"$LOG_FILE" || echo "0")
echo "stock_minute hypertable exists: $MINUTE_HT" >>"$LOG_FILE"
done_step "check_hypertables"

# Step 4: 检查 Alembic 版本
step "check_alembic_version"
ALEMBIC_VER=$(psql_exec "SELECT version_num FROM alembic_version LIMIT 1;" 2>>"$LOG_FILE" || echo "unknown")
echo "Alembic version: $ALEMBIC_VER" >>"$LOG_FILE"
done_step "check_alembic_version"

# Step 5: （可选）与备份 checksum 对账
if [ -n "$BACKUP_FILE" ] && [ -f "${BACKUP_FILE}.sha256" ]; then
  step "verify_backup_checksum"
  EXPECTED_SHA=$(cut -d' ' -f1 "${BACKUP_FILE}.sha256")
  ACTUAL_SHA=$(sha256sum "$BACKUP_FILE" | cut -d' ' -f1)
  echo "Expected SHA256: $EXPECTED_SHA" >>"$LOG_FILE"
  echo "Actual SHA256:   $ACTUAL_SHA" >>"$LOG_FILE"
  if [ "$EXPECTED_SHA" != "$ACTUAL_SHA" ]; then
    echo "ERROR: backup checksum mismatch!" >>"$LOG_FILE"
    fail_step "verify_backup_checksum" 1
  fi
  done_step "verify_backup_checksum"
fi

echo ""
echo "=== Verification Summary ==="
echo "Tables:      $TABLE_COUNT"
echo "Hypertables: $HYPER_COUNT"
echo "stock_minute: $MINUTE_HT"
echo "Alembic:     $ALEMBIC_VER"
echo "Verification completed."
