from app.storage.models import Base


def test_required_schemas_and_tables_exist_in_metadata() -> None:
    expected = {
        "meta.data_source", "meta.data_item", "meta.source_binding",
        "ops.task_definition", "ops.collect_task", "ops.collect_run", "ops.request_slice",
        "ops.slice_attempt", "ops.worker_registry", "ops.scheduler_state", "ops.data_watermark",
        "ops.task_checkpoint", "ops.rate_limit_state", "ops.circuit_breaker_state",
        "raw.raw_batch", "raw.tushare_trade_cal", "raw.tushare_stock_basic", "raw.tushare_daily",
        "raw.tushare_adj_factor", "raw.tushare_daily_basic", "raw.tushare_suspend_d",
        "raw.tushare_stk_limit", "raw.tushare_stk_mins", "raw.tushare_income",
        "raw.tushare_fina_indicator", "audit.audit_event",
    }
    assert expected.issubset(set(Base.metadata.tables))
