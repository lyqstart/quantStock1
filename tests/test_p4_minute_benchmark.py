from app.storage.minute_benchmark import (
    _normalize_explain_payload,
    _project_layer,
    _summarize_runs,
)


def test_projection_reports_per_row_and_daily_yearly_estimates() -> None:
    result = _project_layer(
        {
            "rows": 100,
            "table_bytes": 1000,
            "index_bytes": 500,
            "total_bytes": 1500,
        },
        rows_per_day=1000,
        trading_days=10,
    )
    assert result["table_bytes_per_row"] == 10.0
    assert result["projected_table_bytes_per_day"] == 10000
    assert result["projected_total_bytes_per_year"] == 150000


def test_projection_handles_empty_layer_without_division() -> None:
    result = _project_layer(
        {"rows": 0, "table_bytes": 0, "index_bytes": 0, "total_bytes": 0},
        rows_per_day=1000,
        trading_days=10,
    )
    assert result["total_bytes_per_row"] is None
    assert result["projected_total_bytes_per_day"] is None


def test_explain_payload_accepts_postgresql_json_list() -> None:
    payload = [{"Plan": {"Node Type": "Index Scan"}, "Execution Time": 1.25}]
    assert _normalize_explain_payload(payload)["Plan"]["Node Type"] == "Index Scan"


def test_run_summary_uses_median_and_preserves_last_run() -> None:
    runs = [
        {"execution_time_ms": 3.0, "planning_time_ms": 0.3},
        {"execution_time_ms": 1.0, "planning_time_ms": 0.1},
        {"execution_time_ms": 2.0, "planning_time_ms": 0.2},
    ]
    result = _summarize_runs(runs)
    assert result["execution_time_ms"] == {
        "min": 1.0,
        "median": 2.0,
        "max": 3.0,
    }
    assert result["planning_time_ms"]["median"] == 0.2
    assert result["last_run"] is runs[-1]
