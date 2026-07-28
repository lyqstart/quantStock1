from app.storage.minute_metrics import _hypertable_size


class _Mappings:
    def __init__(self, row):
        self._row = row

    def one(self):
        return self._row


class _Result:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return _Mappings(self._row)


class _Session:
    def __init__(self):
        self.sql = ""
        self.params = None

    def execute(self, statement, params):
        self.sql = str(statement)
        self.params = params
        return _Result(
            {
                "table_bytes": 100,
                "index_bytes": 40,
                "toast_bytes": 10,
                "total_bytes": 150,
            }
        )


def test_hypertable_size_uses_timescale_chunk_aware_size_function() -> None:
    session = _Session()
    result = _hypertable_size(session, "clean.stock_minute")

    assert "hypertable_detailed_size" in session.sql
    assert session.params == {"relation": "clean.stock_minute"}
    assert result == {
        "table_bytes": 100,
        "index_bytes": 40,
        "toast_bytes": 10,
        "total_bytes": 150,
    }
