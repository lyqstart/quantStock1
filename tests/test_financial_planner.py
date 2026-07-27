from datetime import date
from app.collect.planners.financial import plan_financial_slice

def test_financial_slice_is_per_stock_and_report_range() -> None:
    plan=plan_financial_slice(ts_code='000001.SZ',start_date=date(2024,1,1),end_date=date(2026,7,27),api_name='income',source_binding_code='tushare:financial_income',mapping_version='v1')
    assert plan.partition_key=='000001.SZ:20240101:20260727'
    assert plan.request_params['ts_code']=='000001.SZ'
    assert len(plan.request_hash)==64
