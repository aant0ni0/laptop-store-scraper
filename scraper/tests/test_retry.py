import pytest

from scraper.errors import PageLoadError, ProductNotFoundError, RateLimitedError
from scraper.retry import RetryPolicy, with_retry
from scraper.throttle import Throttle

POLICY = RetryPolicy(max_attempts=4, base_delay_seconds=1, max_delay_seconds=30)


def failing(times: int, error: Exception):
    calls = {"count": 0}

    def action():
        calls["count"] += 1
        if calls["count"] <= times:
            raise error
        return "ok"

    return action, calls


def test_retry_waits_exponentially_longer_between_attempts():
    action, calls = failing(3, PageLoadError("boom"))
    delays = []
    assert with_retry(action, POLICY, sleep=delays.append) == "ok"
    assert delays == [1, 2, 4]
    assert calls["count"] == 4


def test_retry_delay_is_capped():
    policy = RetryPolicy(max_attempts=10, base_delay_seconds=1, max_delay_seconds=5)
    assert [policy.delay_after(attempt, PageLoadError()) for attempt in range(1, 6)] == [
        1,
        2,
        4,
        5,
        5,
    ]


def test_retry_respects_retry_after_from_the_server():
    action, _ = failing(2, RateLimitedError(retry_after_seconds=7))
    delays = []
    with_retry(action, POLICY, sleep=delays.append)
    assert delays == [7, 7]


def test_rate_limit_without_retry_after_falls_back_to_backoff():
    action, _ = failing(2, RateLimitedError())
    delays = []
    with_retry(action, POLICY, sleep=delays.append)
    assert delays == [1, 2]


def test_retry_gives_up_after_the_attempt_limit():
    action, calls = failing(10, PageLoadError("still broken"))
    delays = []
    with pytest.raises(PageLoadError):
        with_retry(action, POLICY, sleep=delays.append)
    assert calls["count"] == POLICY.max_attempts
    assert delays == [1, 2, 4]


def test_retry_does_not_retry_errors_outside_retry_on():
    action, calls = failing(1, ProductNotFoundError("404"))
    with pytest.raises(ProductNotFoundError):
        with_retry(action, POLICY, retry_on=(PageLoadError,), sleep=lambda _: None)
    assert calls["count"] == 1


def test_successful_action_runs_once_without_sleeping():
    action, calls = failing(0, PageLoadError())
    delays = []
    with_retry(action, POLICY, sleep=delays.append)
    assert calls["count"] == 1
    assert delays == []


def test_retry_reports_every_retry_to_the_callback():
    action, _ = failing(2, PageLoadError("boom"))
    retries = []
    with_retry(
        action,
        POLICY,
        sleep=lambda _: None,
        on_retry=lambda attempt, error, delay: retries.append((attempt, delay)),
    )
    assert retries == [(1, 1), (2, 2)]


class FakeClock:
    def __init__(self):
        self.now = 100.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def test_throttle_keeps_minimum_interval_between_requests():
    clock = FakeClock()
    throttle = Throttle(0.5, clock=clock, sleep=clock.sleep)
    throttle.wait()
    clock.now += 0.2
    throttle.wait()
    clock.now += 0.7
    throttle.wait()
    assert clock.sleeps == [pytest.approx(0.3)]
    assert throttle.request_count == 3
    assert throttle.waited_seconds == pytest.approx(0.3)
