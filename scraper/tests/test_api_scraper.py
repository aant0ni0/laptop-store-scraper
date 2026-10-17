import pytest

from scraper.api_scraper import ApiSource
from scraper.errors import ProductNotFoundError
from scraper.retry import RetryPolicy
from scraper.throttle import Throttle


class FakeResponse:
    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeHttp:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.headers = {}

    def get(self, url, params=None, timeout=None):
        self.requests.append((url, params))
        return self.responses.pop(0)

    def close(self):
        pass


def make_source(responses):
    http = FakeHttp(responses)
    sleeps = []
    source = ApiSource(
        "http://shop",
        Throttle(0, sleep=lambda _: None),
        RetryPolicy(max_attempts=3),
        timeout_seconds=5,
        http=http,
        sleep=sleeps.append,
    )
    return source, http, sleeps


def chunk(items, has_more, page=1):
    return {"page": page, "page_count": 8, "total": 3, "has_more": has_more, "items": items}


def test_catalog_page_follows_has_more_until_the_page_is_exhausted():
    source, http, _ = make_source(
        [
            FakeResponse(200, chunk([{"id": 1}, {"id": 2}], has_more=True)),
            FakeResponse(200, chunk([{"id": 3}], has_more=False)),
        ]
    )
    rows = source.catalog_page(1)
    assert [row["id"] for row in rows] == [1, 2, 3]
    assert rows[0]["source_page"] == 1
    assert http.requests[1][1]["offset"] == 2
    assert source.page_count() == 8


def test_http_429_waits_for_retry_after_and_retries():
    source, _, sleeps = make_source(
        [
            FakeResponse(429, {"error": "too many requests"}, {"Retry-After": "6"}),
            FakeResponse(200, chunk([{"id": 1}], has_more=False)),
        ]
    )
    assert len(source.catalog_page(1)) == 1
    assert sleeps == [6.0]
    assert source.stats() == {"retries": 1, "api_responses": 2, "http_429_responses": 1}


def test_server_errors_are_retried_with_exponential_backoff():
    source, _, sleeps = make_source(
        [FakeResponse(503), FakeResponse(502), FakeResponse(200, {"id": 1, "name": "X"})]
    )
    assert source.get_json("/api/products/1")["name"] == "X"
    assert sleeps == [1.0, 2.0]


def test_product_merges_details_and_specs():
    source, http, _ = make_source(
        [FakeResponse(200, {"id": 5, "name": "X"}), FakeResponse(200, {"cpu": "i5", "ram_gb": 8})]
    )
    assert source.product(5) == {"id": 5, "name": "X", "cpu": "i5", "ram_gb": 8}
    assert [url for url, _ in http.requests] == [
        "http://shop/api/products/5",
        "http://shop/api/products/5/specs",
    ]


def test_missing_product_is_not_retried():
    source, http, sleeps = make_source([FakeResponse(404, {"error": "product not found"})])
    with pytest.raises(ProductNotFoundError):
        source.product(999)
    assert len(http.requests) == 1
    assert sleeps == []
