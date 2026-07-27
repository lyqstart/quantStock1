from datetime import datetime
from zoneinfo import ZoneInfo

from app.collect.scheduler import _due_through_date


def test_suspend_review_is_delayed_one_day() -> None:
    now = datetime(2026, 7, 28, 10, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    assert _due_through_date(now, {"delay_days": 1}) .isoformat() == "2026-07-27"


def test_normal_daily_item_is_due_same_day() -> None:
    now = datetime(2026, 7, 27, 18, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    assert _due_through_date(now, {"delay_days": 0}).isoformat() == "2026-07-27"
