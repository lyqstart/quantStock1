"""enable offset pagination for stk_limit

Revision ID: 0006_stk_limit_paging
Revises: 0005_core_daily_items
Create Date: 2026-07-27
"""
from alembic import op

revision = "0006_stk_limit_paging"
down_revision = "0005_core_daily_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE meta.source_binding
        SET config = COALESCE(config, '{}'::jsonb) || jsonb_build_object(
            'pagination_mode', 'offset',
            'page_size', 5800
        )
        WHERE binding_code = 'tushare:stock_limit_price'
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE meta.source_binding
        SET config = COALESCE(config, '{}'::jsonb) - 'pagination_mode' - 'page_size'
        WHERE binding_code = 'tushare:stock_limit_price'
    """)
