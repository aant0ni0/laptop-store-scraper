from datetime import date

import pandas as pd
import pytest

from scraper.dataset import build_dataset, export, raw_rows

BASE_URL = "http://localhost:8000"
SCRAPED_ON = date(2026, 10, 14)
RATES = {"PLN": 1.0, "EUR": 4.0, "USD": 4.0}


def listing(product_id, page=1, **overrides):
    row = {
        "id": str(product_id),
        "name": f"Laptop {product_id}",
        "url": f"/product.html?id={product_id}",
        "price": "1 299,00 zł",
        "currency": "PLN",
        "category": "Budżetowy",
        "brand": "Lenovo",
        "availability": "Dostępny",
        "rating": "4.5",
        "review_count": "12",
        "date_added": "26.08.2026",
        "warranty_months": "24 mies.",
        "source_page": page,
        "layout": "table" if page % 2 else "card",
    }
    return row | overrides


def details(**overrides):
    row = {
        "screen_size_in": '15.6"',
        "resolution": "1920x1080",
        "weight_kg": "1.75 kg",
        "os": "Windows 11 Home",
        "color": "Srebrny",
        "release_year": "2025",
        "cpu": "Intel Core i5-1335U",
        "ram_gb": "16 GB",
        "storage_gb": "512 GB",
        "storage_type": "SSD",
        "gpu": "Intel Iris Xe Graphics",
        "battery_wh": "45 Wh",
    }
    return row | overrides


def build(listing_rows, details_by_id):
    return build_dataset(
        listing_rows, details_by_id, base_url=BASE_URL, scraped_on=SCRAPED_ON, rates=RATES
    )


def test_listing_and_details_are_merged_into_typed_columns():
    df, report = build([listing(1)], {1: details()})
    row = df.iloc[0]
    assert row["price"] == 1299.0
    assert row["price_pln"] == 1299.0
    assert row["date_added"] == pd.Timestamp("2026-08-26")
    assert row["warranty_months"] == 24
    assert row["screen_size_in"] == 15.6
    assert row["ram_gb"] == 16
    assert row["url"] == "http://localhost:8000/product.html?id=1"
    assert report.rejected_values == {}
    assert len(df.columns) >= 24


def test_duplicates_are_counted_and_removed():
    rows = [listing(1, page=1), listing(2, page=1), listing(1, page=5)]
    df, report = build(rows, {1: details(), 2: details()})
    assert report.raw_rows == 3
    assert report.duplicate_rows == 1
    assert report.unique_products == 2
    assert df["id"].tolist() == [1, 2]
    assert df.loc[df["id"] == 1, "source_page"].item() == 1


def test_foreign_prices_are_converted_to_pln():
    df, _ = build([listing(1, price="$1,239.99", currency="USD")], {1: details()})
    assert df.loc[0, "price"] == pytest.approx(1239.99)
    assert df.loc[0, "price_pln"] == pytest.approx(4959.96)


def test_missing_values_become_empty_cells_not_errors():
    df, report = build([listing(1, rating="—", warranty_months="—")], {})
    assert pd.isna(df.loc[0, "rating"])
    assert pd.isna(df.loc[0, "warranty_months"])
    assert pd.isna(df.loc[0, "ram_gb"])
    assert report.products_without_details == 1
    assert report.rejected_values == {}


def test_unparseable_and_out_of_range_values_are_rejected_and_counted():
    df, report = build([listing(1, rating="9.5", date_added="kiedyś")], {1: details(ram_gb="dużo")})
    assert pd.isna(df.loc[0, "rating"])
    assert pd.isna(df.loc[0, "date_added"])
    assert pd.isna(df.loc[0, "ram_gb"])
    assert report.rejected_values == {"date_added": 1, "ram_gb": 1, "rating": 1}


def test_numeric_columns_have_numeric_dtypes():
    df, _ = build([listing(1)], {1: details()})
    for column in ("price", "price_pln", "rating", "weight_kg"):
        assert pd.api.types.is_float_dtype(df[column])
    for column in ("review_count", "ram_gb", "storage_gb", "battery_wh", "release_year"):
        assert pd.api.types.is_integer_dtype(df[column])
    assert pd.api.types.is_datetime64_any_dtype(df["date_added"])


def test_api_values_are_cleaned_like_page_text():
    api_row = listing(1, rating=4.5, review_count=12, warranty_months=None, date_added="wczoraj")
    api_details = details(ram_gb=16, storage_gb=512, weight_kg=1.75, release_year=2025)
    df, report = build([api_row], {1: api_details})
    assert df.loc[0, "rating"] == 4.5
    assert pd.isna(df.loc[0, "warranty_months"])
    assert df.loc[0, "date_added"] == pd.Timestamp("2026-10-13")
    assert df.loc[0, "ram_gb"] == 16
    assert report.rejected_values == {}


def test_listing_and_product_page_disagreement_is_reported():
    _, report = build([listing(1)], {1: details(category="Gamingowy", brand="Lenovo")})
    assert report.listing_detail_mismatches == {"category": 1}


def test_export_writes_csv_and_xlsx_with_polish_characters(tmp_path):
    df, _ = build([listing(1, name="Laptop żółty")], {1: details()})
    paths = export(df, raw_rows([listing(1)], {1: details()}), tmp_path / "laptops")
    assert [path.name for path in paths] == ["laptops.csv", "laptops.xlsx", "laptops_raw.csv"]

    csv_text = paths[0].read_text("utf-8-sig")
    assert "Laptop żółty" in csv_text
    assert "2026-08-26" in csv_text
    assert pd.read_excel(paths[1]).loc[0, "category"] == "Budżetowy"
