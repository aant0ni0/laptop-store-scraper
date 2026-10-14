import json

import pytest

from shop.app import LISTING_FIELDS, SPEC_FIELDS, create_app
from shop.catalog import DATA_PATH, PAGE_COUNT, PAGE_SIZE

CATALOG = json.loads(DATA_PATH.read_text("utf-8"))


@pytest.fixture
def client():
    return create_app().test_client()


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
