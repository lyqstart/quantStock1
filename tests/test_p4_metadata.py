from app.storage.models import Base


def test_p4_core_tables_exist_in_metadata() -> None:
    expected = {
        "ops.clean_run",
        "clean.clean_batch",
        "clean.clean_batch_input",
        "clean.clean_candidate_row",
        "clean.trade_calendar",
        "clean.security_master",
        "clean.security_master_history",
        "clean.stock_daily",
        "quality.quality_run",
        "quality.quality_issue",
        "quality.data_gap",
        "quality.issue_task_link",
    }
    assert expected.issubset(set(Base.metadata.tables))
