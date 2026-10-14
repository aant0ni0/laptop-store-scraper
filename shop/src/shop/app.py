import json
import random
import time
from pathlib import Path

from flask import Flask, request

from shop.catalog import DATA_PATH, PAGE_COUNT, PAGE_SIZE

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
DEFAULT_CHUNK_SIZE = 14

LISTING_FIELDS = (
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
)
SPEC_FIELDS = ("cpu", "ram_gb", "storage_gb", "storage_type", "gpu", "battery_wh")


def create_app(data_path: Path = DATA_PATH) -> Flask:
    app = Flask(__name__, static_folder=WEB_DIR, static_url_path="")
    app.json.sort_keys = False
    app.json.ensure_ascii = False
    app.config["CHUNK_DELAY_SECONDS"] = (0.3, 2.0)

    catalog = json.loads(data_path.read_text("utf-8"))
    products_by_id = {product["id"]: product for product in catalog}

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.get("/api/products")
    def product_chunk():
        page = request.args.get("page", type=int)
        if page is None or not 1 <= page <= PAGE_COUNT:
            return error(f"page must be an integer between 1 and {PAGE_COUNT}", 400)

        try:
            offset = int(request.args.get("offset", "0"))
            limit = int(request.args.get("limit", str(DEFAULT_CHUNK_SIZE)))
        except ValueError:
            return error("offset and limit must be integers", 400)

        if offset < 0:
            return error("offset must be a non-negative integer", 400)
        if not 1 <= limit <= PAGE_SIZE:
            return error(f"limit must be an integer between 1 and {PAGE_SIZE}", 400)

        page_entries = catalog[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]
        chunk = page_entries[offset : offset + limit]
        time.sleep(random.uniform(*app.config["CHUNK_DELAY_SECONDS"]))
        return {
            "page": page,
            "page_count": PAGE_COUNT,
            "total": len(page_entries),
            "has_more": offset + limit < len(page_entries),
            "items": [pick(product, LISTING_FIELDS) for product in chunk],
        }

    @app.get("/api/products/<int:product_id>")
    def product_details(product_id: int):
        product = products_by_id.get(product_id)
        if product is None:
            return error("product not found", 404)
        return {field: value for field, value in product.items() if field not in SPEC_FIELDS}

    @app.get("/api/products/<int:product_id>/specs")
    def product_specs(product_id: int):
        product = products_by_id.get(product_id)
        if product is None:
            return error("product not found", 404)
        return pick(product, SPEC_FIELDS)

    return app


def pick(product: dict, fields: tuple[str, ...]) -> dict:
    return {field: product[field] for field in fields}


def error(message: str, status: int) -> tuple[dict, int]:
    return {"error": message}, status
