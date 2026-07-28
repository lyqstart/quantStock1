from datetime import date

from app.storage.minute_metrics import (
    _count_clean_rows,
    _count_raw_rows,
)


class _ScalarResult:
    def __init__(self, value: int):
        self.value = value

    def scalar_one(self) -> int:
        return self.value


class _RecordingSession:
    def __init__(self, value: int = 7):
        self.value = value
        self.calls: list[tuple[str, dict[str, object] | None]] = []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        return _ScalarResult(self.value)


def test_raw_count_without_date_has_no_nullable_parameter() -> None:
    session = _RecordingSession()

    assert _count_raw_rows(session, None) == 7

    sql, params = session.calls[0]
    assert ":trade_date" not in sql
    assert params is None


def test_raw_count_with_date_uses_explicit_date_contract() -> None:
    session = _RecordingSession()
    trade_date = date(2026, 7, 24)

    assert _count_raw_rows(session, trade_date) == 7

    sql, params = session.calls[0]
    assert "IS NULL" not in sql
    assert "CAST(:trade_date AS date)" in sql
    assert params == {"trade_date": trade_date}


def test_clean_count_without_date_has_no_nullable_parameter() -> None:
    session = _RecordingSession()

    assert _count_clean_rows(session, None) == 7

    sql, params = session.calls[0]
    assert ":trade_date" not in sql
    assert params is None


def test_clean_count_with_date_uses_explicit_date_contract() -> None:
    session = _RecordingSession()
    trade_date = date(2026, 7, 24)

    assert _count_clean_rows(session, trade_date) == 7

    sql, params = session.calls[0]
    assert "IS NULL" not in sql
    assert "CAST(:trade_date AS date)" in sql
    assert params == {"trade_date": trade_date}
