"""Compare what a plain HTTP client receives with the DOM the browser builds by running scripts.

uv run python -m scraper.raw_vs_dom [--pages 8] [--product-id 1]
"""

import argparse
import logging
import sys
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from scraper import config, locators
from scraper.browser import is_displayed
from scraper.parsing import count_products, parse_product_details
from scraper.retry import RetryPolicy
from scraper.selenium_source import SeleniumSource
from scraper.throttle import Throttle

logger = logging.getLogger(__name__)
PRODUCT_FIELDS = locators.LISTING_FIELDS + locators.DETAIL_FIELDS + locators.SPEC_FIELDS


def filled_fields(details: dict) -> int:
    return sum(details.get(field) is not None for field in PRODUCT_FIELDS)


def compare(base_url: str, pages: int, product_id: int, *, headless: bool) -> pd.DataFrame:
    throttle = Throttle(config.REQUEST_DELAY_SECONDS)
    http = requests.Session()
    source = SeleniumSource(
        base_url,
        throttle,
        RetryPolicy(),
        headless=headless,
        timeout_seconds=config.WAIT_TIMEOUT_SECONDS,
        quiet_seconds=config.END_OF_LIST_QUIET_SECONDS,
    )
    rows = []
    try:
        for page in range(1, pages + 1):
            path = f"/?page={page}"
            throttle.wait()
            raw_html = http.get(urljoin(base_url, path), timeout=10).text
            dom_rows = source.catalog_page(page)
            rows.append(
                {
                    "page": path,
                    "what": "records (.catalog .product)",
                    "raw_html": count_products(raw_html),
                    "dom_after_scripts": len(dom_rows),
                    "raw_html_kb": round(len(raw_html.encode()) / 1024, 1),
                    "dom_kb": round(len(source.session.driver.page_source.encode()) / 1024, 1),
                }
            )
        rows.extend(compare_product_page(source, http, throttle, base_url, product_id))
    finally:
        source.close()
        http.close()
    return pd.DataFrame(rows)


def compare_product_page(
    source: SeleniumSource,
    http: requests.Session,
    throttle: Throttle,
    base_url: str,
    product_id: int,
) -> list[dict]:
    path = f"/product.html?id={product_id}"
    throttle.wait()
    raw_html = http.get(urljoin(base_url, path), timeout=10).text
    raw_fields = filled_fields(parse_product_details(raw_html))
    raw_dd = len(BeautifulSoup(raw_html, "html.parser").select("dd"))

    session = source.session
    driver = session.driver
    session.open(path)
    session.wait().until(lambda d: is_displayed(d, locators.PRODUCT_DETAILS))
    before_click = filled_fields(parse_product_details(driver.page_source))
    throttle.wait()
    session.wait().until(EC.element_to_be_clickable((By.CSS_SELECTOR, locators.SPECS_TAB))).click()
    session.wait().until(lambda d: d.find_elements(By.CSS_SELECTOR, locators.SPECS_LIST))
    after_click = filled_fields(parse_product_details(driver.page_source))
    dom_dd = len(driver.find_elements(By.CSS_SELECTOR, "dd"))

    return [
        {
            "page": path,
            "what": f"product fields (of {len(PRODUCT_FIELDS)}) before clicking the specs tab",
            "raw_html": raw_fields,
            "dom_after_scripts": before_click,
        },
        {
            "page": path,
            "what": f"product fields (of {len(PRODUCT_FIELDS)}) after clicking the specs tab",
            "raw_html": raw_fields,
            "dom_after_scripts": after_click,
        },
        {"page": path, "what": "<dd> elements", "raw_html": raw_dd, "dom_after_scripts": dom_dd},
    ]


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="python -m scraper.raw_vs_dom")
    parser.add_argument("--base-url", default=config.DEFAULT_BASE_URL)
    parser.add_argument("--pages", type=int, default=8)
    parser.add_argument("--product-id", type=int, default=1)
    parser.add_argument("--headless", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--output", default=str(config.OUTPUT_DIR / "raw_vs_dom.csv"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    table = compare(args.base_url, args.pages, args.product_id, headless=args.headless)
    table.to_csv(args.output, index=False, encoding="utf-8-sig")
    records = table[table["what"].str.startswith("records")]
    print(table.to_string(index=False))
    print(
        f"\nRecords in raw HTML: {records['raw_html'].sum()}, "
        f"in the DOM after scripts: {records['dom_after_scripts'].sum()}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
