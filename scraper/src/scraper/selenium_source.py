from scraper.browser import BrowserSession, create_driver
from scraper.details import scrape_product
from scraper.listing import read_page_count, scrape_catalog_page
from scraper.retry import RetryPolicy
from scraper.throttle import Throttle


class SeleniumSource:
    """Shop data read the way a visitor sees it: rendered by Chrome, loaded by scrolling."""

    name = "selenium"

    def __init__(
        self,
        base_url: str,
        throttle: Throttle,
        retry_policy: RetryPolicy,
        *,
        headless: bool,
        timeout_seconds: float,
        quiet_seconds: float,
    ) -> None:
        self.session = BrowserSession(
            driver=create_driver(headless=headless),
            base_url=base_url,
            throttle=throttle,
            retry_policy=retry_policy,
            timeout_seconds=timeout_seconds,
            quiet_seconds=quiet_seconds,
        )
        self._page_count: int | None = None

    def catalog_page(self, page: int) -> list[dict]:
        rows = scrape_catalog_page(self.session, page)
        self._page_count = read_page_count(self.session.driver) or self._page_count
        return rows

    def page_count(self) -> int | None:
        return self._page_count

    def product(self, product_id: int) -> dict:
        return scrape_product(self.session, product_id)

    def stats(self) -> dict:
        self.session.network.drain()
        return {
            "retries": self.session.retries,
            "api_responses": self.session.network.api_responses,
            "http_429_responses": self.session.network.rate_limited_responses,
        }

    def close(self) -> None:
        self.session.driver.quit()
