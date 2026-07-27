"""P4 governance for core daily market items

Revision ID: 0011_p4_daily_governance
Revises: 0010_p4_skip_audit
Create Date: 2026-07-28
"""
import uuid

from alembic import op

revision = "0011_p4_daily_governance"
down_revision = "0010_p4_skip_audit"
branch_labels = None
depends_on = None

NS = uuid.UUID("f49c0ed2-6b6d-4a65-9e8d-03de74809391")


def uid(value: str) -> uuid.UUID:
    return uuid.uuid5(NS, value)


def _create_task_definition(*, stage: str, item_code: str) -> None:
    op.execute(f'''
        INSERT INTO ops.task_definition (
            task_definition_id, task_code, data_item_id, source_binding_id, task_type,
            update_mode, schedule_rule, availability_rule, split_policy_version,
            retry_policy_version, priority, enabled, definition_version
        ) VALUES (
            '{uid(f"taskdef:{stage}:{item_code}")}',
            '{stage}:{item_code}',
            '{uid(f"item:{item_code}")}',
            '{uid(f"binding:tushare:{item_code}")}',
            '{stage}',
            'event',
            '{{}}'::jsonb,
            '{{}}'::jsonb,
            'p4-v1',
            'p4-v1',
            5,
            true,
            'p4-v1'
        ) ON CONFLICT (task_code) DO NOTHING
    ''')


def upgrade() -> None:
    op.execute('''
        CREATE TABLE clean.stock_adj_factor (
            security_code VARCHAR(16) NOT NULL,
            trade_date DATE NOT NULL,
            adj_factor DOUBLE PRECISION NOT NULL,
            _clean_batch_id UUID NOT NULL REFERENCES clean.clean_batch(clean_batch_id),
            _source VARCHAR(32) NOT NULL,
            _available_at TIMESTAMPTZ NOT NULL,
            _quality_status VARCHAR(16) NOT NULL,
            _mapping_version VARCHAR(32) NOT NULL,
            _normalization_version VARCHAR(32) NOT NULL,
            _quality_rule_version VARCHAR(32) NOT NULL,
            _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            _updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY(security_code, trade_date)
        )
    ''')
    op.execute("CREATE INDEX ix_clean_adj_factor_date_code ON clean.stock_adj_factor(trade_date, security_code)")

    op.execute('''
        CREATE TABLE clean.stock_adj_factor_history (
            adj_factor_version_id UUID PRIMARY KEY,
            security_code VARCHAR(16) NOT NULL,
            trade_date DATE NOT NULL,
            adj_factor DOUBLE PRECISION NOT NULL,
            observed_from TIMESTAMPTZ NOT NULL,
            observed_to TIMESTAMPTZ,
            content_hash VARCHAR(64) NOT NULL,
            _clean_batch_id UUID NOT NULL REFERENCES clean.clean_batch(clean_batch_id),
            _source VARCHAR(32) NOT NULL,
            _created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    ''')
    op.execute("CREATE INDEX ix_adj_factor_history_code_date_time ON clean.stock_adj_factor_history(security_code, trade_date, observed_from DESC)")
    op.execute("CREATE UNIQUE INDEX uq_adj_factor_history_current ON clean.stock_adj_factor_history(security_code, trade_date) WHERE observed_to IS NULL")

    op.execute('''
        CREATE TABLE clean.stock_daily_basic (
            security_code VARCHAR(16) NOT NULL,
            trade_date DATE NOT NULL,
            close DOUBLE PRECISION,
            turnover_rate DOUBLE PRECISION,
            turnover_rate_free DOUBLE PRECISION,
            volume_ratio DOUBLE PRECISION,
            pe DOUBLE PRECISION,
            pe_ttm DOUBLE PRECISION,
            pb DOUBLE PRECISION,
            ps DOUBLE PRECISION,
            ps_ttm DOUBLE PRECISION,
            dividend_yield DOUBLE PRECISION,
            dividend_yield_ttm DOUBLE PRECISION,
            total_share BIGINT,
            float_share BIGINT,
            free_share BIGINT,
            total_market_value_cny DOUBLE PRECISION,
            circulating_market_value_cny DOUBLE PRECISION,
            limit_status SMALLINT,
            _clean_batch_id UUID NOT NULL REFERENCES clean.clean_batch(clean_batch_id),
            _source VARCHAR(32) NOT NULL,
            _available_at TIMESTAMPTZ NOT NULL,
            _quality_status VARCHAR(16) NOT NULL,
            _mapping_version VARCHAR(32) NOT NULL,
            _normalization_version VARCHAR(32) NOT NULL,
            _quality_rule_version VARCHAR(32) NOT NULL,
            _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            _updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY(security_code, trade_date)
        )
    ''')
    op.execute("CREATE INDEX ix_clean_daily_basic_date_code ON clean.stock_daily_basic(trade_date, security_code)")

    op.execute('''
        CREATE TABLE clean.stock_suspend_event (
            suspend_event_id UUID PRIMARY KEY,
            security_code VARCHAR(16) NOT NULL,
            trade_date DATE NOT NULL,
            event_type VARCHAR(8) NOT NULL,
            suspend_timing VARCHAR(64),
            _clean_batch_id UUID NOT NULL REFERENCES clean.clean_batch(clean_batch_id),
            _source VARCHAR(32) NOT NULL,
            _available_at TIMESTAMPTZ NOT NULL,
            _quality_status VARCHAR(16) NOT NULL,
            _mapping_version VARCHAR(32) NOT NULL,
            _normalization_version VARCHAR(32) NOT NULL,
            _quality_rule_version VARCHAR(32) NOT NULL,
            _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            _updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    ''')
    op.execute("CREATE UNIQUE INDEX uq_clean_suspend_event_business ON clean.stock_suspend_event(security_code, trade_date, event_type, COALESCE(suspend_timing, ''))")
    op.execute("CREATE INDEX ix_clean_suspend_event_code_date ON clean.stock_suspend_event(security_code, trade_date)")
    op.execute("CREATE INDEX ix_clean_suspend_event_date_code ON clean.stock_suspend_event(trade_date, security_code)")

    op.execute('''
        CREATE TABLE clean.stock_limit_price (
            security_code VARCHAR(16) NOT NULL,
            trade_date DATE NOT NULL,
            pre_close DOUBLE PRECISION,
            up_limit DOUBLE PRECISION,
            down_limit DOUBLE PRECISION,
            _clean_batch_id UUID NOT NULL REFERENCES clean.clean_batch(clean_batch_id),
            _source VARCHAR(32) NOT NULL,
            _available_at TIMESTAMPTZ NOT NULL,
            _quality_status VARCHAR(16) NOT NULL,
            _mapping_version VARCHAR(32) NOT NULL,
            _normalization_version VARCHAR(32) NOT NULL,
            _quality_rule_version VARCHAR(32) NOT NULL,
            _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            _updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY(security_code, trade_date)
        )
    ''')
    op.execute("CREATE INDEX ix_clean_limit_price_date_code ON clean.stock_limit_price(trade_date, security_code)")

    for item_code in (
        "stock_adj_factor",
        "stock_daily_basic",
        "stock_suspend",
        "stock_limit_price",
    ):
        _create_task_definition(stage="clean", item_code=item_code)
        _create_task_definition(stage="quality", item_code=item_code)


def downgrade() -> None:
    op.execute("DELETE FROM ops.task_definition WHERE task_code IN ('clean:stock_adj_factor','quality:stock_adj_factor','clean:stock_daily_basic','quality:stock_daily_basic','clean:stock_suspend','quality:stock_suspend','clean:stock_limit_price','quality:stock_limit_price')")
    op.execute("DROP TABLE IF EXISTS clean.stock_limit_price")
    op.execute("DROP TABLE IF EXISTS clean.stock_suspend_event")
    op.execute("DROP TABLE IF EXISTS clean.stock_daily_basic")
    op.execute("DROP TABLE IF EXISTS clean.stock_adj_factor_history")
    op.execute("DROP TABLE IF EXISTS clean.stock_adj_factor")
