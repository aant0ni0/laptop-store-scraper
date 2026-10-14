import pytest

from shop.rate_limit import SlidingWindowRateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def limiter(clock):
    return SlidingWindowRateLimiter(clock=clock)


def acquire(limiter, client_id="client"):
    return limiter.try_acquire(client_id, max_requests=3, window_seconds=10)


def test_allows_requests_up_to_the_limit(limiter):
    assert [acquire(limiter) for _ in range(3)] == [None, None, None]


def test_rejects_request_over_the_limit_with_seconds_to_wait(limiter, clock):
    for _ in range(3):
        acquire(limiter)
        clock.now += 2

    assert acquire(limiter) == 4


def test_allows_again_once_oldest_request_leaves_the_window(limiter, clock):
    for _ in range(3):
        acquire(limiter)
    clock.now += 10

    assert acquire(limiter) is None


def test_rejected_requests_do_not_extend_the_wait(limiter, clock):
    for _ in range(3):
        acquire(limiter)
    for _ in range(5):
        acquire(limiter)
    clock.now += 10

    assert acquire(limiter) is None


def test_counts_each_client_separately(limiter):
    for _ in range(3):
        acquire(limiter, "first")

    assert acquire(limiter, "first") is not None
    assert acquire(limiter, "second") is None
