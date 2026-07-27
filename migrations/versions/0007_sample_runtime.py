"""minute and financial sample runtime support

Revision ID: 0007_sample_runtime
Revises: 0006_stk_limit_paging
Create Date: 2026-07-27
"""
from alembic import op

revision = "0007_sample_runtime"
down_revision = "0006_stk_limit_paging"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for constraint, table in (
        ("uq_tushare_stk_mins_content", "tushare_stk_mins"),
        ("uq_tushare_income_content", "tushare_income"),
        ("uq_tushare_fina_indicator_content", "tushare_fina_indicator"),
    ):
        op.create_unique_constraint(constraint, table, ["_source", "_source_api", "_content_hash"], schema="raw")
    op.execute("""
        UPDATE meta.source_binding
        SET entitlement_code='stk_mins', max_rows_per_request=8000,
            split_dimension='ts_code+frequency+time_window',
            update_time_rule=jsonb_build_object('timezone','Asia/Shanghai','mode','historical_minute','sample_validation',true),
            config=COALESCE(config,'{}'::jsonb)||jsonb_build_object('retry_max_attempts',3,'sample_only',true)
        WHERE binding_code='tushare:stock_minute'
    """)
    op.execute("""
        UPDATE meta.source_binding
        SET required_points=2000, split_dimension='ts_code+report_period',
            update_time_rule=jsonb_build_object('timezone','Asia/Shanghai','source_update','realtime_with_disclosure','sample_validation',true),
            config=COALESCE(config,'{}'::jsonb)||jsonb_build_object('retry_max_attempts',3,'sample_only',true)
        WHERE binding_code='tushare:financial_income'
    """)
    op.execute("""
        UPDATE meta.source_binding
        SET required_points=2000, max_rows_per_request=100, split_dimension='ts_code+report_period',
            update_time_rule=jsonb_build_object('timezone','Asia/Shanghai','source_update','with_financial_report','sample_validation',true),
            config=COALESCE(config,'{}'::jsonb)||jsonb_build_object('retry_max_attempts',3,'sample_only',true)
        WHERE binding_code='tushare:financial_indicator'
    """)


def downgrade() -> None:
    for code in ("stock_minute", "financial_income", "financial_indicator"):
        op.execute(f"UPDATE meta.source_binding SET required_points=NULL, entitlement_code=NULL, split_dimension=NULL, update_time_rule='{{}}'::jsonb, config='{{}}'::jsonb WHERE binding_code='tushare:{code}'")
    for constraint, table in (
        ("uq_tushare_fina_indicator_content", "tushare_fina_indicator"),
        ("uq_tushare_income_content", "tushare_income"),
        ("uq_tushare_stk_mins_content", "tushare_stk_mins"),
    ):
        op.drop_constraint(constraint, table, schema="raw", type_="unique")
