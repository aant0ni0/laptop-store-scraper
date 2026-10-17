"""CSS selectors for the partner's shop, shared by Selenium waits and BeautifulSoup parsing.

Product fields are found by the class derived from the JSON field name (`review_count` ->
`.review-count`), never by column position or the Polish label, so the same selector works
for table rows, cards and the product page.
"""

PRODUCT = ".catalog .product"
PRODUCT_LINK = ".product-name a.product-link"
PRICE = ".price"
LOAD_TRIGGER = ".load-trigger"
LOADING = "main > .loading"
RETRY_BUTTON = "main > .retry"
PAGE_STATUS = "main > .status"
PAGE_LINK = ".pagination a.page-link"

PRODUCT_DETAILS = "article.product-details"
PRODUCT_NAME = "h1.product-name"
OVERVIEW_PANEL = "#panel-overview"
SPECS_TAB = "#tab-specs"
SPECS_PANEL = "#panel-specs"
SPECS_LIST = "#panel-specs dl.product-attributes"
SPECS_STATUS = "#panel-specs .status"

LISTING_FIELDS = (
    "category",
    "brand",
    "availability",
    "rating",
    "review_count",
    "date_added",
    "warranty_months",
)
DETAIL_FIELDS = ("screen_size_in", "resolution", "weight_kg", "os", "color", "release_year")
SPEC_FIELDS = ("cpu", "ram_gb", "storage_gb", "storage_type", "gpu", "battery_wh")


def field_selector(field: str) -> str:
    return "." + field.replace("_", "-")
