import json

import pytest

from shop.app import LISTING_FIELDS, SPEC_FIELDS, create_app
from shop.catalog import DATA_PATH, PAGE_COUNT, PAGE_SIZE

CATALOG = json.loads(DATA_PATH.read_text("utf-8"))


@pytest.fixture
def client():
    app = create_app()
    app.config["CHUNK_DELAY_SECONDS"] = (0, 0)
    return app.test_client()


def test_chunk_response_is_delayed_by_configured_range(monkeypatch):
    recorded_delays = []
    monkeypatch.setattr("shop.app.time.sleep", recorded_delays.append)

    create_app().test_client().get("/api/products?page=1")

    assert len(recorded_delays) == 1
    assert 0.3 <= recorded_delays[0] <= 2.0


@pytest.mark.parametrize("path", ["/api/products/1", "/api/products/1/specs"])
def test_details_and_specs_are_not_delayed(monkeypatch, path):
    recorded_delays = []
    monkeypatch.setattr("shop.app.time.sleep", recorded_delays.append)

    create_app().test_client().get(path)

    assert recorded_delays == []


def test_first_chunk_contains_listing_fields_only(client):
    response = client.get("/api/products?page=1")

    assert response.status_code == 200
    body = response.json
    assert len(body["items"]) == 14
    assert body["total"] == PAGE_SIZE
    assert body["has_more"] is True
    assert all(tuple(item) == LISTING_FIELDS for item in body["items"])


def test_chunks_from_all_pages_cover_the_whole_catalog(client):
    collected_ids = []
    for page in range(1, PAGE_COUNT + 1):
        offset, has_more = 0, True
        while has_more:
            body = client.get(f"/api/products?page={page}&offset={offset}&limit=20").json
            collected_ids += [item["id"] for item in body["items"]]
            offset += len(body["items"])
            has_more = body["has_more"]

    assert collected_ids == [product["id"] for product in CATALOG]


@pytest.mark.parametrize(
    "query",
    [
        "",
        "page=0",
        f"page={PAGE_COUNT + 1}",
        "page=abc",
        "page=1&offset=-1",
        "page=1&offset=abc",
        "page=1&offset=1.5",
        "page=1&limit=abc",
        "page=1&limit=",
        "page=1&limit=0",
        f"page=1&limit={PAGE_SIZE + 1}",
    ],
)
def test_invalid_chunk_query_is_rejected(client, query):
    response = client.get(f"/api/products?{query}")

    assert response.status_code == 400
    assert "error" in response.json


def test_product_details_exclude_specs(client):
    product = CATALOG[0]
    body = client.get(f"/api/products/{product['id']}").json

    assert set(LISTING_FIELDS) < set(body)
    assert set(SPEC_FIELDS).isdisjoint(body)
    assert body == {field: product[field] for field in body}


def test_product_specs_contain_only_spec_fields(client):
    product = CATALOG[0]
    body = client.get(f"/api/products/{product['id']}/specs").json

    assert body == {field: product[field] for field in SPEC_FIELDS}


@pytest.mark.parametrize("path", ["/api/products/9999", "/api/products/9999/specs"])
def test_unknown_product_returns_404(client, path):
    response = client.get(path)

    assert response.status_code == 404
    assert "error" in response.json


def test_polish_characters_are_not_escaped(client):
    response = client.get("/api/products?page=1&limit=56")

    assert "zł" in response.get_data(as_text=True)


def test_index_page_is_served_without_products(client):
    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '<section class="catalog"' in html
    assert "data-id" not in html
    assert CATALOG[0]["name"] not in html


def test_product_page_is_served_without_product_data(client):
    response = client.get("/product.html?id=1")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'class="product product-details"' in html
    assert CATALOG[0]["name"] not in html
    assert CATALOG[0]["cpu"] not in html


@pytest.mark.parametrize(
    "path",
    [
        "/js/catalog.js",
        "/js/product.js",
        "/js/api.js",
        "/js/product-view.js",
        "/css/styles.css",
    ],
)
def test_page_assets_are_served(client, path):
    assert client.get(path).status_code == 200
