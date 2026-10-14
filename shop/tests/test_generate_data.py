import json
from statistics import correlation

import pytest
from generate_data import OUTPUT_PATH, PRODUCT_COUNT, generate_products

EXPECTED_ATTRIBUTES = {
    # listing
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
    # details
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


@pytest.fixture(scope="module")
def products() -> list[dict]:
    return generate_products()


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


def test_generation_is_deterministic():
    assert generate_products() == generate_products()


def test_saved_catalog_matches_generator(products):
    saved = json.loads(OUTPUT_PATH.read_text("utf-8"))
    assert saved == products, "products.json is stale - run scripts/generate_data.py"
