"""Read the JSON API the shop's own JavaScript calls, without a browser.

Found in DevTools -> Network: the catalog fetches /api/products?page=&offset=&limit=, the
product page /api/products/<id>, and the specs tab /api/products/<id>/specs.
"""

import time
from collections.abc import Callable
from urllib.parse import urljoin

import requests

from scraper.errors import PageLoadError, ProductNotFoundError, RateLimitedError
from scraper.retry import RetryPolicy, parse_retry_after, with_retry
from scraper.throttle import Throttle

CHUNK_LIMIT = 56
USER_AGENT = "laptop-store-scraper/0.1 (Lab 1 PARSER)"
RETRYABLE_ERRORS = (RateLimitedError, PageLoadError, requests.ConnectionError, requests.Timeout)


class ApiSource:
    name = "api"

    def __init__(
        self,
        base_url: str,
        throttle: Throttle,
        retry_policy: RetryPolicy,
        *,
        timeout_seconds: float,
        http: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = base_url
        self.throttle = throttle
        self.retry_policy = retry_policy
        self.timeout_seconds = timeout_seconds
        self.http = http or requests.Session()
        self.http.headers["User-Agent"] = USER_AGENT
        self._sleep = sleep
        self._page_count: int | None = None
        self.api_responses = 0
        self.rate_limited_responses = 0
        self.retries = 0

    def get_json(self, path: str, params: dict | None = None) -> dict:
        def attempt() -> dict:
            self.throttle.wait()
            response = self.http.get(
                urljoin(self.base_url, path), params=params, timeout=self.timeout_seconds
            )
            self.api_responses += 1
            if response.status_code == 429:
                self.rate_limited_responses += 1
                raise RateLimitedError(parse_retry_after(response.headers.get("Retry-After")))
            if response.status_code == 404:
                raise ProductNotFoundError(f"{path} not found")
            if response.status_code >= 500:
                raise PageLoadError(f"{path} returned HTTP {response.status_code}")
            response.raise_for_status()
            return response.json()

        return with_retry(
            attempt,
            self.retry_policy,
            retry_on=RETRYABLE_ERRORS,
            sleep=self._sleep,
            on_retry=self._record_retry,
            description=f"GET {path}",
        )

    def catalog_page(self, page: int) -> list[dict]:
        rows: list[dict] = []
        offset = 0
        while True:
            chunk = self.get_json(
                "/api/products", {"page": page, "offset": offset, "limit": CHUNK_LIMIT}
            )
            self._page_count = chunk["page_count"]
            rows.extend({**item, "source_page": page, "layout": "api"} for item in chunk["items"])
            offset += len(chunk["items"])
            if not chunk["has_more"] or not chunk["items"]:
                return rows

    def page_count(self) -> int | None:
        return self._page_count

    def product(self, product_id: int) -> dict:
        details = self.get_json(f"/api/products/{product_id}")
        specs = self.get_json(f"/api/products/{product_id}/specs")
        return {**details, **specs}

    def stats(self) -> dict:
        return {
            "retries": self.retries,
            "api_responses": self.api_responses,
            "http_429_responses": self.rate_limited_responses,
        }

    def close(self) -> None:
        self.http.close()

    def _record_retry(self, attempt: int, error: BaseException, delay: float) -> None:
        self.retries += 1
