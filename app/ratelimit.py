"""A token bucket per user: a burst of N questions, then one more every 60/N seconds."""
import threading
import time


class RateLimiter:
    def __init__(self, per_minute: int, clock=time.monotonic):
        self.capacity, self.refill = float(per_minute), per_minute / 60.0
        self.clock, self.lock = clock, threading.Lock()
        self.buckets: dict[str, tuple[float, float]] = {}  # user -> (tokens left, last time)

    def allow(self, key: str) -> tuple[bool, int]:
        """(allowed, seconds to wait if not)."""
        with self.lock:
            now = self.clock()
            tokens, last = self.buckets.get(key, (self.capacity, now))
            tokens = min(self.capacity, tokens + (now - last) * self.refill)
            if tokens < 1:
                self.buckets[key] = (tokens, now)
                return False, int((1 - tokens) / self.refill) + 1
            self.buckets[key] = (tokens - 1, now)
            return True, 0
