from app.storage.models import Base


def test_p4_core_tables_exist_in_metadata() -> None:
    expected = {
        "ops.clean_run",
        "clean.clean_batch",
        "clean.clean_batch_input",
        "clean.clean_candidate_row",
        "clean.clean_skipped_row",
        "clean.trade_calendar",
        "clean.security_master",
        "clean.security_master_history",
        "clean.stock_daily",
        "clean.stock_adj_factor",
        "clean.stock_adj_factor_history",
        "clean.stock_daily_basic",
        "clean.stock_suspend_event",
        "clean.stock_limit_price",
        "quality.quality_run",
        "quality.quality_issue",
        "quality.data_gap",
        "quality.issue_task_link",
    }
    assert expected.issubset(set(Base.metadata.tables))
