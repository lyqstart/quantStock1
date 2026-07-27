from app.datasource.errors import classify_provider_exception


def test_rate_limit_is_retryable() -> None:
    failure = classify_provider_exception(RuntimeError("每分钟访问频次超过限制"))
    assert failure.error_type == "RATE_LIMITED"
    assert failure.retryable is True


def test_invalid_request_is_not_retryable() -> None:
    failure = classify_provider_exception(RuntimeError("参数错误：start_date格式错误"))
    assert failure.error_type == "INVALID_REQUEST"
    assert failure.retryable is False
