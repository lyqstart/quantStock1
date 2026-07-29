"""lineage schema + lineage_edge + data_snapshot tables

Revision ID: 0013_lineage_and_snapshot
Revises: 0012_p4_minute_governance
Create Date: 2026-07-29

Implements DD-CORE-011 (lineage_edge) and DD-CORE-015 (data_snapshot + data_snapshot_input
with READY-immutability trigger). Backed by REQ-CORE-013/019/020.
"""
from alembic import op

revision = "0013_lineage_and_snapshot"
down_revision = "0012_p4_minute_governance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- lineage schema + lineage.lineage_edge (DD-CORE-011) ----
    op.execute("CREATE SCHEMA IF NOT EXISTS lineage")
    op.execute('''
        CREATE TABLE IF NOT EXISTS lineage.lineage_edge (
            edge_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_type VARCHAR(64) NOT NULL,
            source_id UUID NOT NULL,
            target_type VARCHAR(64) NOT NULL,
            target_id UUID NOT NULL,
            edge_type VARCHAR(64) NOT NULL,
            scope_key VARCHAR(512),
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            trace_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    ''')
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_lineage_edge_source "
        "ON lineage.lineage_edge (source_type, source_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_lineage_edge_target "
        "ON lineage.lineage_edge (target_type, target_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_lineage_edge_type "
        "ON lineage.lineage_edge (edge_type)"
    )

    # ---- clean.data_snapshot (DD-CORE-015) ----
    op.execute('''
        CREATE TABLE IF NOT EXISTS clean.data_snapshot (
            snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            data_item_codes TEXT[] NOT NULL,
            as_of_time TIMESTAMPTZ NOT NULL,
            available_at_cutoff TIMESTAMPTZ NOT NULL,
            quality_policy VARCHAR(32) NOT NULL DEFAULT 'strict',
            adjustment_policy VARCHAR(32) NOT NULL DEFAULT 'none',
            status VARCHAR(16) NOT NULL DEFAULT 'BUILDING'
                CHECK (status IN ('BUILDING','READY','INVALIDATED')),
            content_fingerprint VARCHAR(128),
            supersedes_snapshot_id UUID REFERENCES clean.data_snapshot(snapshot_id),
            total_rows BIGINT NOT NULL DEFAULT 0,
            clean_batch_count INT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            ready_at TIMESTAMPTZ,
            invalidated_at TIMESTAMPTZ
        )
    ''')
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_data_snapshot_status_cutoff "
        "ON clean.data_snapshot (status, available_at_cutoff DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_data_snapshot_as_of "
        "ON clean.data_snapshot (as_of_time DESC)"
    )

    # ---- clean.data_snapshot_input (DD-CORE-015) ----
    op.execute('''
        CREATE TABLE IF NOT EXISTS clean.data_snapshot_input (
            snapshot_id UUID NOT NULL REFERENCES clean.data_snapshot(snapshot_id),
            clean_batch_id UUID NOT NULL REFERENCES clean.clean_batch(clean_batch_id),
            data_item_id UUID NOT NULL REFERENCES meta.data_item(data_item_id),
            input_role VARCHAR(16) NOT NULL DEFAULT 'PRIMARY',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (snapshot_id, clean_batch_id)
        )
    ''')
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_data_snapshot_input_item "
        "ON clean.data_snapshot_input (data_item_id)"
    )

    # ---- READY immutability trigger (DD-CORE-015) ----
    # Block UPDATE/DELETE on rows whose current or new status is READY.
    op.execute('''
        CREATE OR REPLACE FUNCTION clean.prevent_snapshot_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                IF OLD.status = 'READY' THEN
                    RAISE EXCEPTION 'data_snapshot is immutable in READY status: DELETE prohibited (snapshot_id=%)', OLD.snapshot_id;
                END IF;
                RETURN OLD;
            END IF;
            -- TG_OP = 'UPDATE'
            IF OLD.status = 'READY' OR NEW.status = 'READY' THEN
                RAISE EXCEPTION 'data_snapshot is immutable in READY status: UPDATE prohibited (snapshot_id=%)', OLD.snapshot_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    ''')
    op.execute('''
        DROP TRIGGER IF EXISTS trg_data_snapshot_no_modify_ready ON clean.data_snapshot
    ''')
    op.execute('''
        CREATE TRIGGER trg_data_snapshot_no_modify_ready
            BEFORE UPDATE OR DELETE ON clean.data_snapshot
            FOR EACH ROW EXECUTE FUNCTION clean.prevent_snapshot_modification()
    ''')


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_data_snapshot_no_modify_ready ON clean.data_snapshot")
    op.execute("DROP FUNCTION IF EXISTS clean.prevent_snapshot_modification()")
    op.execute("DROP TABLE IF EXISTS clean.data_snapshot_input")
    op.execute("DROP TABLE IF EXISTS clean.data_snapshot")
    op.execute("DROP TABLE IF EXISTS lineage.lineage_edge")
    # Keep schemas in place: clean schema hosts other tables; lineage schema is
    # only used by lineage_edge but dropping it would break downstream tooling
    # that references it. Leaving empty schemas is safe and matches the
    # convention applied to other governance schemas in earlier revisions.
