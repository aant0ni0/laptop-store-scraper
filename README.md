# Laptop Store Scraper

Dynamiczny sklep z laptopami renderowany JavaScriptem oraz scraper w Selenium z czyszczeniem i analizą danych.

Projekt pary na Laboratorium nr 1 — parser strony www (poziom 5.0).

- **AUTOR** buduje sklep z laptopami (`shop/`), którego produkty są wstrzykiwane JavaScriptem.
- **PARSER** pisze scraper w Selenium (`scraper/`), który pobiera, czyści i analizuje dane.

Pełna lista wymagań: [docs/requirements.md](docs/requirements.md).

## Struktura

```
laptop-store-scraper/
├── docs/          # wymagania i dokumentacja projektu
├── shop/          # AUTOR — Flask + HTML/CSS/JS
│   ├── scripts/   # generator danych
│   ├── data/      # products.json
│   ├── src/shop/  # serwer i API
│   ├── tests/
│   └── web/       # strony, style, skrypty
├── scraper/       # PARSER — Selenium + pandas
│   ├── src/scraper/
│   ├── tests/
│   ├── notebooks/ # analiza danych
│   └── output/    # wyniki (poza repo)
└── report/        # sprawozdanie PDF
```

## Wymagania

- [uv](https://docs.astral.sh/uv/) — instaluje właściwą wersję Pythona (3.12) i zależności.

```bash
cd shop && uv sync
cd scraper && uv sync
```

Instrukcje uruchomienia sklepu i scrapera zostaną dodane wraz z implementacją.

## Konwencje

- Kod, nazwy plików i klasy CSS po angielsku; treść strony po polsku.
- Gałąź na każdą zmianę (`feat/...`, `fix/...`), merge przez Pull Request.
- Commity w stylu [Conventional Commits](https://www.conventionalcommits.org/).
- Przed commitem: `uv run ruff check . && uv run ruff format . && uv run pytest`.
