import json
import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

from selenium import webdriver
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from scraper.errors import PageLoadError, ProductNotFoundError, RateLimitedError
from scraper.retry import RetryPolicy, parse_retry_after
from scraper.throttle import Throttle

logger = logging.getLogger(__name__)

RETRYABLE_ERRORS = (RateLimitedError, PageLoadError, TimeoutException, WebDriverException)
RATE_LIMIT_MESSAGE = "zbyt wiele zapytań"
NOT_FOUND_MESSAGE = "nie znaleziono"
RETRY_HINT = re.compile(r"za (\d+)\s*s\b")


def create_driver(headless: bool = True) -> WebDriver:
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1366,900")
    options.add_argument("--lang=pl-PL")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    options.add_experimental_option(
        "perfLoggingPrefs", {"enableNetwork": True, "enablePage": False}
    )
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver


@dataclass(frozen=True, slots=True)
class ApiResponse:
    url: str
    status: int
    retry_after_seconds: float | None


class NetworkMonitor:
    """Reads HTTP responses of the page's fetch() calls from Chrome's performance log.

    Selenium itself cannot see status codes; the DevTools network events can, including the
    429 status and its Retry-After header.
    """

    def __init__(self, driver: WebDriver) -> None:
        self._driver = driver
        self.api_responses = 0
        self.rate_limited_responses = 0

    def drain(self) -> list[ApiResponse]:
        try:
            entries = self._driver.get_log("performance")
        except WebDriverException:
            return []
        responses = [response for entry in entries if (response := api_response(entry))]
        self.api_responses += len(responses)
        self.rate_limited_responses += sum(response.status == 429 for response in responses)
        return responses


def api_response(log_entry: dict) -> ApiResponse | None:
    message = json.loads(log_entry["message"])["message"]
    if message.get("method") != "Network.responseReceived":
        return None
    response = message["params"]["response"]
    if "/api/" not in response.get("url", ""):
        return None
    headers = {name.lower(): value for name, value in response.get("headers", {}).items()}
    return ApiResponse(
        url=response["url"],
        status=int(response["status"]),
        retry_after_seconds=parse_retry_after(headers.get("retry-after")),
    )


def retry_hint_from_message(message: str) -> float | None:
    match = RETRY_HINT.search(message)
    return float(match.group(1)) if match else None


@dataclass
class BrowserSession:
    driver: WebDriver
    base_url: str
    throttle: Throttle
    retry_policy: RetryPolicy
    timeout_seconds: float
    quiet_seconds: float
    network: NetworkMonitor = field(init=False)
    retries: int = 0

    def __post_init__(self) -> None:
        self.network = NetworkMonitor(self.driver)

    def open(self, path: str) -> None:
        self.throttle.wait()
        self.network.drain()
        self.driver.get(urljoin(self.base_url, path))

    def wait(self, timeout_seconds: float | None = None) -> WebDriverWait:
        return WebDriverWait(
            self.driver,
            timeout_seconds or self.timeout_seconds,
            poll_frequency=0.1,
            ignored_exceptions=(StaleElementReferenceException,),
        )

    def record_retry(self, attempt: int, error: BaseException, delay: float) -> None:
        self.retries += 1

    def raise_for_error(self, message: str) -> None:
        """Turn an error shown by the page into an exception, preferring the real HTTP status."""
        if not message:
            return
        rate_limited = [r for r in self.network.drain() if r.status == 429]
        if rate_limited:
            retry_after = rate_limited[-1].retry_after_seconds
            raise RateLimitedError(retry_after or retry_hint_from_message(message))
        lowered = message.lower()
        if RATE_LIMIT_MESSAGE in lowered:
            raise RateLimitedError(retry_hint_from_message(message))
        if NOT_FOUND_MESSAGE in lowered:
            raise ProductNotFoundError(message)
        raise PageLoadError(message)


def text_of(driver: WebDriver, selector: str) -> str:
    elements = driver.find_elements(By.CSS_SELECTOR, selector)
    return elements[0].text.strip() if elements else ""


def is_displayed(driver: WebDriver, selector: str) -> bool:
    elements = driver.find_elements(By.CSS_SELECTOR, selector)
    return bool(elements) and elements[0].is_displayed()
