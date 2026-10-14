import math
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

RetryAfterSeconds = int


class SlidingWindowRateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._request_times_by_client: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def try_acquire(
        self, client_id: str, max_requests: int, window_seconds: float
    ) -> RetryAfterSeconds | None:
        with self._lock:
            now = self._clock()
            request_times = self._request_times_by_client[client_id]
            while request_times and request_times[0] <= now - window_seconds:
                request_times.popleft()

            if len(request_times) >= max_requests:
                seconds_until_oldest_expires = request_times[0] + window_seconds - now
                return max(1, math.ceil(seconds_until_oldest_expires))

            request_times.append(now)
            return None
