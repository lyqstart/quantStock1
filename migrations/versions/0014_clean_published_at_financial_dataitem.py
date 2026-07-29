"""CLEAN published_at + financial tables + DataItem metadata

Revision ID: 0014_clean_published_at_financial_dataitem
Revises: 0013_lineage_and_snapshot
Create Date: 2026-07-29

Implements:
- DD-CORE-006: published_at separation on all CLEAN typed tables.
- DD-CORE-008: clean.financial_income and clean.financial_indicator multi-version tables
  with partial unique index on is_current=true.
- DD-CORE-001: meta.data_item.quality_policy_ref column + seed metadata for 10 DataItems.
"""
import uuid

from alembic import op

revision = "0014_clean_published_at_financial_dataitem"
down_revision = "0013_lineage_and_snapshot"
branch_labels = None
depends_on = None

NS = uuid.UUID("f49c0ed2-6b6d-4a65-9e8d-03de74809391")


def uid(value: str) -> uuid.UUID:
    return uuid.uuid5(NS, value)


# All CLEAN typed tables that carry the _published_at governance column (DD-CORE-006).
CLEAN_TABLES_WITH_PUBLISHED_AT = [
    "trade_calendar",
    "security_master",
    "security_master_history",
    "stock_daily",
    "stock_adj_factor",
    "stock_adj_factor_history",
    "stock_daily_basic",
    "stock_suspend_event",
    "stock_limit_price",
    "stock_minute",
]


def upgrade() -> None:
    # ---- DD-CORE-006: _published_at TIMESTAMPTZ on all CLEAN typed tables ----
    for table in CLEAN_TABLES_WITH_PUBLISHED_AT:
        op.execute(
            f"ALTER TABLE clean.{table} "
            f"ADD COLUMN IF NOT EXISTS _published_at TIMESTAMPTZ NOT NULL DEFAULT now()"
        )

    # ---- DD-CORE-008: clean.financial_income multi-version table ----
    op.execute('''
        CREATE TABLE IF NOT EXISTS clean.financial_income (
            financial_income_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            ts_code VARCHAR(16) NOT NULL,
            end_date DATE NOT NULL,
            ann_date DATE,
            f_ann_date DATE,
            report_type VARCHAR(8),
            update_flag VARCHAR(8),
            revision_version INT NOT NULL DEFAULT 1,
            is_current BOOLEAN NOT NULL DEFAULT true,
            valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
            valid_to TIMESTAMPTZ,
            -- core business fields (mapped from raw.tushare_income)
            basic_eps DOUBLE PRECISION,
            diluted_eps DOUBLE PRECISION,
            total_revenue DOUBLE PRECISION,
            revenue DOUBLE PRECISION,
            oper_cost DOUBLE PRECISION,
            total_profit DOUBLE PRECISION,
            income_tax DOUBLE PRECISION,
            n_income DOUBLE PRECISION,
            n_income_attr_p DOUBLE PRECISION,
            operate_profit DOUBLE PRECISION,
            total_cogs DOUBLE PRECISION,
            sell_exp DOUBLE PRECISION,
            admin_exp DOUBLE PRECISION,
            fin_exp DOUBLE PRECISION,
            rd_exp DOUBLE PRECISION,
            ebit DOUBLE PRECISION,
            ebitda DOUBLE PRECISION,
            -- governance columns (CLEAN convention: _ prefix)
            _clean_batch_id UUID NOT NULL REFERENCES clean.clean_batch(clean_batch_id),
            _source VARCHAR(32) NOT NULL,
            _available_at TIMESTAMPTZ NOT NULL,
            _quality_status VARCHAR(16) NOT NULL,
            _mapping_version VARCHAR(32) NOT NULL,
            _normalization_version VARCHAR(32) NOT NULL,
            _quality_rule_version VARCHAR(32) NOT NULL,
            _published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            _updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    ''')
    # Partial unique index: only one is_current=true row per (ts_code, end_date, report_type)
    op.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS uq_financial_income_current
            ON clean.financial_income (ts_code, end_date, report_type)
            WHERE is_current = true
    ''')
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_financial_income_tscode_enddate "
        "ON clean.financial_income (ts_code, end_date DESC)"
    )

    # ---- DD-CORE-008: clean.financial_indicator multi-version table ----
    op.execute('''
        CREATE TABLE IF NOT EXISTS clean.financial_indicator (
            financial_indicator_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            ts_code VARCHAR(16) NOT NULL,
            end_date DATE NOT NULL,
            ann_date DATE,
            update_flag VARCHAR(8),
            revision_version INT NOT NULL DEFAULT 1,
            is_current BOOLEAN NOT NULL DEFAULT true,
            valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
            valid_to TIMESTAMPTZ,
            -- core indicator fields (mapped from raw.tushare_fina_indicator)
            eps DOUBLE PRECISION,
            dt_eps DOUBLE PRECISION,
            total_revenue_ps DOUBLE PRECISION,
            revenue_ps DOUBLE PRECISION,
            bps DOUBLE PRECISION,
            roe DOUBLE PRECISION,
            roe_dt DOUBLE PRECISION,
            roa DOUBLE PRECISION,
            npta DOUBLE PRECISION,
            grossprofit_margin DOUBLE PRECISION,
            netprofit_margin DOUBLE PRECISION,
            current_ratio DOUBLE PRECISION,
            quick_ratio DOUBLE PRECISION,
            debt_to_assets DOUBLE PRECISION,
            ocfps DOUBLE PRECISION,
            -- governance columns
            _clean_batch_id UUID NOT NULL REFERENCES clean.clean_batch(clean_batch_id),
            _source VARCHAR(32) NOT NULL,
            _available_at TIMESTAMPTZ NOT NULL,
            _quality_status VARCHAR(16) NOT NULL,
            _mapping_version VARCHAR(32) NOT NULL,
            _normalization_version VARCHAR(32) NOT NULL,
            _quality_rule_version VARCHAR(32) NOT NULL,
            _published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            _created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            _updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    ''')
    op.execute('''
        CREATE UNIQUE INDEX IF NOT EXISTS uq_financial_indicator_current
            ON clean.financial_indicator (ts_code, end_date)
            WHERE is_current = true
    ''')
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_financial_indicator_tscode_enddate "
        "ON clean.financial_indicator (ts_code, end_date DESC)"
    )

    # ---- DD-CORE-001: meta.data_item.quality_policy_ref column ----
    op.execute(
        "ALTER TABLE meta.data_item "
        "ADD COLUMN IF NOT EXISTS quality_policy_ref VARCHAR(64)"
    )

    # ---- DD-CORE-001: seed metadata for 10 DataItems ----
    # All values come from DD-CORE-001 table and TASK-WI-0001-002 context block.
    dataitem_seeds = [
        # (code, business_time_field, update_mode, frequency, history_start, retention_class, quality_policy_ref)
        ("trade_calendar", "cal_date", "full_refresh", "daily", None, "permanent", "basic"),
        ("stock_basic", "list_date", "full_refresh", "on_change", None, "permanent", "basic"),
        ("stock_daily", "trade_date", "incremental", "daily", "1991-01-01", "permanent", "standard"),
        ("stock_adj_factor", "trade_date", "incremental", "daily", "1991-01-01", "permanent", "standard"),
        ("stock_daily_basic", "trade_date", "incremental", "daily", "1991-01-01", "permanent", "standard"),
        ("stock_suspend", "trade_date", "event_driven", "irregular", None, "permanent", "standard"),
        ("stock_limit_price", "trade_date", "incremental", "daily", None, "permanent", "standard"),
        ("stock_minute", "trade_time", "incremental", "1min", None, "hot_2y_cold_archive", "minute"),
        ("financial_income", "end_date", "incremental_revs", "quarterly", None, "permanent", "financial"),
        ("financial_indicator", "end_date", "incremental_revs", "quarterly", None, "permanent", "financial"),
    ]
    for (
        code,
        business_time_field,
        update_mode,
        frequency,
        history_start,
        retention_class,
        quality_policy_ref,
    ) in dataitem_seeds:
        history_start_sql = "NULL" if history_start is None else f"'{history_start}'::date"
        op.execute(
            f"""
            UPDATE meta.data_item SET
                business_time_field = '{business_time_field}',
                update_mode = '{update_mode}',
                frequency = '{frequency}',
                history_start = {history_start_sql},
                retention_class = '{retention_class}',
                quality_policy_ref = '{quality_policy_ref}',
                updated_at = now()
            WHERE code = '{code}'
            """
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS clean.financial_indicator")
    op.execute("DROP TABLE IF EXISTS clean.financial_income")
    for table in reversed(CLEAN_TABLES_WITH_PUBLISHED_AT):
        op.execute(f"ALTER TABLE clean.{table} DROP COLUMN IF EXISTS _published_at")
    op.execute("ALTER TABLE meta.data_item DROP COLUMN IF EXISTS quality_policy_ref")
