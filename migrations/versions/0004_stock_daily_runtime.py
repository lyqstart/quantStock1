"""stock basic and daily runtime support

Revision ID: 0004_stock_daily_runtime
Revises: 0003_trade_cal_runtime
Create Date: 2026-07-27
"""
import uuid

from alembic import op

revision = "0004_stock_daily_runtime"
down_revision = "0003_trade_cal_runtime"
branch_labels = None
depends_on = None

NS = uuid.UUID("f49c0ed2-6b6d-4a65-9e8d-03de74809391")


def uid(value: str) -> uuid.UUID:
    return uuid.uuid5(NS, value)


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_tushare_stock_basic_content",
        "tushare_stock_basic",
        ["_source", "_source_api", "_content_hash"],
        schema="raw",
    )
    op.create_unique_constraint(
        "uq_tushare_daily_content",
        "tushare_daily",
        ["_source", "_source_api", "_content_hash"],
        schema="raw",
    )

    op.execute("""
        UPDATE meta.source_binding
        SET required_points = 2000,
            max_rows_per_request = 6000,
            max_calls_per_minute = 50,
            effective_calls_per_minute = 40,
            split_dimension = 'list_status',
            config = COALESCE(config, '{}'::jsonb) || jsonb_build_object('retry_max_attempts', 3)
        WHERE binding_code = 'tushare:stock_basic'
    """)
    op.execute("""
        UPDATE meta.source_binding
        SET max_rows_per_request = 6000,
            max_calls_per_minute = 500,
            max_calls_per_day = 100000,
            effective_calls_per_minute = 180,
            split_dimension = 'trade_date',
            update_time_rule = jsonb_build_object(
                'timezone', 'Asia/Shanghai',
                'source_update_window', '15:00-16:00',
                'available_after', '16:10'
            ),
            config = COALESCE(config, '{}'::jsonb) || jsonb_build_object('retry_max_attempts', 3)
        WHERE binding_code = 'tushare:stock_daily'
    """)

    op.execute(f"""
        INSERT INTO ops.task_definition (
            task_definition_id, task_code, data_item_id, source_binding_id, task_type, update_mode,
            schedule_rule, availability_rule, split_policy_version, retry_policy_version, priority, enabled, definition_version
        ) VALUES (
            '{uid("taskdef:stock_daily_incremental")}',
            'stock_daily_incremental',
            '{uid("item:stock_daily")}',
            '{uid("binding:tushare:stock_daily")}',
            'collect',
            'trading_day',
            '{{"scan":"periodic","timezone":"Asia/Shanghai"}}'::jsonb,
            '{{"available_after":"16:10","timezone":"Asia/Shanghai"}}'::jsonb,
            'v1', 'v1', 0, true, 'v1'
        )
    """)



def downgrade() -> None:
    op.execute("DELETE FROM ops.task_definition WHERE task_code = 'stock_daily_incremental'")
    op.execute("""
        UPDATE meta.source_binding
        SET required_points = NULL,
            max_calls_per_minute = NULL,
            effective_calls_per_minute = NULL,
            split_dimension = NULL,
            config = '{}'::jsonb
        WHERE binding_code = 'tushare:stock_basic'
    """)
    op.execute("""
        UPDATE meta.source_binding
        SET max_calls_per_minute = NULL,
            max_calls_per_day = NULL,
            effective_calls_per_minute = NULL,
            split_dimension = NULL,
            update_time_rule = '{}'::jsonb,
            config = '{}'::jsonb
        WHERE binding_code = 'tushare:stock_daily'
    """)
    op.drop_constraint("uq_tushare_daily_content", "tushare_daily", schema="raw", type_="unique")
    op.drop_constraint("uq_tushare_stock_basic_content", "tushare_stock_basic", schema="raw", type_="unique")
