"""AuditEvent extension + run_type CHECK + DataGap VERIFIED + RAW evidence

Revision ID: 0015_audit_gap_rawev
Revises: 0014_pub_at_fin_dataitem
Create Date: 2026-07-29

Implements:
- DD-CORE-012/013: audit_event event_type/run_id/environment_id columns + append-only trigger.
- DD-CORE-003: run_type CHECK constraint with historical fix-up.
- DD-CORE-010: data_gap verification evidence columns (pre/post backfill count + checksum).
- DD-CORE-005: raw_batch content_hash/fetched_at/schema_fingerprint columns.
"""
import uuid

from alembic import op

revision = "0015_audit_gap_rawev"
down_revision = "0014_pub_at_fin_dataitem"
branch_labels = None
depends_on = None

NS = uuid.UUID("f49c0ed2-6b6d-4a65-9e8d-03de74809391")


def uid(value: str) -> uuid.UUID:
    return uuid.uuid5(NS, value)


VALID_RUN_TYPES = ("INITIALIZE", "INCREMENTAL", "BACKFILL", "REPAIR", "RETRY")


def upgrade() -> None:
    # ---- DD-CORE-012: AuditEvent field extension ----
    op.execute(
        "ALTER TABLE audit.audit_event "
        "ADD COLUMN IF NOT EXISTS event_type VARCHAR(64) NOT NULL DEFAULT 'state_change'"
    )
    op.execute(
        "ALTER TABLE audit.audit_event "
        "ADD COLUMN IF NOT EXISTS run_id UUID"
    )
    op.execute(
        "ALTER TABLE audit.audit_event "
        "ADD COLUMN IF NOT EXISTS environment_id VARCHAR(32) NOT NULL DEFAULT 'dev'"
    )

    # ---- DD-CORE-013: AuditEvent append-only trigger ----
    op.execute('''
        CREATE OR REPLACE FUNCTION audit.prevent_audit_event_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'audit_event is append-only: % prohibited (audit_event_id=%)',
                TG_OP, COALESCE(OLD.audit_event_id, NEW.audit_event_id);
        END;
        $$ LANGUAGE plpgsql
    ''')
    op.execute("DROP TRIGGER IF EXISTS trg_audit_event_append_only ON audit.audit_event")
    op.execute('''
        CREATE TRIGGER trg_audit_event_append_only
            BEFORE UPDATE OR DELETE ON audit.audit_event
            FOR EACH ROW EXECUTE FUNCTION audit.prevent_audit_event_modification()
    ''')

    # ---- DD-CORE-003: run_type CHECK constraint with historical fix-up ----
    # Map any non-canonical run_type value to the closest valid value before adding
    # the CHECK constraint, so the ALTER does not fail on legacy rows.
    fixup_mapping = {
        "INIT": "INITIALIZE",
        "INITIAL": "INITIALIZE",
        "INC": "INCREMENTAL",
        "INCR": "INCREMENTAL",
        "RETRY_RUN": "RETRY",
        "REPAIR_RUN": "REPAIR",
        "BACK_FILL": "BACKFILL",
        "FULL_REFRESH": "INITIALIZE",
        "FULL": "INITIALIZE",
    }
    for legacy, canonical in fixup_mapping.items():
        op.execute(
            f"""
            WITH fixed AS (
                SELECT task_id, run_type
                FROM ops.collect_task
                WHERE run_type = '{legacy}'
            )
            UPDATE ops.collect_task SET run_type = '{canonical}'
            WHERE task_id IN (SELECT task_id FROM fixed)
            """
        )

    # Any remaining run_type that is not in the canonical set is coerced to RETRY
    # (closest "manual intervention" semantics) and recorded via an audit_event.
    # The audit_event insert is best-effort: if there is nothing to fix the CTE
    # is empty and no audit row is written.
    op.execute('''
        INSERT INTO audit.audit_event (
            audit_event_id, object_type, object_id, action, reason,
            actor_type, actor_id, metadata, occurred_at,
            event_type, environment_id
        )
        SELECT
            gen_random_uuid(),
            'collect_task',
            task_id::text,
            'run_type_repaired',
            'non-canonical run_type coerced to RETRY during migration 0015',
            'system',
            'migration_0015',
            jsonb_build_object('old_run_type', run_type, 'new_run_type', 'RETRY'),
            now(),
            'run_type_repair',
            'dev'
        FROM ops.collect_task
        WHERE run_type NOT IN ('INITIALIZE','INCREMENTAL','BACKFILL','REPAIR','RETRY')
    ''')
    op.execute('''
        UPDATE ops.collect_task
        SET run_type = 'RETRY'
        WHERE run_type NOT IN ('INITIALIZE','INCREMENTAL','BACKFILL','REPAIR','RETRY')
    ''')

    op.execute('''
        ALTER TABLE ops.collect_task
        DROP CONSTRAINT IF EXISTS ck_collect_task_run_type
    ''')
    op.execute(
        "ALTER TABLE ops.collect_task "
        "ADD CONSTRAINT ck_collect_task_run_type "
        "CHECK (run_type IN ('INITIALIZE','INCREMENTAL','BACKFILL','REPAIR','RETRY'))"
    )

    # ---- DD-CORE-010: data_gap verification evidence columns ----
    op.execute(
        "ALTER TABLE quality.data_gap "
        "ADD COLUMN IF NOT EXISTS pre_backfill_count INT"
    )
    op.execute(
        "ALTER TABLE quality.data_gap "
        "ADD COLUMN IF NOT EXISTS post_backfill_count INT"
    )
    op.execute(
        "ALTER TABLE quality.data_gap "
        "ADD COLUMN IF NOT EXISTS checksum_verified BOOLEAN"
    )
    op.execute(
        "ALTER TABLE quality.data_gap "
        "ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ"
    )

    # ---- DD-CORE-005: raw_batch evidence columns ----
    op.execute(
        "ALTER TABLE raw.raw_batch "
        "ADD COLUMN IF NOT EXISTS content_hash VARCHAR(128)"
    )
    op.execute(
        "ALTER TABLE raw.raw_batch "
        "ADD COLUMN IF NOT EXISTS fetched_at TIMESTAMPTZ"
    )
    op.execute(
        "ALTER TABLE raw.raw_batch "
        "ADD COLUMN IF NOT EXISTS schema_fingerprint VARCHAR(128)"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_event_append_only ON audit.audit_event")
    op.execute("DROP FUNCTION IF EXISTS audit.prevent_audit_event_modification()")
    op.execute("ALTER TABLE ops.collect_task DROP CONSTRAINT IF EXISTS ck_collect_task_run_type")
    op.execute("ALTER TABLE raw.raw_batch DROP COLUMN IF EXISTS schema_fingerprint")
    op.execute("ALTER TABLE raw.raw_batch DROP COLUMN IF EXISTS fetched_at")
    op.execute("ALTER TABLE raw.raw_batch DROP COLUMN IF EXISTS content_hash")
    op.execute("ALTER TABLE quality.data_gap DROP COLUMN IF EXISTS verified_at")
    op.execute("ALTER TABLE quality.data_gap DROP COLUMN IF EXISTS checksum_verified")
    op.execute("ALTER TABLE quality.data_gap DROP COLUMN IF EXISTS post_backfill_count")
    op.execute("ALTER TABLE quality.data_gap DROP COLUMN IF EXISTS pre_backfill_count")
    op.execute("ALTER TABLE audit.audit_event DROP COLUMN IF EXISTS environment_id")
    op.execute("ALTER TABLE audit.audit_event DROP COLUMN IF EXISTS run_id")
    op.execute("ALTER TABLE audit.audit_event DROP COLUMN IF EXISTS event_type")
