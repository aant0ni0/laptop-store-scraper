# Laptop Store Scraper

Dynamiczny sklep z laptopami renderowany JavaScriptem oraz scraper w Selenium z czyszczeniem i analizą danych.

Projekt pary na Laboratorium nr 1 — parser strony www (poziom 5.0).

- **AUTOR** buduje sklep z laptopami (`shop/`), którego produkty są wstrzykiwane JavaScriptem.
- **PARSER** pisze scraper w Selenium (`scraper/`), który pobiera, czyści i analizuje dane.

Lista wymagań z dowodami realizacji: [docs/requirements.md](docs/requirements.md).

## Struktura

```
laptop-store-scraper/
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
- Google Chrome — dla scrapera w Selenium.

## Szybki start

```bash
make setup     # instalacja zależności (raz)
make shop      # terminal 1: sklep na http://localhost:8000
make demo      # terminal 2: scraper z widocznym oknem Chrome (1 podstrona, 3 produkty)
```

Wszystkie skróty: `make help` (pełny przebieg, tryb API, porównanie HTML vs DOM, benchmark, testy, lint). Pełne komendy są opisane niżej.

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

## Scraper

Wymaga działającego sklepu (patrz wyżej) i zainstalowanego Chrome — sterownik pobiera Selenium Manager.

### Uruchomienie

```bash
cd scraper
uv run python -m scraper                      # pełny przebieg w Selenium (headless), ok. 10 min
uv run python -m scraper --mode api           # ten sam zbiór z API JSON, bez przeglądarki
uv run python -m scraper --resume             # dokończenie przerwanego przebiegu (Ctrl+C)
uv run python -m scraper --pages 1 --limit 20 --no-headless   # szybki podgląd z oknem przeglądarki
```

Pełny przebieg trwa ok. 10 minut, bo limit sklepu to 20 zapytań na 10 s, a scraper robi ok. 900 zapytań do API (porcje katalogu, szczegóły i specyfikacja każdego produktu).

| Parametr | Domyślnie | Znaczenie |
|---|---|---|
| `--base-url` | `http://127.0.0.1:8000` | adres sklepu (`127.0.0.1`, bo na Windows `localhost` dokłada ~2 s do każdego połączenia `requests`) |
| `--mode` | `selenium` | `selenium` — strona renderowana w Chrome; `api` — bezpośrednio `/api/*` |
| `--pages`, `--limit` | wszystkie | maks. liczba podstron katalogu / produktów, których szczegóły są pobierane |
| `--output` | `output/laptops` | ścieżka bez rozszerzenia |
| `--delay` | `0.6` | odstęp między zapytaniami w sekundach (wymagane min. 0,5 s) |
| `--headless / --no-headless` | headless | Chrome bez okna lub z oknem |
| `--resume` | — | wznowienie od `output/checkpoint_<mode>.json` |
| `--max-attempts`, `--timeout` | `5`, `15` | limit prób ponawiania (1 s, 2 s, 4 s…) i czas oczekiwania na element |

### Wyniki (`scraper/output/`)

| Plik | Zawartość |
|---|---|
| `laptops.csv`, `laptops.xlsx` | oczyszczone dane: 1 wiersz = 1 laptop, bez duplikatów, ceny jako liczby, `price_pln` przeliczone kursem NBP |
| `laptops_raw.csv` | surowe teksty ze strony, z duplikatami — do kontroli jakości |
| `laptops_summary.json` | podsumowanie: czas, liczba stron, rekordów, duplikatów, błędów, odpowiedzi 429, odrzuconych wartości |
| `scraper.log` | log przebiegu |

### Narzędzia do sprawozdania

```bash
uv run python -m scraper.raw_vs_dom          # rekordy w surowym HTML vs w DOM po wykonaniu skryptów
uv run python -m scraper.benchmark           # czas i pamięć: API vs Selenium headless vs z oknem
uv run python -m scraper --mode api --delay 0 --pages 1 --limit 40 --output output/http429   # wymuszenie 429
```

Analiza danych: `notebooks/analysis.ipynb` (wykresy zapisuje do `report/figures/`).

### Testy

```bash
cd scraper
uv run pytest
```

## Konwencje

- Kod, nazwy plików i klasy CSS po angielsku; treść strony po polsku.
- Gałąź na każdą zmianę (`feat/...`, `fix/...`), merge przez Pull Request.
- Commity w stylu [Conventional Commits](https://www.conventionalcommits.org/).
- Przed commitem: `uv run ruff check . && uv run ruff format . && uv run pytest`.
