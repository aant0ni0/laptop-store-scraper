from datetime import date

import pytest

from scraper.cleaning import (
    clean_text,
    detect_currency,
    parse_date,
    parse_int,
    parse_number,
    parse_price,
    to_pln,
)

SCRAPED_ON = date(2026, 10, 14)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("4 199,00 zł", 4199.0),
        ("4\xa0199,00\xa0zł", 4199.0),
        ("4 199,00 zł", 4199.0),
        ("899,00 zł", 899.0),
        ("12 499,00 zł", 12499.0),
        ("$1,239.99", 1239.99),
        ("€999.99", 999.99),
        ("€2,345.99", 2345.99),
        ("1 299 zł", 1299.0),
        ("$1,299", 1299.0),
    ],
)
def test_parse_price_handles_polish_and_english_number_formats(text, expected):
    assert parse_price(text) == pytest.approx(expected)


def test_parse_price_does_not_turn_decimal_comma_into_thousands():
    assert parse_price("1 299,00 zł") != 129900


@pytest.mark.parametrize("text", [None, "", "—", "cena na zapytanie"])
def test_parse_price_returns_none_without_a_number(text):
    assert parse_price(text) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("4 199,00 zł", "PLN"),
        ("12 PLN", "PLN"),
        ("$1,239.99", "USD"),
        ("€999.99", "EUR"),
        ("1", None),
    ],
)
def test_detect_currency_from_price_text(text, expected):
    assert detect_currency(text) == expected


def test_to_pln_converts_with_given_rates():
    rates = {"PLN": 1.0, "EUR": 4.0, "USD": 3.5}
    assert to_pln(100.0, "PLN", rates) == 100.0
    assert to_pln(99.99, "EUR", rates) == pytest.approx(399.96)
    assert to_pln(10.0, "USD", rates) == 35.0


def test_to_pln_returns_none_for_missing_amount_or_unknown_currency():
    rates = {"PLN": 1.0}
    assert to_pln(None, "PLN", rates) is None
    assert to_pln(10.0, "GBP", rates) is None
    assert to_pln(10.0, None, rates) is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026-08-26", date(2026, 8, 26)),
        ("26.08.2026", date(2026, 8, 26)),
        (" 01.02.2025 ", date(2025, 2, 1)),
        ("wczoraj", date(2026, 10, 13)),
        ("Wczoraj", date(2026, 10, 13)),
        ("dzisiaj", date(2026, 10, 14)),
        ("przedwczoraj", date(2026, 10, 12)),
    ],
)
def test_parse_date_unifies_formats(text, expected):
    assert parse_date(text, SCRAPED_ON) == expected


@pytest.mark.parametrize("text", [None, "—", "kiedyś", "31.02.2026", "2026/08/26"])
def test_parse_date_returns_none_for_unknown_or_invalid_dates(text):
    assert parse_date(text, SCRAPED_ON) is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ('15.6"', 15.6),
        ("1.85 kg", 1.85),
        ("16 GB", 16.0),
        ("24 mies.", 24.0),
        ("55 Wh", 55.0),
        ("4,5", 4.5),
        ("1 024 GB", 1024.0),
        (4.3, 4.3),
        (36, 36.0),
    ],
)
def test_parse_number_strips_units(value, expected):
    assert parse_number(value) == pytest.approx(expected)


@pytest.mark.parametrize("value", [None, "", "—", "-", "brak", "n/a"])
def test_parse_number_returns_none_for_missing_values(value):
    assert parse_number(value) is None


def test_parse_number_ignores_booleans():
    assert parse_number(True) is None


def test_parse_int_rejects_fractions():
    assert parse_int("24 mies.") == 24
    assert parse_int(512) == 512
    assert parse_int("1.5 GB") is None
    assert parse_int("—") is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("  Intel  Core\xa0i5 ", "Intel Core i5"),
        ("Dostępny", "Dostępny"),
        ("—", None),
        ("", None),
        (None, None),
        (12, "12"),
    ],
)
def test_clean_text_normalises_whitespace_and_missing_markers(value, expected):
    assert clean_text(value) == expected
