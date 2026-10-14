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
uv sync --directory shop
uv sync --directory scraper
```

## Sklep

### Uruchomienie

```bash
uv run --directory shop flask --app shop.app run --port 8000
```

Sklep działa pod adresem <http://localhost:8000>. Port 8000 zamiast domyślnego 5000, bo na macOS port 5000 zajmuje AirPlay Receiver.

### Strony

| Adres | Zawartość |
|---|---|
| `/?page=1` … `/?page=8` | katalog — produkty doładowywane porcjami przy przewijaniu |
| `/product.html?id=<id>` | szczegóły produktu; zakładka „Specyfikacja” ładowana po kliknięciu |

Produkty nie występują w źródle HTML — wstawia je JavaScript na podstawie API.

### API

| Endpoint | Zwraca |
|---|---|
| `GET /api/products?page=<1-8>&offset=<n>&limit=<1-56>` | porcja produktów z danej podstrony: `{page, page_count, total, has_more, items}`; domyślnie `offset=0`, `limit=14` |
| `GET /api/products/<id>` | szczegóły produktu (bez specyfikacji) |
| `GET /api/products/<id>/specs` | specyfikacja produktu |

Błędy mają postać `{"error": "..."}`:

- `400` — niepoprawne parametry,
- `404` — nieistniejący produkt,
- `429` — przekroczony limit: 20 zapytań do `/api/*` na 10 s z jednego adresu IP; nagłówek `Retry-After` podaje, po ilu sekundach ponowić.

### Dane i testy

```bash
cd shop
uv run python scripts/generate_data.py
uv run pytest
```

Generator jest deterministyczny (stały seed), a `data/products.json` jest w repozytorium — regeneracja jest potrzebna tylko po zmianie generatora. Test `test_saved_catalog_matches_generator` pilnuje, żeby plik był aktualny.

## Konwencje

- Kod, nazwy plików i klasy CSS po angielsku; treść strony po polsku.
- Gałąź na każdą zmianę (`feat/...`, `fix/...`), merge przez Pull Request.
- Commity w stylu [Conventional Commits](https://www.conventionalcommits.org/).
- Przed commitem: `uv run ruff check . && uv run ruff format . && uv run pytest`.
