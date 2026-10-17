"""Time and memory of the same subset scraped through the API, headless Chrome and visible Chrome.

uv run python -m scraper.benchmark [--products 30] [--variants api headless headed]
"""

import argparse
import logging
import sys
import threading
import time

import pandas as pd
import psutil

from scraper import config
from scraper.pipeline import Settings, run

logger = logging.getLogger(__name__)

VARIANTS = {
    "api": {"mode": "api", "headless": True},
    "headless": {"mode": "selenium", "headless": True},
    "headed": {"mode": "selenium", "headless": False},
}


def process_tree_rss() -> int:
    process = psutil.Process()
    total = process.memory_info().rss
    for child in process.children(recursive=True):
        try:
            total += child.memory_info().rss
        except psutil.Error:
            continue
    return total


class PeakMemory:
    """Samples the resident memory of this process plus chromedriver and Chrome children."""

    def __init__(self, interval_seconds: float = 0.2) -> None:
        self.interval_seconds = interval_seconds
        self.peak_bytes = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def __enter__(self) -> "PeakMemory":
        self._thread.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._stop.set()
        self._thread.join()

    def _sample(self) -> None:
        while not self._stop.is_set():
            self.peak_bytes = max(self.peak_bytes, process_tree_rss())
            self._stop.wait(self.interval_seconds)


def measure(variant: str, products: int, base_url: str, delay: float) -> dict:
    settings = Settings(
        base_url=base_url,
        max_pages=1,
        max_products=products,
        output=config.OUTPUT_DIR / "benchmark" / variant,
        delay_seconds=delay,
        **VARIANTS[variant],
    )
    started = time.perf_counter()
    with PeakMemory() as memory:
        summary = run(settings)
    duration = time.perf_counter() - started
    return {
        "variant": variant,
        "products": summary.cleaning.unique_products,
        "duration_s": round(duration, 1),
        "throttle_wait_s": summary.throttle_wait_seconds,
        "active_s": round(duration - summary.throttle_wait_seconds, 1),
        "peak_memory_mb": round(memory.peak_bytes / 2**20, 1),
        "api_responses": summary.source_stats["api_responses"],
        "http_429": summary.source_stats["http_429_responses"],
    }


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="python -m scraper.benchmark")
    parser.add_argument("--base-url", default=config.DEFAULT_BASE_URL)
    parser.add_argument("--products", type=int, default=30)
    parser.add_argument("--delay", type=float, default=config.REQUEST_DELAY_SECONDS)
    parser.add_argument("--variants", nargs="+", choices=list(VARIANTS), default=list(VARIANTS))
    parser.add_argument("--output", default=str(config.OUTPUT_DIR / "benchmark.csv"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")

    results = []
    for variant in args.variants:
        print(f"measuring {variant}...", flush=True)
        results.append(measure(variant, args.products, args.base_url, args.delay))
    table = pd.DataFrame(results)
    table.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(table.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
