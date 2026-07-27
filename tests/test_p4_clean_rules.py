from datetime import date

import pytest

from app.governance.executor import _date8, _int_exact


def test_p4_date_and_daily_units_are_deterministic() -> None:
    assert _date8("20260727") == date(2026, 7, 27)
    assert _date8("") is None
    assert _int_exact(12.34, 100) == 1234
    assert _int_exact(None, 100) is None


def test_p4_volume_conversion_rejects_fractional_share() -> None:
    with pytest.raises(ValueError):
        _int_exact(1.2345, 100)
