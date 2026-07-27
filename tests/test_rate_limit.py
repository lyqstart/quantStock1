from app.collect.rate_limit import LocalRateLimiter


def test_rate_limiter_waits_when_window_is_full() -> None:
    state = {"now": 0.0}
    sleeps: list[float] = []

    def clock() -> float:
        return state["now"]

    def sleeper(seconds: float) -> None:
        sleeps.append(seconds)
        state["now"] += seconds

    limiter = LocalRateLimiter(clock=clock, sleeper=sleeper)
    assert limiter.acquire(key="trade_cal", limit_per_minute=2) == 0
    state["now"] = 1
    assert limiter.acquire(key="trade_cal", limit_per_minute=2) == 0
    state["now"] = 2
    waited = limiter.acquire(key="trade_cal", limit_per_minute=2)
    assert waited == 58
    assert sleeps == [58]
