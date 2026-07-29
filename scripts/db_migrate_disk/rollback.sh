#!/bin/bash
# 数据库迁盘回滚脚本
# 当迁盘失败或验证不通过时，恢复到迁盘前的状态
#
# 输出格式: START|step=xxx / DONE|step=xxx / FAILED|step=xxx|rc=code
set -euo pipefail

LOG_FILE="/tmp/db_migrate_rollback.log"
: > "$LOG_FILE"

# 源配置（迁盘前的原始状态）
SRC_COMPOSE="${SRC_COMPOSE:-compose.dev.yml}"
SRC_PROJECT="${SRC_PROJECT:-quantstock1-dev}"
SRC_VOLUME="${SRC_VOLUME:-quantstock1_dev_pgdata}"
DST_VOLUME="${DST_VOLUME:-quantstock1_data_pgdata}"
BACKUP_DIR="${BACKUP_DIR:-/tmp/db_migrate_backup}"

step() { echo "START|step=$1"; }
done_step() { echo "DONE|step=$1"; }
fail_step() { echo "FAILED|step=$1|rc=$2"; exit "$2"; }

echo "================================================"
echo " Database Migration Rollback Plan"
echo " Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "================================================"
echo ""

# Step 1: 停止使用新 volume 的服务
step "stop_services"
echo "--- Step 1: Stop Services ---"
echo "WAITING_USER_EXECUTION:"
echo "  docker compose -f $SRC_COMPOSE --project-name $SRC_PROJECT stop"
echo "  # => 停止所有服务，避免在新 volume 上继续写入"
done_step "stop_services"
echo ""

# Step 2: 恢复原始 compose 配置
step "restore_compose"
echo "--- Step 2: Restore Original Compose Configuration ---"
echo "  # 将 $SRC_COMPOSE 中的 volume 改回 $SRC_VOLUME"
echo "  # 方法1 (git):"
echo "    git checkout $SRC_COMPOSE"
echo "  # 方法2 (手动):"
echo "    # 编辑 compose 文件，将 volume 引用从 $DST_VOLUME 改回 $SRC_VOLUME"
done_step "restore_compose"
echo ""

# Step 3: 重启服务到旧 volume
step "restart_old_volume"
echo "--- Step 3: Restart on Old Volume ---"
echo "WAITING_USER_EXECUTION:"
echo "  docker compose -f $SRC_COMPOSE --project-name $SRC_PROJECT up -d --wait"
echo "  # => 使用原始 volume 重启服务"
done_step "restart_old_volume"
echo ""

# Step 4: 验证旧 volume 数据可用
step "verify_old_volume"
echo "--- Step 4: Verify Old Volume ---"
echo "  docker compose -f $SRC_COMPOSE --project-name $SRC_PROJECT exec db pg_isready"
echo "  docker compose -f $SRC_COMPOSE --project-name $SRC_PROJECT exec db \\"
echo "    psql -U <user> -d <db> -c 'SELECT count(*) FROM meta.data_item;'"
echo "  alembic current  # 确认迁移版本正确"
echo "  bash scripts/db_restore/verify.sh"
done_step "verify_old_volume"
echo ""

# Step 5: （可选）从备份恢复数据（如果旧 volume 已损坏）
step "restore_from_backup"
echo "--- Step 5: Restore from Backup (only if old volume corrupted) ---"
echo "  # 若旧 volume 已损坏，从迁盘前的备份恢复:"
echo "WAITING_USER_EXECUTION:"
echo "  docker volume rm $SRC_VOLUME"
echo "  docker volume create $SRC_VOLUME"
echo "WAITING_USER_EXECUTION:"
echo "  docker run --rm \\"
echo "    -v $SRC_VOLUME:/var/lib/postgresql/data \\"
echo "    -v $BACKUP_DIR:/backup \\"
echo "    -e POSTGRES_DB=<db> \\"
echo "    -e POSTGRES_USER=<user> \\"
echo "    timescale/timescaledb:2.28.3-pg16 \\"
echo "    pg_restore -U <user> -d <db> /backup/migrate.dump"
done_step "restore_from_backup"
echo ""

# Step 6: 清理失败的新 volume
step "cleanup_failed_volume"
echo "--- Step 6: Cleanup Failed New Volume ---"
echo "WAITING_USER_EXECUTION:"
echo "  docker volume rm $DST_VOLUME  # 仅在确认不再需要时删除"
done_step "cleanup_failed_volume"
echo ""

echo "================================================"
echo " Rollback plan generated."
echo " Execute each WAITING_USER_EXECUTION step manually."
echo " Log: $LOG_FILE"
echo "================================================"
