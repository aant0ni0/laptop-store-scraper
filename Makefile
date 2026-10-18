.PHONY: help setup shop demo scrape scrape-api raw-vs-dom benchmark test lint

help:
	@echo "make setup       install dependencies of the shop and the scraper"
	@echo "make shop        start the shop at http://localhost:8000 (keep it running)"
	@echo "make demo        scrape 1 page and 3 products with a visible Chrome window"
	@echo "make scrape      full Selenium run (about 10 minutes)"
	@echo "make scrape-api  full run through the JSON API, without a browser"
	@echo "make raw-vs-dom  count products in raw HTML vs the rendered DOM"
	@echo "make benchmark   compare time and memory: API vs Selenium"
	@echo "make test        run all tests"
	@echo "make lint        check code style"

setup:
	uv sync --directory shop
	uv sync --directory scraper

shop:
	uv run --directory shop flask --app shop.app run --port 8000

demo:
	uv run --directory scraper python -m scraper --pages 1 --limit 3 --no-headless

scrape:
	uv run --directory scraper python -m scraper

scrape-api:
	uv run --directory scraper python -m scraper --mode api --output output/laptops_api

raw-vs-dom:
	uv run --directory scraper python -m scraper.raw_vs_dom

benchmark:
	uv run --directory scraper python -m scraper.benchmark

test:
	uv run --directory shop pytest
	uv run --directory scraper pytest

lint:
	uv run --directory shop ruff check .
	uv run --directory scraper ruff check .
