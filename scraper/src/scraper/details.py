from collections.abc import Callable

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from scraper import locators
from scraper.browser import RETRYABLE_ERRORS, BrowserSession, is_displayed, text_of
from scraper.parsing import parse_product_details
from scraper.retry import with_retry


def scrape_product(session: BrowserSession, product_id: int) -> dict:
    """Open the product page, then click the specs tab, whose data is fetched only on click.

    Each step is retried on its own: a failed specs request is repeated by clicking the tab
    again (one request), not by reloading the page (two requests). Under the shop's
    sliding-window limit, waiting for Retry-After frees exactly one request slot.
    """
    retry(session, lambda: open_product_page(session, product_id), f"product {product_id} page")
    retry(session, lambda: load_specs(session), f"product {product_id} specs")
    return parse_product_details(session.driver.page_source)


def retry(session: BrowserSession, action: Callable[[], None], description: str) -> None:
    with_retry(
        action,
        session.retry_policy,
        retry_on=RETRYABLE_ERRORS,
        on_retry=session.record_retry,
        description=description,
    )


def open_product_page(session: BrowserSession, product_id: int) -> None:
    session.open(f"/product.html?id={product_id}")
    session.wait().until(
        lambda d: (
            is_displayed(d, locators.PRODUCT_DETAILS) or bool(text_of(d, locators.PAGE_STATUS))
        )
    )
    session.raise_for_error(text_of(session.driver, locators.PAGE_STATUS))


def load_specs(session: BrowserSession) -> None:
    driver = session.driver
    previous_error = driver.find_elements(By.CSS_SELECTOR, locators.SPECS_STATUS)
    session.throttle.wait()
    session.wait().until(EC.element_to_be_clickable((By.CSS_SELECTOR, locators.SPECS_TAB))).click()
    if previous_error:
        session.wait().until(EC.staleness_of(previous_error[0]))
    session.wait().until(
        lambda d: (
            d.find_elements(By.CSS_SELECTOR, locators.SPECS_LIST)
            or d.find_elements(By.CSS_SELECTOR, locators.SPECS_STATUS)
        )
    )
    session.raise_for_error(text_of(driver, locators.SPECS_STATUS))
