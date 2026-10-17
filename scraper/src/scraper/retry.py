import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from scraper.errors import RateLimitedError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 5
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0

    def delay_after(self, failed_attempt: int, error: BaseException) -> float:
        if isinstance(error, RateLimitedError) and error.retry_after_seconds is not None:
            return error.retry_after_seconds
        return min(self.base_delay_seconds * 2 ** (failed_attempt - 1), self.max_delay_seconds)


RetryCallback = Callable[[int, BaseException, float], None]


def parse_retry_after(value: str | None) -> float | None:
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def with_retry[T](
    action: Callable[[], T],
    policy: RetryPolicy,
    *,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    sleep: Callable[[float], None] = time.sleep,
    on_retry: RetryCallback | None = None,
    description: str = "operation",
) -> T:
    """Run `action`, retrying with exponential backoff (1 s, 2 s, 4 s...) up to a limit.

    A RateLimitedError that carries Retry-After waits exactly as long as the server asked.
    After the last attempt the error propagates to the caller.
    """
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return action()
        except retry_on as error:
            if attempt == policy.max_attempts:
                logger.error("%s failed after %d attempts: %s", description, attempt, error)
                raise
            delay = policy.delay_after(attempt, error)
            logger.warning(
                "%s failed (attempt %d/%d): %s; retrying in %.1f s",
                description,
                attempt,
                policy.max_attempts,
                error,
                delay,
            )
            if on_retry is not None:
                on_retry(attempt, error, delay)
            sleep(delay)
    raise AssertionError("unreachable")
