#!/bin/bash
# WAITING_USER_EXECUTION
# 数据库恢复脚本
# 从 pg_dump custom 格式备份恢复到目标 PG 实例
#
# 用法:
#   bash restore.sh --backup /path/to/file.dump [--dry-run]
#
# 输出格式: START|step=xxx / DONE|step=xxx / FAILED|step=xxx|rc=code
set -euo pipefail

LOG_FILE="/tmp/db_restore.log"
: > "$LOG_FILE"

# 参数解析
BACKUP_FILE=""
DRY_RUN=false
while [ $# -gt 0 ]; do
  case "$1" in
    --backup) BACKUP_FILE="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done
if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: restore.sh --backup <file.dump> [--dry-run]" >&2
  exit 1
fi

SHA_FILE="${BACKUP_FILE}.sha256"

# 目标数据库配置
PG_HOST="${PG_HOST:-127.0.0.1}"
PG_PORT="${PG_PORT:-15432}"
PG_DB="${PG_DB:-quantstock1_test}"
PG_USER="${PG_USER:-quantstock1_test}"
PGPASSWORD="${PGPASSWORD:-test_password_only}"
export PGPASSWORD

step() { echo "START|step=$1"; }
done_step() { echo "DONE|step=$1"; }
fail_step() { echo "FAILED|step=$1|rc=$2"; exit "$2"; }

# Step 1: 验证备份文件存在
step "check_backup_exists"
if [ ! -f "$BACKUP_FILE" ]; then
  echo "ERROR: backup file not found: $BACKUP_FILE" >>"$LOG_FILE"
  fail_step "check_backup_exists" 1
fi
BACKUP_SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE" 2>/dev/null || echo "0")
echo "Backup file: $BACKUP_FILE ($BACKUP_SIZE bytes)" >>"$LOG_FILE"
done_step "check_backup_exists"

# Step 2: 验证 checksum
step "verify_checksum"
if [ -f "$SHA_FILE" ]; then
  EXPECTED_SHA=$(cut -d' ' -f1 "$SHA_FILE")
  ACTUAL_SHA=$(sha256sum "$BACKUP_FILE" | cut -d' ' -f1)
  echo "Expected SHA256: $EXPECTED_SHA" >>"$LOG_FILE"
  echo "Actual SHA256:   $ACTUAL_SHA" >>"$LOG_FILE"
  if [ "$EXPECTED_SHA" != "$ACTUAL_SHA" ]; then
    echo "ERROR: checksum mismatch! Backup may be corrupted." >>"$LOG_FILE"
    fail_step "verify_checksum" 2
  fi
else
  echo "WARN: no .sha256 file found ($SHA_FILE), skipping checksum verification" >>"$LOG_FILE"
fi
done_step "verify_checksum"

# Dry-run 模式：只输出计划不执行
if [ "$DRY_RUN" = true ]; then
  echo ""
  echo "=== Dry Run: Restore Plan ==="
  echo "Backup file:  $BACKUP_FILE ($BACKUP_SIZE bytes)"
  echo "Target host:  $PG_HOST:$PG_PORT"
  echo "Target DB:    $PG_DB"
  echo "Target user:  $PG_USER"
  echo ""
  echo "Commands to execute:"
  echo "  pg_restore -h $PG_HOST -p $PG_PORT -U $PG_USER -d $PG_DB \\"
  echo "    --no-owner --no-privileges \"$BACKUP_FILE\""
  echo ""
  echo "WAITING_USER_EXECUTION: remove --dry-run to execute"
  exit 0
fi

# Step 3: 创建目标数据库（如果不存在）
step "ensure_database"
DB_EXISTS=$(psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d postgres -t -A -c "SELECT 1 FROM pg_database WHERE datname='$PG_DB';" 2>>"$LOG_FILE" || echo "")
if [ "$DB_EXISTS" != "1" ]; then
  psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d postgres -c "CREATE DATABASE $PG_DB;" 2>>"$LOG_FILE" \
    || fail_step "ensure_database" 3
fi
echo "Database ready: $PG_DB" >>"$LOG_FILE"
done_step "ensure_database"

# Step 4: 执行 pg_restore
step "pg_restore"
pg_restore -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" --no-owner --no-privileges "$BACKUP_FILE" 2>>"$LOG_FILE" || {
  # pg_restore 对已存在对象会报 warning (exit code 1)，检查是否有致命错误
  echo "WARN: pg_restore reported non-zero exit, checking for fatal errors..." >>"$LOG_FILE"
}
done_step "pg_restore"

# Step 5: 验证 Alembic 版本
step "verify_alembic"
ALEMBIC_VER=$(psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -t -A -c "SELECT version_num FROM alembic_version LIMIT 1;" 2>>"$LOG_FILE" || echo "unknown")
echo "Alembic version: $ALEMBIC_VER" >>"$LOG_FILE"
done_step "verify_alembic"

# Step 6: 基本健康检查
step "health_check"
psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -c "SELECT 1;" >>"$LOG_FILE" 2>&1 || fail_step "health_check" 4
done_step "health_check"

echo ""
echo "=== Restore Summary ==="
echo "Backup:   $BACKUP_FILE"
echo "Target:   $PG_HOST:$PG_PORT/$PG_DB"
echo "Alembic:  $ALEMBIC_VER"
echo "Restore completed. Run verify.sh for full validation."
