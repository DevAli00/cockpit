from __future__ import annotations

import time
from collections import OrderedDict, deque
from collections.abc import Callable


class SlidingWindowLimiter:
    """In-process sliding-window limiter. Bounded: the oldest keys are evicted first.

    Single-process only, which matches this app (one uvicorn worker, one owner).
    """

    def __init__(
        self, limit: int, window_s: float, clock: Callable[[], float] = time.monotonic,
        max_keys: int = 10_000,
    ) -> None:
        self._limit, self._window, self._clock, self._max = limit, window_s, clock, max_keys
        self._hits: OrderedDict[str, deque[float]] = OrderedDict()

    def hit(self, key: str) -> bool:
        """Record an attempt; False when the key is over its limit."""
        now = self._clock()
        q = self._hits.pop(key, None) or deque()
        while q and now - q[0] >= self._window:
            q.popleft()
        allowed = len(q) < self._limit
        if allowed:
            q.append(now)
        self._hits[key] = q
        while len(self._hits) > self._max:
            self._hits.popitem(last=False)
        return allowed

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)

    def size(self) -> int:
        return len(self._hits)
