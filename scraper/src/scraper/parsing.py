"""Extract raw field text from the DOM rendered by the browser.

Selenium only renders the page; reading hundreds of fields through WebDriver calls would cost
one round trip each, so the finished DOM is parsed here with the same CSS selectors.
"""

from bs4 import BeautifulSoup, Tag

from scraper import locators
from scraper.locators import field_selector


def parse_catalog(html: str, page: int) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    return [parse_catalog_entry(entry, page) for entry in soup.select(locators.PRODUCT)]


def parse_catalog_entry(entry: Tag, page: int) -> dict:
    link = entry.select_one(locators.PRODUCT_LINK)
    return {
        "id": entry.get("data-id"),
        "name": text_of(link),
        "url": link.get("href") if link else None,
        "price": text_of(entry.select_one(locators.PRICE)),
        "currency": entry.get("data-currency"),
        **fields(entry, locators.LISTING_FIELDS),
        "source_page": page,
        "layout": "table" if entry.name == "tr" else "card",
    }


def parse_product_details(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    details = soup.select_one(locators.PRODUCT_DETAILS)
    if details is None:
        return {}
    return {
        "id": details.get("data-id"),
        "name": text_of(details.select_one(locators.PRODUCT_NAME)),
        "price": text_of(details.select_one(locators.PRICE)),
        "currency": details.get("data-currency"),
        **fields(
            details.select_one(locators.OVERVIEW_PANEL),
            locators.LISTING_FIELDS + locators.DETAIL_FIELDS,
        ),
        **fields(details.select_one(locators.SPECS_PANEL), locators.SPEC_FIELDS),
    }


def fields(scope: Tag | None, names: tuple[str, ...]) -> dict[str, str | None]:
    if scope is None:
        return dict.fromkeys(names)
    return {name: text_of(scope.select_one(field_selector(name))) for name in names}


def text_of(tag: Tag | None) -> str | None:
    return tag.get_text(" ", strip=True) if tag is not None else None


def count_products(html: str) -> int:
    return len(BeautifulSoup(html, "html.parser").select(locators.PRODUCT))
