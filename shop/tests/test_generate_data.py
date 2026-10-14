import json
import random
import re
from collections import defaultdict
from statistics import correlation

import pytest
from generate_data import (
    DUPLICATE_COUNT,
    PRODUCT_COUNT,
    SEED,
    generate_catalog,
    generate_products,
)

from shop.catalog import DATA_PATH, PAGE_COUNT, PAGE_SIZE

EXPECTED_ATTRIBUTES = {
    "id",
    "name",
    "price",
    "currency",
    "category",
    "brand",
    "availability",
    "rating",
    "review_count",
    "date_added",
    "warranty_months",
    "url",
    "cpu",
    "ram_gb",
    "storage_gb",
    "storage_type",
    "gpu",
    "screen_size_in",
    "resolution",
    "weight_kg",
    "battery_wh",
    "os",
    "color",
    "release_year",
}


PLN_PRICE = re.compile(r"^\d{1,3}( \d{3})*,\d{2} zł$")
FOREIGN_PRICE = re.compile(r"^[€$]\d{1,3}(,\d{3})*\.\d{2}$")
DATE_FORMATS = {
    "iso": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "dotted": re.compile(r"^\d{2}\.\d{2}\.\d{4}$"),
    "yesterday": re.compile(r"^wczoraj$"),
}


@pytest.fixture(scope="module")
def products() -> list[dict]:
    return generate_products(random.Random(SEED))


@pytest.fixture(scope="module")
def catalog() -> list[dict]:
    return generate_catalog()


def test_generates_expected_number_of_unique_products(products):
    assert len(products) == PRODUCT_COUNT
    assert len({product["id"] for product in products}) == PRODUCT_COUNT
    assert len({product["name"] for product in products}) == PRODUCT_COUNT


def test_every_product_has_all_attributes(products):
    assert len(EXPECTED_ATTRIBUTES) >= 22
    for product in products:
        assert set(product) == EXPECTED_ATTRIBUTES


def test_values_are_within_realistic_ranges(products):
    for product in products:
        assert 1000 < product["price"] < 25000
        assert 1.0 <= product["rating"] <= 5.0
        assert product["review_count"] >= 1
        assert 8 <= product["ram_gb"] <= 64
        assert 0.9 <= product["weight_kg"] <= 3.5
        assert product["release_year"] <= int(product["date_added"][:4])


def test_gaming_laptops_have_dedicated_graphics(products):
    gaming = [product for product in products if product["category"] == "Gamingowy"]
    assert gaming
    assert all(product["gpu"].startswith("NVIDIA") for product in gaming)


def test_specs_drive_price_and_weight(products):
    prices = [product["price"] for product in products]
    ram = [product["ram_gb"] for product in products]
    screens = [product["screen_size_in"] for product in products]
    weights = [product["weight_kg"] for product in products]

    assert correlation(ram, prices) > 0.5
    assert correlation(screens, weights) > 0.7


def test_catalog_spreads_duplicates_across_pages(catalog):
    assert len(catalog) == PAGE_COUNT * PAGE_SIZE
    assert len({product["id"] for product in catalog}) == PRODUCT_COUNT >= 400

    pages_by_id = defaultdict(list)
    for position, product in enumerate(catalog):
        pages_by_id[product["id"]].append(position // PAGE_SIZE)
    duplicated_pages = [pages for pages in pages_by_id.values() if len(pages) > 1]

    assert len(duplicated_pages) == DUPLICATE_COUNT >= 8
    assert all(len(set(pages)) == len(pages) for pages in duplicated_pages)


def test_duplicates_are_exact_copies(catalog):
    first_seen = {}
    for product in catalog:
        original = first_seen.setdefault(product["id"], product)
        assert original == product


def test_prices_are_text_in_several_currencies(catalog):
    for product in catalog:
        pattern = PLN_PRICE if product["currency"] == "PLN" else FOREIGN_PRICE
        assert pattern.match(product["price"]), product["price"]

    foreign_share = share(catalog, lambda product: product["currency"] != "PLN")
    assert {product["currency"] for product in catalog} == {"PLN", "EUR", "USD"}
    assert 0.1 <= foreign_share <= 0.2


@pytest.mark.parametrize("field", ["rating", "warranty_months"])
def test_two_fields_have_missing_values(catalog, field):
    assert share(catalog, lambda product: product[field] is None) >= 0.15


def test_dates_use_inconsistent_formats(catalog):
    formats_seen = set()
    for product in catalog:
        matching = [
            name for name, pattern in DATE_FORMATS.items() if pattern.match(product["date_added"])
        ]
        assert len(matching) == 1, product["date_added"]
        formats_seen.add(matching[0])
    assert formats_seen == set(DATE_FORMATS)


def test_generation_is_deterministic():
    assert generate_catalog() == generate_catalog()


def test_saved_catalog_matches_generator(catalog):
    saved = json.loads(DATA_PATH.read_text("utf-8"))
    assert saved == catalog, "products.json is stale - run scripts/generate_data.py"


def share(products: list[dict], predicate) -> float:
    return sum(1 for product in products if predicate(product)) / len(products)
