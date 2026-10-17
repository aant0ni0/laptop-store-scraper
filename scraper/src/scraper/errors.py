class ScraperError(Exception):
    """Base class for errors raised while scraping the shop."""


class RateLimitedError(ScraperError):
    def __init__(self, retry_after_seconds: float | None = None) -> None:
        hint = f", retry after {retry_after_seconds:g} s" if retry_after_seconds else ""
        super().__init__(f"rate limited (HTTP 429){hint}")
        self.retry_after_seconds = retry_after_seconds


class PageLoadError(ScraperError):
    """The page reported an error that may go away on retry (for example HTTP 5xx)."""


class ProductNotFoundError(ScraperError):
    """The product does not exist; retrying will not help."""
