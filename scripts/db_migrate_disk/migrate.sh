#!/bin/bash
# WAITING_USER_EXECUTION
# 数据库迁盘执行脚本（生成命令序列，不自动执行）
#
# 本脚本输出完整的迁盘命令序列，供运维人员审查后手动执行。
# 严禁自动执行任何 stable 不可逆操作（迁盘、删旧卷、开端口、替换正式数据库、扩大分钟历史）。
#
# 用法:
#   bash migrate.sh              # 生成命令序列
#   bash migrate.sh --dry-run    # 同上（显式 dry-run）
#
# 输出格式: START|step=xxx / DONE|step=xxx / FAILED|step=xxx|rc=code
set -euo pipefail

LOG_FILE="/tmp/db_migrate_run.log"
: > "$LOG_FILE"

# 源数据库配置（当前系统盘）
SRC_COMPOSE="${SRC_COMPOSE:-compose.dev.yml}"
SRC_PROJECT="${SRC_PROJECT:-quantstock1-dev}"
SRC_VOLUME="${SRC_VOLUME:-quantstock1_dev_pgdata}"
SRC_DB_NAME="${SRC_DB_NAME:-quantstock1}"
SRC_DB_USER="${SRC_DB_USER:-quantstock1}"

# 目标磁盘配置
DST_VOLUME="${DST_VOLUME:-quantstock1_data_pgdata}"
DST_MOUNT="${DST_MOUNT:-/mnt/data}"

# 备份临时目录
BACKUP_DIR="${BACKUP_DIR:-/tmp/db_migrate_backup}"

step() { echo "START|step=$1"; }
done_step() { echo "DONE|step=$1"; }
fail_step() { echo "FAILED|step=$1|rc=$2"; exit "$2"; }

emit() {
  echo "  $1"
}

emit_wait() {
  echo "WAITING_USER_EXECUTION:"
  echo "  $1"
}

echo "================================================"
echo " Database Migration Disk Plan"
echo " Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "================================================"
echo ""

# Step 1: 预检
step "precheck"
echo "--- Step 1: Precheck ---"
emit "bash scripts/db_migrate_disk/precheck.sh"
echo "  # => 运行预检脚本，确认所有前置条件满足"
done_step "precheck"
echo ""

# Step 2: 停止服务（确保无写入）
step "stop_services"
echo "--- Step 2: Stop Services ---"
emit_wait "docker compose -f $SRC_COMPOSE --project-name $SRC_PROJECT stop"
echo "  # => 停止所有依赖数据库的服务，确保迁移期间无写入"
done_step "stop_services"
echo ""

# Step 3: 全量备份（回滚保险）
step "backup"
echo "--- Step 3: Full Backup ---"
emit "mkdir -p $BACKUP_DIR"
emit_wait "docker compose -f $SRC_COMPOSE --project-name $SRC_PROJECT exec -T db \\"
emit "  pg_dump -U $SRC_DB_USER -d $SRC_DB_NAME --format=custom -f /tmp/migrate.dump"
emit_wait "docker compose -f $SRC_COMPOSE --project-name $SRC_PROJECT \\"
emit "  cp db:/tmp/migrate.dump $BACKUP_DIR/migrate.dump"
emit "sha256sum $BACKUP_DIR/migrate.dump > $BACKUP_DIR/migrate.dump.sha256"
echo "  # => 生成全量备份 + checksum，作为回滚保险"
done_step "backup"
echo ""

# Step 4: 创建新 volume / 挂载目标磁盘
step "create_target_volume"
echo "--- Step 4: Create Target Volume ---"
emit_wait "docker volume create $DST_VOLUME"
emit "# 或在 $DST_MOUNT 挂载新磁盘后创建绑定卷:"
emit_wait "# docker volume create --driver local --opt type=none --opt device=$DST_MOUNT \\"
emit "#   --opt o=bind $DST_VOLUME"
done_step "create_target_volume"
echo ""

# Step 5: 启动临时 PG 容器并 restore
step "restore_to_new_volume"
echo "--- Step 5: Restore to New Volume ---"
emit_wait "docker run -d --name pg-migrate-tmp \\"
emit "  -v $DST_VOLUME:/var/lib/postgresql/data \\"
emit "  -e POSTGRES_DB=$SRC_DB_NAME \\"
emit "  -e POSTGRES_USER=$SRC_DB_USER \\"
emit "  -e POSTGRES_PASSWORD=<set_password> \\"
emit "  timescale/timescaledb:2.28.3-pg16"
emit "# 等待容器健康后执行 restore:"
emit_wait "docker cp $BACKUP_DIR/migrate.dump pg-migrate-tmp:/tmp/migrate.dump"
emit_wait "docker exec -T pg-migrate-tmp \\"
emit "  pg_restore -U $SRC_DB_USER -d $SRC_DB_NAME --no-owner --no-privileges /tmp/migrate.dump"
done_step "restore_to_new_volume"
echo ""

# Step 6: 更新 compose 配置指向新 volume
step "update_compose"
echo "--- Step 6: Update Compose Configuration ---"
emit "# 编辑 $SRC_COMPOSE，将 volume 从 $SRC_VOLUME 改为 $DST_VOLUME"
emit "# 或创建新的 compose 文件指向新 volume"
emit_wait "# 手动编辑 compose 文件后验证配置:"
emit "# docker compose -f <new-compose> config"
done_step "update_compose"
echo ""

# Step 7: 重启服务并验证
step "restart_and_verify"
echo "--- Step 7: Restart and Verify ---"
emit_wait "docker compose -f $SRC_COMPOSE --project-name $SRC_PROJECT up -d --wait"
emit "docker compose -f $SRC_COMPOSE --project-name $SRC_PROJECT exec db pg_isready"
emit "cd $PROJECT_ROOT && alembic current  # 确认迁移版本一致"
emit "bash scripts/db_restore/verify.sh  # 运行完整验证"
done_step "restart_and_verify"
echo ""

# Step 8: 验证通过后清理临时资源（高风险，最后执行）
step "cleanup"
echo "--- Step 8: Cleanup (HIGH RISK - only after full verification) ---"
emit_wait "docker rm -f pg-migrate-tmp"
emit_wait "# 确认新 volume 工作正常后，方可删除旧 volume:"
emit_wait "docker volume rm $SRC_VOLUME  # 不可逆操作，需双重确认"
done_step "cleanup"
echo ""

echo "================================================"
echo " Migration plan generated successfully."
echo " Review and execute each WAITING_USER_EXECUTION step manually."
echo " Log: $LOG_FILE"
echo "================================================"
