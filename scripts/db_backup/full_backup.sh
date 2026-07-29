#!/bin/bash
# WAITING_USER_EXECUTION (对 stable 执行时)
# 全量数据库备份脚本
# 使用 pg_dump --format=custom 生成备份 + SHA256 checksum + manifest
#
# 用法:
#   bash full_backup.sh --target /path/to/backup_dir
#   bash full_backup.sh --target /tmp/test_backup
#
# 输出格式: START|step=xxx / DONE|step=xxx / FAILED|step=xxx|rc=code
set -euo pipefail

LOG_FILE="/tmp/db_backup_full.log"
: > "$LOG_FILE"

# 参数解析
TARGET_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --target) TARGET_DIR="$2"; shift 2 ;;
    --retention) RETENTION_COUNT_OVERRIDE="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done
if [ -z "$TARGET_DIR" ]; then
  TARGET_DIR="${BACKUP_DIR:-/tmp/db_backups}"
fi

# 数据库配置
PG_HOST="${PG_HOST:-127.0.0.1}"
PG_PORT="${PG_PORT:-15432}"
PG_DB="${PG_DB:-quantstock1_test}"
PG_USER="${PG_USER:-quantstock1_test}"
PGPASSWORD="${PGPASSWORD:-test_password_only}"
export PGPASSWORD

# 保留策略：默认保留最近 7 份
RETENTION_COUNT="${RETENTION_COUNT_OVERRIDE:-${RETENTION_COUNT:-7}}"

# Docker 模式（如果设置 DOCKER_COMPOSE，使用 docker exec 执行 pg_dump）
DOCKER_COMPOSE="${DOCKER_COMPOSE:-}"

step() { echo "START|step=$1"; }
done_step() { echo "DONE|step=$1"; }
fail_step() { echo "FAILED|step=$1|rc=$2"; exit "$2"; }

TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_FILE="$TARGET_DIR/${PG_DB}_${TIMESTAMP}.dump"
SHA_FILE="$BACKUP_FILE.sha256"
MANIFEST_FILE="$TARGET_DIR/manifest_${TIMESTAMP}.json"

# Step 1: 创建备份目录
step "prepare_dir"
mkdir -p "$TARGET_DIR" 2>>"$LOG_FILE" || fail_step "prepare_dir" 1
echo "Backup directory: $TARGET_DIR" >>"$LOG_FILE"
done_step "prepare_dir"

# Step 2: 获取数据库元信息
step "gather_metadata"
if [ -n "$DOCKER_COMPOSE" ]; then
  PG_VERSION=$(docker compose -f "$DOCKER_COMPOSE" exec -T db psql -U "$PG_USER" -d "$PG_DB" -t -A -c "SHOW server_version;" 2>>"$LOG_FILE" | tr -d '[:space:]' || echo "unknown")
  ALEMBIC_REV=""
else
  PG_VERSION=$(psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -t -A -c "SHOW server_version;" 2>>"$LOG_FILE" | tr -d '[:space:]' || echo "unknown")
  ALEMBIC_REV=$(alembic current 2>>"$LOG_FILE" | grep -oP 'rev:\s*\K[a-z0-9_]+' || echo "unknown")
fi
echo "PG version: $PG_VERSION" >>"$LOG_FILE"
echo "Alembic rev: $ALEMBIC_REV" >>"$LOG_FILE"
done_step "gather_metadata"

# Step 3: 执行 pg_dump 全量备份
step "pg_dump"
if [ -n "$DOCKER_COMPOSE" ]; then
  docker compose -f "$DOCKER_COMPOSE" exec -T db pg_dump -U "$PG_USER" -d "$PG_DB" --format=custom > "$BACKUP_FILE" 2>>"$LOG_FILE" \
    || fail_step "pg_dump" 2
else
  pg_dump -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" --format=custom > "$BACKUP_FILE" 2>>"$LOG_FILE" \
    || fail_step "pg_dump" 2
fi
BACKUP_SIZE=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || stat -f%z "$BACKUP_FILE" 2>/dev/null || echo "0")
echo "Backup file: $BACKUP_FILE ($BACKUP_SIZE bytes)" >>"$LOG_FILE"
done_step "pg_dump"

# Step 4: 计算 SHA256 checksum
step "checksum"
sha256sum "$BACKUP_FILE" > "$SHA_FILE" 2>>"$LOG_FILE" || fail_step "checksum" 3
SHA256=$(cut -d' ' -f1 "$SHA_FILE")
echo "SHA256: $SHA256" >>"$LOG_FILE"
done_step "checksum"

# Step 5: 写入 manifest
step "write_manifest"
cat > "$MANIFEST_FILE" <<EOF
{
  "backup_format": "pg_dump custom",
  "backup_file": "$BACKUP_FILE",
  "timestamp": "$TIMESTAMP",
  "pg_version": "$PG_VERSION",
  "alembic_revision": "$ALEMBIC_REV",
  "database": "$PG_DB",
  "size_bytes": $BACKUP_SIZE,
  "checksum_algorithm": "sha256",
  "checksum": "$SHA256",
  "checksum_file": "$SHA_FILE",
  "retention_count": $RETENTION_COUNT,
  "include_timescaledb": true
}
EOF
echo "Manifest: $MANIFEST_FILE" >>"$LOG_FILE"
done_step "write_manifest"

# Step 6: 执行保留策略（保留最近 N 份）
step "retention"
BACKUP_COUNT=$(find "$TARGET_DIR" -name "${PG_DB}_*.dump" 2>>"$LOG_FILE" | wc -l)
if [ "$BACKUP_COUNT" -gt "$RETENTION_COUNT" ]; then
  find "$TARGET_DIR" -name "${PG_DB}_*.dump" -printf '%T@ %p\n' 2>>"$LOG_FILE" \
    | sort -n | head -n $((BACKUP_COUNT - RETENTION_COUNT)) \
    | while read -r _ old_file; do
      echo "Removing old backup: $old_file" >>"$LOG_FILE"
      rm -f "$old_file" "${old_file}.sha256"
    done
fi
REMAINING=$(find "$TARGET_DIR" -name "${PG_DB}_*.dump" 2>>"$LOG_FILE" | wc -l)
echo "Backups retained: $REMAINING (limit: $RETENTION_COUNT)" >>"$LOG_FILE"
done_step "retention"

echo ""
echo "=== Backup Summary ==="
echo "File:     $BACKUP_FILE"
echo "Size:     $BACKUP_SIZE bytes"
echo "SHA256:   $SHA256"
echo "Manifest: $MANIFEST_FILE"
echo "Backup completed."
