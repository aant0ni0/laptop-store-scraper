"""Merge listing rows with product details, clean and validate them, export the result."""

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd

from scraper.cleaning import (
    clean_text,
    detect_currency,
    parse_date,
    parse_int,
    parse_number,
    parse_price,
    to_pln,
)
from scraper.locators import DETAIL_FIELDS, LISTING_FIELDS, SPEC_FIELDS

COLUMNS = [
    "id",
    "name",
    "url",
    "price_original",
    "currency",
    "price",
    "price_pln",
    "category",
    "brand",
    "availability",
    "rating",
    "review_count",
    "date_added",
    "warranty_months",
    "screen_size_in",
    "resolution",
    "weight_kg",
    "os",
    "color",
    "release_year",
    "cpu",
    "ram_gb",
    "storage_gb",
    "storage_type",
    "gpu",
    "battery_wh",
    "source_page",
    "layout",
]
TEXT_FIELDS = (
    "category",
    "brand",
    "availability",
    "resolution",
    "os",
    "color",
    "cpu",
    "storage_type",
    "gpu",
)
FLOAT_FIELDS = ("price", "price_pln", "rating", "screen_size_in", "weight_kg")
INT_FIELDS = (
    "review_count",
    "warranty_months",
    "release_year",
    "ram_gb",
    "storage_gb",
    "battery_wh",
    "source_page",
)
COMPARED_FIELDS = ("name", "price", "currency", *LISTING_FIELDS)


def valid_ranges(scraped_on: date) -> dict[str, Callable[[object], bool]]:
    return {
        "price": lambda price: price > 0,
        "rating": lambda rating: 0 <= rating <= 5,
        "review_count": lambda count: count >= 0,
        "warranty_months": lambda months: 0 < months <= 120,
        "date_added": lambda added_on: date(2000, 1, 1) <= added_on <= scraped_on,
        "release_year": lambda year: 2000 <= year <= scraped_on.year + 1,
        "screen_size_in": lambda inches: 10 <= inches <= 20,
        "weight_kg": lambda kilograms: 0.5 <= kilograms <= 6,
        "ram_gb": lambda gigabytes: 2 <= gigabytes <= 256,
        "storage_gb": lambda gigabytes: 32 <= gigabytes <= 16_384,
        "battery_wh": lambda watt_hours: 10 <= watt_hours <= 120,
    }


@dataclass
class CleaningReport:
    raw_rows: int
    duplicate_rows: int
    unique_products: int
    products_without_details: int
    rejected_values: dict[str, int]
    listing_detail_mismatches: dict[str, int]


def build_dataset(
    listing_rows: list[dict],
    details_by_id: dict[int, dict],
    *,
    base_url: str,
    scraped_on: date,
    rates: dict[str, float],
) -> tuple[pd.DataFrame, CleaningReport]:
    first_row_by_id: dict[int, dict] = {}
    rejected: Counter[str] = Counter()
    for row in listing_rows:
        product_id = parse_int(row.get("id"))
        if product_id is None:
            rejected["id"] += 1
            continue
        first_row_by_id.setdefault(product_id, row)

    mismatches: Counter[str] = Counter()
    records = []
    for product_id, listing in first_row_by_id.items():
        details = details_by_id.get(product_id) or {}
        record, record_rejected = clean_record(
            product_id, listing, details, base_url=base_url, scraped_on=scraped_on, rates=rates
        )
        records.append(record)
        rejected.update(record_rejected)
        mismatches.update(listing_detail_mismatches(listing, details))

    report = CleaningReport(
        raw_rows=len(listing_rows),
        duplicate_rows=len(listing_rows) - len(first_row_by_id) - rejected["id"],
        unique_products=len(first_row_by_id),
        products_without_details=sum(
            1 for product_id in first_row_by_id if not details_by_id.get(product_id)
        ),
        rejected_values=dict(sorted(rejected.items())),
        listing_detail_mismatches=dict(sorted(mismatches.items())),
    )
    return to_dataframe(records), report


def clean_record(
    product_id: int,
    listing: dict,
    details: dict,
    *,
    base_url: str,
    scraped_on: date,
    rates: dict[str, float],
) -> tuple[dict, list[str]]:
    raw = {**{field: details.get(field) for field in DETAIL_FIELDS + SPEC_FIELDS}, **listing}
    ranges = valid_ranges(scraped_on)
    rejected: list[str] = []

    def take(field: str, parse: Callable[[object], object]) -> object:
        value = parse(raw.get(field))
        is_valid = value is None or field not in ranges or ranges[field](value)
        if (value is None and clean_text(raw.get(field)) is not None) or not is_valid:
            rejected.append(field)
            return None
        return value

    price_text = clean_text(raw.get("price"))
    currency = clean_text(raw.get("currency")) or detect_currency(price_text)
    if currency not in rates:
        rejected.append("currency")
    price = take("price", parse_price)
    href = clean_text(raw.get("url"))

    record = {
        "id": product_id,
        "name": clean_text(raw.get("name")),
        "url": urljoin(base_url, href) if href else None,
        "price_original": price_text,
        "currency": currency,
        "price": price,
        "price_pln": to_pln(price, currency, rates),
        "rating": take("rating", parse_number),
        "date_added": take("date_added", lambda value: parse_date(value, scraped_on)),
        "screen_size_in": take("screen_size_in", parse_number),
        "weight_kg": take("weight_kg", parse_number),
        "source_page": raw.get("source_page"),
        "layout": raw.get("layout"),
    }
    for field in TEXT_FIELDS:
        record[field] = take(field, clean_text)
    for field in INT_FIELDS:
        if field not in record:
            record[field] = take(field, parse_int)
    return record, rejected


def listing_detail_mismatches(listing: dict, details: dict) -> list[str]:
    """Fields the catalog and the product page show differently: a sign of a parser bug."""
    if not details:
        return []
    return [
        field
        for field in COMPARED_FIELDS
        if field in details and clean_text(listing.get(field)) != clean_text(details.get(field))
    ]


def to_dataframe(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame.from_records(records, columns=COLUMNS)
    df["id"] = df["id"].astype("int64")
    for field in INT_FIELDS:
        df[field] = df[field].astype("Int64")
    for field in FLOAT_FIELDS:
        df[field] = pd.to_numeric(df[field], errors="coerce").astype("float64")
    df["date_added"] = pd.to_datetime(df["date_added"])
    return df.sort_values("id", ignore_index=True)


def raw_rows(listing_rows: list[dict], details_by_id: dict[int, dict]) -> pd.DataFrame:
    """Uncleaned rows, duplicates included, for quality control."""
    rows = []
    for listing in listing_rows:
        details = details_by_id.get(parse_int(listing.get("id"))) or {}
        rows.append(
            {**listing, **{field: details.get(field) for field in DETAIL_FIELDS + SPEC_FIELDS}}
        )
    return pd.DataFrame(rows)


def export(df: pd.DataFrame, raw: pd.DataFrame, output_base: Path) -> list[Path]:
    output_base.parent.mkdir(parents=True, exist_ok=True)
    csv_path = output_base.with_suffix(".csv")
    xlsx_path = output_base.with_suffix(".xlsx")
    raw_path = output_base.with_name(f"{output_base.stem}_raw.csv")

    df.to_csv(csv_path, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    with pd.ExcelWriter(
        xlsx_path, engine="openpyxl", date_format="YYYY-MM-DD", datetime_format="YYYY-MM-DD"
    ) as writer:
        df.to_excel(writer, index=False, sheet_name="laptops")
    raw.to_csv(raw_path, index=False, encoding="utf-8-sig")
    return [csv_path, xlsx_path, raw_path]
