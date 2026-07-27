"""core daily item runtime support

Revision ID: 0005_core_daily_items
Revises: 0004_stock_daily_runtime
Create Date: 2026-07-27
"""
import uuid

from alembic import op

revision = "0005_core_daily_items"
down_revision = "0004_stock_daily_runtime"
branch_labels = None
depends_on = None

NS = uuid.UUID("f49c0ed2-6b6d-4a65-9e8d-03de74809391")


def uid(value: str) -> uuid.UUID:
    return uuid.uuid5(NS, value)


def _insert_task_definition(
    *, item_code: str, task_code: str, priority: int, available_after: str, delay_days: int = 0
) -> None:
    op.execute(f"""
        INSERT INTO ops.task_definition (
            task_definition_id, task_code, data_item_id, source_binding_id, task_type, update_mode,
            schedule_rule, availability_rule, split_policy_version, retry_policy_version,
            priority, enabled, definition_version
        ) VALUES (
            '{uid(f"taskdef:{task_code}")}',
            '{task_code}',
            '{uid(f"item:{item_code}")}',
            '{uid(f"binding:tushare:{item_code}")}',
            'collect', 'trading_day',
            '{{"scan":"periodic","timezone":"Asia/Shanghai"}}'::jsonb,
            '{{"available_after":"{available_after}","delay_days":"{delay_days}","timezone":"Asia/Shanghai"}}'::jsonb,
            'v1', 'v1', {priority}, true, 'v1'
        )
    """)


def upgrade() -> None:
    for constraint, table in (
        ("uq_tushare_adj_factor_content", "tushare_adj_factor"),
        ("uq_tushare_daily_basic_content", "tushare_daily_basic"),
        ("uq_tushare_suspend_d_content", "tushare_suspend_d"),
        ("uq_tushare_stk_limit_content", "tushare_stk_limit"),
    ):
        op.create_unique_constraint(
            constraint,
            table,
            ["_source", "_source_api", "_content_hash"],
            schema="raw",
        )

    op.execute("""
        UPDATE meta.source_binding
        SET required_points = 2000,
            max_rows_per_request = 6000,
            split_dimension = 'trade_date',
            update_time_rule = jsonb_build_object(
                'timezone', 'Asia/Shanghai',
                'source_update_window', '09:15-09:20',
                'available_after', '09:30'
            ),
            config = COALESCE(config, '{}'::jsonb) || jsonb_build_object('retry_max_attempts', 3)
        WHERE binding_code = 'tushare:stock_adj_factor'
    """)
    op.execute("""
        UPDATE meta.source_binding
        SET required_points = 2000,
            max_rows_per_request = 6000,
            split_dimension = 'trade_date',
            update_time_rule = jsonb_build_object(
                'timezone', 'Asia/Shanghai',
                'source_update_window', '15:00-17:00',
                'available_after', '17:10'
            ),
            config = COALESCE(config, '{}'::jsonb) || jsonb_build_object('retry_max_attempts', 3)
        WHERE binding_code = 'tushare:stock_daily_basic'
    """)
    op.execute("""
        UPDATE meta.source_binding
        SET split_dimension = 'trade_date',
            update_time_rule = jsonb_build_object(
                'timezone', 'Asia/Shanghai',
                'source_update', 'irregular',
                'collection_policy', 'next_day_review'
            ),
            config = COALESCE(config, '{}'::jsonb) || jsonb_build_object('retry_max_attempts', 3)
        WHERE binding_code = 'tushare:stock_suspend'
    """)
    op.execute("""
        UPDATE meta.source_binding
        SET required_points = 2000,
            max_rows_per_request = 5800,
            split_dimension = 'trade_date',
            update_time_rule = jsonb_build_object(
                'timezone', 'Asia/Shanghai',
                'source_update_approx', '08:40',
                'available_after', '08:50'
            ),
            config = COALESCE(config, '{}'::jsonb) || jsonb_build_object('retry_max_attempts', 3)
        WHERE binding_code = 'tushare:stock_limit_price'
    """)

    _insert_task_definition(
        item_code="stock_limit_price",
        task_code="stock_limit_price_incremental",
        priority=1,
        available_after="08:50",
    )
    _insert_task_definition(
        item_code="stock_adj_factor",
        task_code="stock_adj_factor_incremental",
        priority=2,
        available_after="09:30",
    )
    _insert_task_definition(
        item_code="stock_daily_basic",
        task_code="stock_daily_basic_incremental",
        priority=3,
        available_after="17:10",
    )
    _insert_task_definition(
        item_code="stock_suspend",
        task_code="stock_suspend_incremental",
        priority=4,
        available_after="09:00",
        delay_days=1,
    )


def downgrade() -> None:
    op.execute("""
        DELETE FROM ops.task_definition
        WHERE task_code IN (
            'stock_adj_factor_incremental',
            'stock_daily_basic_incremental',
            'stock_suspend_incremental',
            'stock_limit_price_incremental'
        )
    """)
    for code in ("stock_adj_factor", "stock_daily_basic", "stock_suspend", "stock_limit_price"):
        op.execute(f"""
            UPDATE meta.source_binding
            SET required_points = NULL,
                split_dimension = NULL,
                update_time_rule = '{{}}'::jsonb,
                config = '{{}}'::jsonb
            WHERE binding_code = 'tushare:{code}'
        """)
    op.execute("UPDATE meta.source_binding SET max_rows_per_request = NULL WHERE binding_code = 'tushare:stock_adj_factor'")
    op.execute("UPDATE meta.source_binding SET max_rows_per_request = 6000 WHERE binding_code = 'tushare:stock_daily_basic'")
    op.execute("UPDATE meta.source_binding SET max_rows_per_request = NULL WHERE binding_code = 'tushare:stock_suspend'")
    op.execute("UPDATE meta.source_binding SET max_rows_per_request = 5800 WHERE binding_code = 'tushare:stock_limit_price'")

    for constraint, table in (
        ("uq_tushare_stk_limit_content", "tushare_stk_limit"),
        ("uq_tushare_suspend_d_content", "tushare_suspend_d"),
        ("uq_tushare_daily_basic_content", "tushare_daily_basic"),
        ("uq_tushare_adj_factor_content", "tushare_adj_factor"),
    ):
        op.drop_constraint(constraint, table, schema="raw", type_="unique")
