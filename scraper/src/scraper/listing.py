import logging

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from scraper import locators
from scraper.browser import RETRYABLE_ERRORS, BrowserSession, is_displayed, text_of
from scraper.parsing import parse_catalog
from scraper.retry import with_retry

logger = logging.getLogger(__name__)


def scrape_catalog_page(session: BrowserSession, page: int) -> list[dict]:
    session.open(f"/?page={page}")
    with_retry(
        lambda: load_remaining_chunks(session),
        session.retry_policy,
        retry_on=RETRYABLE_ERRORS,
        on_retry=session.record_retry,
        description=f"catalog page {page}",
    )
    rows = parse_catalog(session.driver.page_source, page)
    logger.info("catalog page %d: %d products (%s)", page, len(rows), layout_of(rows))
    return rows


def load_remaining_chunks(session: BrowserSession) -> None:
    """Scroll to the load trigger until the page stops adding products.

    The page loads chunks when `.load-trigger` comes into view and stops observing it after
    the last chunk. So: wait until idle, scroll the trigger into view, and if within the
    quiet period no loading starts, the list is exhausted. A failed chunk (for example
    HTTP 429) raises, and the next attempt resumes with the page's own retry button.
    """
    driver = session.driver
    if is_displayed(driver, locators.RETRY_BUTTON):
        session.throttle.wait()
        driver.find_element(By.CSS_SELECTOR, locators.RETRY_BUTTON).click()

    while True:
        session.wait().until(chunk_settled)
        session.raise_for_error(text_of(driver, locators.PAGE_STATUS))
        count_before = product_count(driver)
        session.throttle.wait()
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'end'});",
            driver.find_element(By.CSS_SELECTOR, locators.LOAD_TRIGGER),
        )
        if not loading_started(session, count_before):
            return


def chunk_settled(driver: WebDriver) -> bool:
    if is_displayed(driver, locators.LOADING):
        return False
    return product_count(driver) > 0 or bool(text_of(driver, locators.PAGE_STATUS))


def loading_started(session: BrowserSession, count_before: int) -> bool:
    try:
        session.wait(session.quiet_seconds).until(
            lambda driver: (
                is_displayed(driver, locators.LOADING)
                or product_count(driver) > count_before
                or bool(text_of(driver, locators.PAGE_STATUS))
            )
        )
    except TimeoutException:
        return False
    return True


def product_count(driver: WebDriver) -> int:
    return len(driver.find_elements(By.CSS_SELECTOR, locators.PRODUCT))


def read_page_count(driver: WebDriver) -> int:
    return len(driver.find_elements(By.CSS_SELECTOR, locators.PAGE_LINK))


def layout_of(rows: list[dict]) -> str:
    return ", ".join(sorted({row["layout"] for row in rows})) or "empty"
