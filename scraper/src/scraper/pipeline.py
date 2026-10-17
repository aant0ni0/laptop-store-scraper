import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Protocol

from scraper import config
from scraper.checkpoint import Checkpoint
from scraper.cleaning import parse_int
from scraper.dataset import CleaningReport, build_dataset, export, raw_rows
from scraper.errors import ProductNotFoundError
from scraper.retry import RetryPolicy
from scraper.throttle import Throttle

logger = logging.getLogger(__name__)

MAX_CONSECUTIVE_FAILURES = 5


class ShopSource(Protocol):
    name: str

    def catalog_page(self, page: int) -> list[dict]: ...

    def page_count(self) -> int | None: ...

    def product(self, product_id: int) -> dict: ...

    def stats(self) -> dict: ...

    def close(self) -> None: ...


@dataclass(frozen=True)
class Settings:
    base_url: str = config.DEFAULT_BASE_URL
    mode: str = "selenium"
    max_pages: int | None = None
    max_products: int | None = None
    output: Path = config.DEFAULT_OUTPUT
    headless: bool = True
    delay_seconds: float = config.REQUEST_DELAY_SECONDS
    resume: bool = False
    timeout_seconds: float = config.WAIT_TIMEOUT_SECONDS
    max_attempts: int = config.MAX_ATTEMPTS

    @property
    def checkpoint_path(self) -> Path:
        return self.output.with_name(f"checkpoint_{self.mode}.json")

    @property
    def summary_path(self) -> Path:
        return self.output.with_name(f"{self.output.stem}_summary.json")


@dataclass
class CollectionStats:
    pages_scraped: int = 0
    pages_restored: int = 0
    products_scraped: int = 0
    products_restored: int = 0
    failed_products: dict[int, str] = field(default_factory=dict)


@dataclass
class RunSummary:
    mode: str
    base_url: str
    started_at: str
    duration_seconds: float
    page_count: int | None
    pages: int
    collection: CollectionStats
    cleaning: CleaningReport
    missing_values: dict[str, int]
    requests_sent: int
    throttle_wait_seconds: float
    source_stats: dict
    exchange_rates: dict[str, float]
    outputs: list[str]


def create_source(settings: Settings, throttle: Throttle) -> ShopSource:
    policy = RetryPolicy(
        max_attempts=settings.max_attempts,
        base_delay_seconds=config.RETRY_BASE_DELAY_SECONDS,
        max_delay_seconds=config.RETRY_MAX_DELAY_SECONDS,
    )
    if settings.mode == "api":
        from scraper.api_scraper import ApiSource

        return ApiSource(
            settings.base_url, throttle, policy, timeout_seconds=settings.timeout_seconds
        )
    from scraper.selenium_source import SeleniumSource

    return SeleniumSource(
        settings.base_url,
        throttle,
        policy,
        headless=settings.headless,
        timeout_seconds=settings.timeout_seconds,
        quiet_seconds=config.END_OF_LIST_QUIET_SECONDS,
    )


def collect(
    source: ShopSource,
    checkpoint: Checkpoint,
    *,
    max_pages: int | None,
    max_products: int | None,
) -> tuple[list[dict], dict[int, dict], CollectionStats]:
    stats = CollectionStats()
    page = 1
    while True:
        if page in checkpoint.catalog_pages:
            stats.pages_restored += 1
            logger.info("catalog page %d restored from checkpoint", page)
        else:
            checkpoint.catalog_pages[page] = source.catalog_page(page)
            checkpoint.page_count = source.page_count() or checkpoint.page_count
            checkpoint.save()
            stats.pages_scraped += 1
        last_page = checkpoint.page_count or page
        if max_pages is not None:
            last_page = min(last_page, max_pages)
        if page >= last_page:
            break
        page += 1

    listing_rows = [
        row
        for page_number in sorted(checkpoint.catalog_pages)
        if page_number <= last_page
        for row in checkpoint.catalog_pages[page_number]
    ]
    product_ids = list(dict.fromkeys(parse_int(row.get("id")) for row in listing_rows))
    product_ids = [product_id for product_id in product_ids if product_id is not None]
    if max_products is not None:
        product_ids = product_ids[:max_products]
        selected = set(product_ids)
        listing_rows = [row for row in listing_rows if parse_int(row.get("id")) in selected]

    consecutive_failures = 0
    for index, product_id in enumerate(product_ids, start=1):
        if product_id in checkpoint.details:
            stats.products_restored += 1
            continue
        try:
            checkpoint.details[product_id] = source.product(product_id)
        except ProductNotFoundError as error:
            stats.failed_products[product_id] = str(error)
            logger.warning("product %d skipped: %s", product_id, error)
            continue
        except Exception as error:
            stats.failed_products[product_id] = f"{type(error).__name__}: {error}"
            logger.error("product %d failed: %s", product_id, error)
            consecutive_failures += 1
            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                logger.critical("%d products in a row failed, stopping", consecutive_failures)
                raise
            continue
        consecutive_failures = 0
        stats.products_scraped += 1
        if index % config.CHECKPOINT_EVERY_PRODUCTS == 0:
            checkpoint.save()
            logger.info("products: %d/%d", index, len(product_ids))
    checkpoint.save()

    details_by_id = {product_id: checkpoint.details.get(product_id) for product_id in product_ids}
    return listing_rows, details_by_id, stats


def run(settings: Settings) -> RunSummary:
    started_at = datetime.now()
    started = time.perf_counter()
    logger.info("run started: %s", settings)

    throttle = Throttle(settings.delay_seconds)
    checkpoint = (
        Checkpoint.load(settings.checkpoint_path)
        if settings.resume
        else Checkpoint(settings.checkpoint_path)
    )
    source = create_source(settings, throttle)
    try:
        listing_rows, details_by_id, collection = collect(
            source,
            checkpoint,
            max_pages=settings.max_pages,
            max_products=settings.max_products,
        )
    finally:
        checkpoint.save()
        source_stats = source.stats()
        source.close()

    df, cleaning = build_dataset(
        listing_rows,
        details_by_id,
        base_url=settings.base_url,
        scraped_on=date.today(),
        rates=config.RATES_TO_PLN,
    )
    outputs = export(df, raw_rows(listing_rows, details_by_id), settings.output)

    summary = RunSummary(
        mode=settings.mode,
        base_url=settings.base_url,
        started_at=started_at.isoformat(timespec="seconds"),
        duration_seconds=round(time.perf_counter() - started, 1),
        page_count=checkpoint.page_count,
        pages=collection.pages_scraped + collection.pages_restored,
        collection=collection,
        cleaning=cleaning,
        missing_values={column: int(count) for column, count in df.isna().sum().items()},
        requests_sent=throttle.request_count,
        throttle_wait_seconds=round(throttle.waited_seconds, 1),
        source_stats=source_stats,
        exchange_rates=config.RATES_TO_PLN,
        outputs=[str(path) for path in outputs],
    )
    settings.summary_path.write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2), "utf-8"
    )
    log_summary(summary)
    return summary


def log_summary(summary: RunSummary) -> None:
    cleaning = summary.cleaning
    logger.info("=== summary (%s) ===", summary.mode)
    logger.info(
        "time: %.1f s, throttled requests (page loads, scrolls, clicks): %d",
        summary.duration_seconds,
        summary.requests_sent,
    )
    logger.info("pages: %d of %s", summary.pages, summary.page_count)
    logger.info(
        "rows: %d raw, %d duplicates removed, %d unique products",
        cleaning.raw_rows,
        cleaning.duplicate_rows,
        cleaning.unique_products,
    )
    logger.info(
        "details: %d scraped, %d from checkpoint, %d failed",
        summary.collection.products_scraped,
        summary.collection.products_restored,
        len(summary.collection.failed_products),
    )
    logger.info("source: %s", summary.source_stats)
    logger.info("rejected values: %s", cleaning.rejected_values or "none")
    logger.info("listing/details mismatches: %s", cleaning.listing_detail_mismatches or "none")
    logger.info("outputs: %s", ", ".join(summary.outputs))
