import time
from collections.abc import Callable


class Throttle:
    """Keeps at least `min_interval_seconds` between consecutive requests to the shop.

    This is politeness towards the server, not a way of waiting for the page: page state is
    always awaited with WebDriverWait conditions.
    """

    def __init__(
        self,
        min_interval_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.min_interval_seconds = min_interval_seconds
        self._clock = clock
        self._sleep = sleep
        self._last_request_at: float | None = None
        self.request_count = 0
        self.waited_seconds = 0.0

    def wait(self) -> None:
        if self._last_request_at is not None:
            remaining = self._last_request_at + self.min_interval_seconds - self._clock()
            if remaining > 0:
                self._sleep(remaining)
                self.waited_seconds += remaining
        self._last_request_at = self._clock()
        self.request_count += 1
