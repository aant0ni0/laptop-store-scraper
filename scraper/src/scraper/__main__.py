import argparse
import logging
import sys
from pathlib import Path

from scraper import config
from scraper.pipeline import Settings, run

logger = logging.getLogger("scraper")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m scraper",
        description="Scrape the Laptop Store catalog into CSV and XLSX.",
    )
    parser.add_argument("--base-url", default=config.DEFAULT_BASE_URL, help="shop address")
    parser.add_argument(
        "--mode",
        choices=("selenium", "api"),
        default="selenium",
        help="selenium renders the pages; api reads the JSON the pages are built from",
    )
    parser.add_argument("--pages", type=int, help="scrape at most this many catalog pages")
    parser.add_argument("--limit", type=int, help="scrape details of at most this many products")
    parser.add_argument(
        "--output",
        type=Path,
        default=config.DEFAULT_OUTPUT,
        help="output path without extension; .csv, .xlsx and _raw.csv are written",
    )
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="run Chrome without a window (default: yes)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=config.REQUEST_DELAY_SECONDS,
        help=f"seconds between requests (default {config.REQUEST_DELAY_SECONDS})",
    )
    parser.add_argument("--resume", action="store_true", help="continue from the checkpoint")
    parser.add_argument("--timeout", type=float, default=config.WAIT_TIMEOUT_SECONDS)
    parser.add_argument("--max-attempts", type=int, default=config.MAX_ATTEMPTS)
    parser.add_argument("--log-file", type=Path, default=config.OUTPUT_DIR / "scraper.log")
    parser.add_argument("-v", "--verbose", action="store_true", help="log debug messages")
    return parser.parse_args(argv)


def configure_logging(log_file: Path, verbose: bool) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    console_handler = logging.StreamHandler()
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    for handler in (file_handler, console_handler):
        handler.setFormatter(formatter)
        root.addHandler(handler)
    for noisy in ("selenium", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    configure_logging(args.log_file, args.verbose)
    if args.delay < config.MIN_REQUEST_DELAY_SECONDS:
        logger.warning(
            "delay %.2f s is below the required %.1f s; use it only to test HTTP 429 handling",
            args.delay,
            config.MIN_REQUEST_DELAY_SECONDS,
        )
    settings = Settings(
        base_url=args.base_url,
        mode=args.mode,
        max_pages=args.pages,
        max_products=args.limit,
        output=args.output,
        headless=args.headless,
        delay_seconds=args.delay,
        resume=args.resume,
        timeout_seconds=args.timeout,
        max_attempts=args.max_attempts,
    )
    try:
        run(settings)
    except KeyboardInterrupt:
        logger.warning("interrupted; progress saved, continue with --resume")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
