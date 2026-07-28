"""P4 minute governance and storage policy baseline

Revision ID: 0012_p4_minute_governance
Revises: 0011_p4_daily_governance
Create Date: 2026-07-28
"""
import uuid

from alembic import op

revision = "0012_p4_minute_governance"
down_revision = "0011_p4_daily_governance"
branch_labels = None
depends_on = None

NS = uuid.UUID("f49c0ed2-6b6d-4a65-9e8d-03de74809391")


def uid(value: str) -> uuid.UUID:
    return uuid.uuid5(NS, value)


def _create_task_definition(stage: str) -> None:
    op.execute(f'''
        INSERT INTO ops.task_definition (
            task_definition_id, task_code, data_item_id, source_binding_id, task_type,
            update_mode, schedule_rule, availability_rule, split_policy_version,
            retry_policy_version, priority, enabled, definition_version
        ) VALUES (
            '{uid(f"taskdef:{stage}:stock_minute")}',
            '{stage}:stock_minute',
            '{uid("item:stock_minute")}',
            '{uid("binding:tushare:stock_minute")}',
            '{stage}', 'event', '{{}}'::jsonb, '{{}}'::jsonb,
            'p4-v1', 'p4-v1', 5, true, 'p4-v1'
        ) ON CONFLICT (task_code) DO NOTHING
    ''')


def upgrade() -> None:
    op.execute('''
        CREATE TABLE meta.storage_policy (
            storage_policy_id UUID PRIMARY KEY,
            policy_code VARCHAR(128) NOT NULL,
            data_item_id UUID NOT NULL REFERENCES meta.data_item(data_item_id),
            data_layer VARCHAR(16) NOT NULL,
            storage_class VARCHAR(16) NOT NULL,
            partition_mode VARCHAR(64),
            chunk_interval VARCHAR(64),
            compression_enabled BOOLEAN NOT NULL DEFAULT false,
            hot_mutable_window VARCHAR(64),
            online_retention VARCHAR(64),
            archive_required BOOLEAN NOT NULL DEFAULT false,
            policy_version VARCHAR(32) NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT true,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_storage_policy_code_version UNIQUE(policy_code, policy_version)
        )
    ''')

    op.execute('''
        CREATE TABLE clean.stock_minute (
            security_code VARCHAR(16) NOT NULL,
            frequency VARCHAR(8) NOT NULL,
            trade_time TIMESTAMPTZ NOT NULL,
            open DOUBLE PRECISION NOT NULL,
            high DOUBLE PRECISION NOT NULL,
            low DOUBLE PRECISION NOT NULL,
            close DOUBLE PRECISION NOT NULL,
            volume_share BIGINT,
            amount_cny DOUBLE PRECISION,
            _clean_batch_id UUID NOT NULL REFERENCES clean.clean_batch(clean_batch_id),
            PRIMARY KEY(security_code, frequency, trade_time)
        )
    ''')
    # Keep the extension default interval only as a provisional physical setting.
    # The approved chunk interval remains NULL in StoragePolicy until real capacity benchmarking.
    op.execute("SELECT create_hypertable('clean.stock_minute', by_range('trade_time'), if_not_exists => TRUE)")

    op.execute(f'''
        INSERT INTO meta.storage_policy (
            storage_policy_id, policy_code, data_item_id, data_layer, storage_class,
            partition_mode, chunk_interval, compression_enabled, hot_mutable_window,
            online_retention, archive_required, policy_version, enabled, notes
        ) VALUES
        (
            '{uid("storage-policy:stock_minute:raw:v1")}',
            'stock_minute.raw', '{uid("item:stock_minute")}', 'RAW', 'HOT',
            'POSTGRESQL_PENDING_TIMESCALE', NULL, false, NULL, NULL, true,
            'storage-v1', true,
            'RAW minute conversion is deferred until the source-text trade_time/primary-key migration is benchmarked and proven safe.'
        ),
        (
            '{uid("storage-policy:stock_minute:clean:v1")}',
            'stock_minute.clean', '{uid("item:stock_minute")}', 'CLEAN', 'HOT',
            'TIMESCALE_TIME', NULL, false, NULL, NULL, false,
            'storage-v1', true,
            'Hypertable is enabled. Final chunk interval and columnstore policy are intentionally unapproved until P4-3 capacity evidence exists.'
        )
    ''')

    _create_task_definition("clean")
    _create_task_definition("quality")


def downgrade() -> None:
    op.execute("DELETE FROM ops.task_definition WHERE task_code IN ('clean:stock_minute','quality:stock_minute')")
    op.execute("DELETE FROM meta.storage_policy WHERE policy_code IN ('stock_minute.raw','stock_minute.clean')")
    op.execute("DROP TABLE IF EXISTS clean.stock_minute")
    op.execute("DROP TABLE IF EXISTS meta.storage_policy")
