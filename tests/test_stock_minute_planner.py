from datetime import datetime
from zoneinfo import ZoneInfo
from app.collect.planners.stock_minute import plan_stock_minute_slice

def test_stock_minute_slice_uses_stock_frequency_and_time_window() -> None:
    tz=ZoneInfo('Asia/Shanghai')
    plan=plan_stock_minute_slice(ts_code='000001.SZ',frequency='1min',start_time=datetime(2026,7,24,9,0,tzinfo=tz),end_time=datetime(2026,7,24,15,30,tzinfo=tz),source_binding_code='tushare:stock_minute',mapping_version='v1')
    assert plan.partition_key=='000001.SZ:1min:20260724T090000:20260724T153000'
    assert plan.request_params['freq']=='1min'
    assert len(plan.request_hash)==64
