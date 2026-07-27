"""tushare trade calendar runtime support

Revision ID: 0003_trade_cal_runtime
Revises: 0002_seed_catalog
Create Date: 2026-07-27
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_trade_cal_runtime"
down_revision = "0002_seed_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE ops.data_watermark SET frequency = '' WHERE frequency IS NULL")
    op.alter_column("data_watermark", "frequency", schema="ops", existing_type=sa.String(length=16), nullable=False, server_default="")
    op.create_unique_constraint(
        "uq_tushare_trade_cal_content",
        "tushare_trade_cal",
        ["_source", "_source_api", "_content_hash"],
        schema="raw",
    )
    op.execute("""
        UPDATE meta.data_source
        SET credential_ref = 'env:QUANTSTOCK1_TUSHARE_TOKEN'
        WHERE source_code = 'tushare'
    """)
    op.execute("""
        UPDATE meta.source_binding
        SET required_points = 2000,
            max_calls_per_minute = 200,
            max_calls_per_day = 100000,
            split_dimension = 'date_range',
            config = COALESCE(config, '{}'::jsonb) || jsonb_build_object('retry_max_attempts', 3)
        WHERE binding_code = 'tushare:trade_calendar'
    """)


def downgrade() -> None:
    op.execute("UPDATE meta.data_source SET credential_ref = 'env:TUSHARE_TOKEN' WHERE source_code = 'tushare'")
    op.execute("""
        UPDATE meta.source_binding
        SET required_points = NULL,
            max_calls_per_minute = NULL,
            max_calls_per_day = NULL,
            split_dimension = NULL,
            config = '{}'::jsonb
        WHERE binding_code = 'tushare:trade_calendar'
    """)
    op.drop_constraint("uq_tushare_trade_cal_content", "tushare_trade_cal", schema="raw", type_="unique")
    op.alter_column("data_watermark", "frequency", schema="ops", existing_type=sa.String(length=16), nullable=True, server_default=None)
