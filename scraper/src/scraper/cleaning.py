"""Turn the raw text shown by the shop (or values returned by its API) into typed values.

Every function returns None instead of raising when a value is missing or cannot be parsed,
so one bad field never stops the scraper.
"""

import re
from datetime import date, datetime, timedelta

MISSING_MARKERS = frozenset({"", "—", "–", "-", "brak", "n/a", "none", "null"})
RELATIVE_DAYS = {"dzisiaj": 0, "dziś": 0, "wczoraj": 1, "przedwczoraj": 2}
DATE_FORMATS = ("%Y-%m-%d", "%d.%m.%Y")
CURRENCY_MARKERS = {"zł": "PLN", "pln": "PLN", "€": "EUR", "eur": "EUR", "$": "USD", "usd": "USD"}

_SPACES = re.compile(r"[\s  ]+")
_NUMBER = re.compile(r"\d[\d\s  .,]*")
_DIGIT_GROUP_SPACE = re.compile(r"(?<=\d)[\s  ](?=\d{3}(?!\d))")


def clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = _SPACES.sub(" ", str(value)).strip()
    return None if text.lower() in MISSING_MARKERS else text


def parse_price(text: object) -> float | None:
    """Parse "4 199,00 zł" and "$1,239.99" alike, deciding the decimal separator by position.

    A separator followed by exactly one or two final digits is the decimal point; every other
    separator groups thousands. That is what keeps "1 299,00 zł" from becoming 129900.
    """
    cleaned = clean_text(text)
    if cleaned is None:
        return None
    match = _NUMBER.search(cleaned)
    if match is None:
        return None
    number = _SPACES.sub("", match.group()).rstrip(".,")
    decimal_match = re.search(r"[.,](\d{1,2})$", number)
    if decimal_match:
        integer_part = number[: decimal_match.start()]
        fraction = decimal_match.group(1)
    else:
        integer_part, fraction = number, "0"
    digits = re.sub(r"[.,]", "", integer_part)
    return float(f"{digits}.{fraction}") if digits else None


def detect_currency(text: object) -> str | None:
    cleaned = clean_text(text)
    if cleaned is None:
        return None
    lowered = cleaned.lower()
    for marker, currency in CURRENCY_MARKERS.items():
        if marker in lowered:
            return currency
    return None


def to_pln(amount: float | None, currency: str | None, rates: dict[str, float]) -> float | None:
    if amount is None or currency not in rates:
        return None
    return round(amount * rates[currency], 2)


def parse_date(text: object, scraped_on: date) -> date | None:
    cleaned = clean_text(text)
    if cleaned is None:
        return None
    lowered = cleaned.lower()
    if lowered in RELATIVE_DAYS:
        return scraped_on - timedelta(days=RELATIVE_DAYS[lowered])
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, date_format).date()
        except ValueError:
            continue
    return None


def parse_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    cleaned = clean_text(value)
    if cleaned is None:
        return None
    match = re.search(r"\d+(?:[.,]\d+)?", _DIGIT_GROUP_SPACE.sub("", cleaned))
    if match is None:
        return None
    return float(match.group().replace(",", "."))


def parse_int(value: object) -> int | None:
    number = parse_number(value)
    if number is None or not number.is_integer():
        return None
    return int(number)
