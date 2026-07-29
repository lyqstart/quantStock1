#!/bin/bash
# WAITING_USER_EXECUTION
# 分钟数据压缩 chunk 归档脚本
# 导出超过保留期的压缩 chunk 到归档文件，删除 chunk 需要用户确认
#
# 用法:
#   bash archive.sh --dry-run                  # 预览将归档的 chunk
#   bash archive.sh --export /path/to/dir      # 导出 chunk 到指定目录
#   bash archive.sh --export /path --retention-days 365
#
# 输出格式: START|step=xxx / DONE|step=xxx / FAILED|step=xxx|rc=code
set -euo pipefail

LOG_FILE="/tmp/minute_archive.log"
: > "$LOG_FILE"

# 参数解析
DRY_RUN=false
EXPORT_DIR=""
RETENTION_DAYS="${RETENTION_DAYS:-365}"
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --export) EXPORT_DIR="$2"; shift 2 ;;
    --retention-days) RETENTION_DAYS="$2"; shift 2 ;;
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

TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)

# Step 1: 查询超过保留期的压缩 chunk
step "query_expired_chunks"
EXPIRED_CHUNKS=$(psql_exec "
  SELECT chunk_name
  FROM timescaledb_information.chunks
  WHERE hypertable_name = 'stock_minute'
    AND range_end < (now() - interval '${RETENTION_DAYS} days')
    AND is_compressed = true
  ORDER BY range_start;
" 2>>"$LOG_FILE" || echo "")
if [ -z "$EXPIRED_CHUNKS" ]; then
  CHUNK_COUNT=0
else
  CHUNK_COUNT=$(echo "$EXPIRED_CHUNKS" | grep -c . 2>>"$LOG_FILE" || echo "0")
fi
echo "Expired compressed chunks: $CHUNK_COUNT (retention: ${RETENTION_DAYS}d)" >>"$LOG_FILE"
echo "Expired compressed chunks (retention ${RETENTION_DAYS} days):"
if [ "$CHUNK_COUNT" -gt 0 ]; then
  echo "$EXPIRED_CHUNKS" | head -20
else
  echo "  (none)"
fi
done_step "query_expired_chunks"

if [ "$CHUNK_COUNT" -eq 0 ]; then
  echo "No expired chunks to archive."
  exit 0
fi

# Step 2: 导出压缩 chunk（仅当指定 --export 时）
if [ -n "$EXPORT_DIR" ]; then
  step "export_chunks"
  mkdir -p "$EXPORT_DIR" 2>>"$LOG_FILE" || fail_step "export_chunks" 1

  ARCHIVE_MANIFEST="$EXPORT_DIR/archive_manifest_${TIMESTAMP}.txt"
  : > "$ARCHIVE_MANIFEST"

  echo "$EXPIRED_CHUNKS" | while IFS= read -r chunk; do
    [ -z "$chunk" ] && continue
    DUMP_FILE="$EXPORT_DIR/${chunk}_${TIMESTAMP}.sql.gz"
    echo "Exporting chunk: $chunk -> $DUMP_FILE" >>"$LOG_FILE"
    echo "WAITING_USER_EXECUTION: export $chunk"
    echo "  pg_dump -h $PG_HOST -p $PG_PORT -U $PG_USER -d $PG_DB \\"
    echo "    --data-only --table _timescaledb_internal.$chunk | gzip > $DUMP_FILE"
    echo "$chunk|$DUMP_FILE" >> "$ARCHIVE_MANIFEST"
  done
  echo "Archive manifest: $ARCHIVE_MANIFEST" >>"$LOG_FILE"
  done_step "export_chunks"

  # Step 3: 计算 checksum
  step "checksum"
  if [ -f "$ARCHIVE_MANIFEST" ]; then
    while IFS='|' read -r chunk dump_file; do
      if [ -f "$dump_file" ]; then
        sha256sum "$dump_file" > "${dump_file}.sha256"
        echo "checksum written: ${dump_file}.sha256" >>"$LOG_FILE"
      fi
    done < "$ARCHIVE_MANIFEST"
  fi
  done_step "checksum"

  # Step 4: 验证导出完整性
  step "verify_export"
  VERIFY_FAIL=0
  while IFS='|' read -r chunk dump_file; do
    if [ ! -f "$dump_file" ] || [ ! -f "${dump_file}.sha256" ]; then
      echo "ERROR: missing export or checksum for chunk $chunk" >>"$LOG_FILE"
      VERIFY_FAIL=1
    fi
  done < "$ARCHIVE_MANIFEST"
  if [ "$VERIFY_FAIL" -ne 0 ]; then
    fail_step "verify_export" 2
  fi
  echo "All exports verified with checksum." >>"$LOG_FILE"
  done_step "verify_export"
fi

# Step 5: 删除已归档 chunk（高风险，必须用户确认）
step "drop_archived_chunks"
echo "WAITING_USER_EXECUTION: the following archived chunks can be dropped:"
echo "  # Verify archive integrity before dropping!"
if [ "$CHUNK_COUNT" -gt 0 ]; then
  echo "$EXPIRED_CHUNKS" | while IFS= read -r chunk; do
    [ -z "$chunk" ] && continue
    echo "  SELECT drop_chunks('stock_minute', TIMESTAMP '<chunk_range_end>');  -- $chunk"
  done
fi
echo "  # Confirm each drop manually after verifying archive checksum."
done_step "drop_archived_chunks"

echo ""
echo "=== Archive Summary ==="
echo "Expired chunks:  $CHUNK_COUNT"
echo "Retention:       ${RETENTION_DAYS} days"
echo "Export dir:      ${EXPORT_DIR:-N/A (dry-run)}"
echo "Manifest:        ${EXPORT_DIR:-.}/archive_manifest_${TIMESTAMP}.txt"
echo "Log:             $LOG_FILE"
