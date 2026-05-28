from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class SlidingWindowRateLimiter:
    limit: int
    window_seconds: int = 60

    def __post_init__(self) -> None:
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self._buckets[key]

        while bucket and (now - bucket[0]) >= self.window_seconds:
            bucket.popleft()

        if len(bucket) >= self.limit:
            return False

        bucket.append(now)
        return True
