from app.collect.executor import RAW_INSERT_BATCH_SIZE, chunk_rows


def test_full_market_rows_are_split_into_safe_batches():
    rows = [{"i": i} for i in range(5522)]
    chunks = list(chunk_rows(rows))
    assert RAW_INSERT_BATCH_SIZE == 1000
    assert [len(chunk) for chunk in chunks] == [1000, 1000, 1000, 1000, 1000, 522]
    assert sum(map(len, chunks)) == 5522


def test_chunk_rows_rejects_invalid_size():
    try:
        list(chunk_rows([{}], size=0))
    except ValueError as exc:
        assert "positive" in str(exc)
    else:
        raise AssertionError("expected ValueError")
