from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable


class LocalRateLimiter:
    """Single-process limiter for the first-stage single Worker deployment."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._clock = clock
        self._sleeper = sleeper
        self._lock = threading.Lock()
        self._windows: dict[str, deque[float]] = {}

    def acquire(self, *, key: str, limit_per_minute: int | None) -> float:
        if limit_per_minute is None or limit_per_minute <= 0:
            return 0.0

        total_wait = 0.0
        while True:
            with self._lock:
                now = self._clock()
                window = self._windows.setdefault(key, deque())
                cutoff = now - 60.0
                while window and window[0] <= cutoff:
                    window.popleft()
                if len(window) < limit_per_minute:
                    window.append(now)
                    return total_wait
                wait_for = max(0.0, 60.0 - (now - window[0]))
            if wait_for > 0:
                self._sleeper(wait_for)
                total_wait += wait_for
