import pytest

from scraper.checkpoint import Checkpoint
from scraper.errors import PageLoadError, ProductNotFoundError
from scraper.pipeline import MAX_CONSECUTIVE_FAILURES, collect


class FakeSource:
    name = "fake"

    def __init__(self, pages, missing=(), broken=()):
        self.pages = pages
        self.missing = set(missing)
        self.broken = set(broken)
        self.page_calls = []
        self.product_calls = []

    def catalog_page(self, page):
        self.page_calls.append(page)
        return [{"id": str(product_id), "source_page": page} for product_id in self.pages[page]]

    def page_count(self):
        return len(self.pages)

    def product(self, product_id):
        self.product_calls.append(product_id)
        if product_id in self.missing:
            raise ProductNotFoundError("not found")
        if product_id in self.broken:
            raise PageLoadError("broken")
        return {"cpu": f"cpu-{product_id}"}

    def stats(self):
        return {}

    def close(self):
        pass


PAGES = {1: [1, 2], 2: [3, 1], 3: [4, 5]}


def test_collect_visits_every_page_and_each_unique_product_once(tmp_path):
    source = FakeSource(PAGES)
    rows, details, stats = collect(
        source, Checkpoint(tmp_path / "cp.json"), max_pages=None, max_products=None
    )
    assert source.page_calls == [1, 2, 3]
    assert len(rows) == 6
    assert source.product_calls == [1, 2, 3, 4, 5]
    assert details[4] == {"cpu": "cpu-4"}
    assert stats.products_scraped == 5


def test_collect_respects_page_and_product_limits(tmp_path):
    source = FakeSource(PAGES)
    rows, details, _ = collect(
        source, Checkpoint(tmp_path / "cp.json"), max_pages=2, max_products=2
    )
    assert source.page_calls == [1, 2]
    assert sorted(details) == [1, 2]
    assert [row["id"] for row in rows] == ["1", "2", "1"]


def test_failed_products_are_recorded_and_do_not_stop_the_run(tmp_path):
    source = FakeSource(PAGES, missing={2}, broken={4})
    _, details, stats = collect(
        source, Checkpoint(tmp_path / "cp.json"), max_pages=None, max_products=None
    )
    assert set(stats.failed_products) == {2, 4}
    assert details[2] is None
    assert details[5] == {"cpu": "cpu-5"}


def test_too_many_failures_in_a_row_stop_the_run(tmp_path):
    product_ids = list(range(1, MAX_CONSECUTIVE_FAILURES + 3))
    source = FakeSource({1: product_ids}, broken=product_ids)
    with pytest.raises(PageLoadError):
        collect(source, Checkpoint(tmp_path / "cp.json"), max_pages=None, max_products=None)
    assert len(source.product_calls) == MAX_CONSECUTIVE_FAILURES


def test_resume_skips_pages_and_products_saved_in_the_checkpoint(tmp_path):
    path = tmp_path / "cp.json"
    first = FakeSource(PAGES, broken={5})
    collect(first, Checkpoint(path), max_pages=None, max_products=None)

    second = FakeSource(PAGES)
    _, details, stats = collect(second, Checkpoint.load(path), max_pages=None, max_products=None)
    assert second.page_calls == []
    assert second.product_calls == [5]
    assert stats.pages_restored == 3
    assert stats.products_restored == 4
    assert details[5] == {"cpu": "cpu-5"}


def test_checkpoint_round_trips_polish_text(tmp_path):
    path = tmp_path / "cp.json"
    checkpoint = Checkpoint(path, page_count=8)
    checkpoint.catalog_pages[1] = [{"id": "1", "category": "Budżetowy"}]
    checkpoint.details[1] = {"availability": "Dostępny"}
    checkpoint.save()

    loaded = Checkpoint.load(path)
    assert loaded.page_count == 8
    assert loaded.catalog_pages == {1: [{"id": "1", "category": "Budżetowy"}]}
    assert loaded.details == {1: {"availability": "Dostępny"}}
