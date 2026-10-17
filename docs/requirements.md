# Wymagania — poziom 5.0

Kontrakt projektu. Każdy punkt odhaczamy dopiero z dowodem (test, komenda albo zrzut).

## Sklep (AUTOR) — `shop/`

### Obowiązkowe

- [x] min. 400 rekordów — 438 unikalnych + 10 duplikatów = 448 wpisów (`test_catalog_spreads_duplicates_across_pages`)
- [x] min. 22 atrybuty — 24: 12 na liście, 6 w szczegółach, 6 w specyfikacji (`test_every_product_has_all_attributes`)
- [x] paginacja — 8 podstron po 56 wpisów (`test_chunks_from_all_pages_cover_the_whole_catalog`)
- [x] strona szczegółów `product.html?id=` z 12 dodatkowymi atrybutami (`test_product_details_exclude_specs`, `test_product_specs_contain_only_spec_fields`)
- [x] dwie struktury: tabela (podstrony nieparzyste) i karty `article` (parzyste) — `catalog.js`
- [x] semantyczne klasy i atrybuty (`product`, `price`, `data-id`, `data-currency`), bez generowanych nazw
- [x] rekordy w pliku JSON, wstawiane przez `fetch` — w źródle HTML brak rekordów (`test_index_page_is_served_without_products`, `test_product_page_is_served_without_product_data`)
- [x] doładowywanie porcjami po 14 przy przewijaniu (`IntersectionObserver` w `catalog.js`)
- [x] sztuczne opóźnienie 300–2000 ms przy każdej porcji (`test_chunk_response_is_delayed_by_configured_range`)

### Utrudnienia z 4.0 (min. 3 — wybrane 4)

- [x] ceny jako „1 299,00 zł”, 16% w EUR/USD (`test_prices_are_text_in_several_currencies`)
- [x] braki w `rating` i `warranty_months` u ok. 22% rekordów (`test_two_fields_have_missing_values`)
- [x] 10 duplikatów, każdy na innej podstronie niż oryginał (`test_catalog_spreads_duplicates_across_pages`)
- [x] niespójne formaty dat: `2026-08-26`, `26.08.2026`, „wczoraj” (`test_dates_use_inconsistent_formats`)

### Utrudnienia z 5.0 (min. 2)

- [x] własny serwer Flask zwracający 429 z nagłówkiem `Retry-After` (`test_api_returns_429_with_retry_after_when_limit_is_exceeded`, `test_rate_limit.py`)
- [x] atrybuty widoczne dopiero po interakcji — zakładka „Specyfikacja” pobierana z `/specs` po kliknięciu (`product.js`)

## Scraper (PARSER) — `scraper/`

### Obowiązkowe

- [x] Selenium — Chrome 155, Selenium 4.51 (`selenium_source.py`, `browser.py`)
- [x] jawne oczekiwanie — `WebDriverWait` z warunkami (`listing.py`, `details.py`); `sleep` tylko w odstępie między żądaniami (`throttle.py`) i w ponawianiu (`retry.py`)
- [x] doładowywanie aż do wyczerpania rekordów, na wszystkich podstronach — 8 × 56 = 448 wierszy (`load_remaining_chunks`)
- [x] wejście w szczegóły i połączenie danych z listy i szczegółów — 438/438, 0 różnic lista vs strona produktu (`dataset.py`)
- [x] ponawianie z opóźnieniem wykładniczym (1 s, 2 s, 4 s…) i limitem prób (`test_retry.py`)
- [x] czyszczenie: ceny jako liczby, ujednolicone formaty, usunięte duplikaty — 448 → 438 (`test_cleaning.py`, `test_dataset.py`)
- [x] brak danych jako pusta wartość, nie wyjątek — `rating` 98, `warranty_months` 96 pustych komórek
- [x] opóźnienie min. 0,5 s między żądaniami — domyślnie 0,6 s (`--delay`)
- [x] zapis do CSV/XLSX w UTF-8, poprawne polskie znaki — `laptops.csv` (UTF-8 z BOM), `laptops.xlsx`
- [x] weryfikacja z `shop/data/products.json`: 438 produktów × 22 pola, 0 różnic

### Rozszerzenia z 5.0 (min. 2 — zrobione 5)

- [x] obsługa 429 z poszanowaniem `Retry-After` — kod i nagłówek z logu sieciowego Chrome; test `--delay 0`: 19 × 429, 40/40 produktów
- [x] wykrycie i wykorzystanie źródła danych strony (JSON) — `--mode api` (`api_scraper.py`), ten sam zbiór co Selenium
- [x] tryb headless z pomiarem czasu w obu trybach (`benchmark.py`)
- [x] porównanie czasu i pamięci: bez przeglądarki vs Selenium na tym samym podzbiorze (`benchmark.py`)
- [x] wznawianie od punktu kontrolnego (`--resume`, `checkpoint.py`)

### Rozszerzenia z 4.0 (dodatkowo)

- [x] walidacja typów i zakresów wszystkich kolumn z raportem odrzuconych wartości (`laptops_summary.json`)
- [x] eksport do dwóch formatów (CSV i XLSX)
- [x] log przebiegu do pliku z podsumowaniem (`output/scraper.log`)
- [x] testy jednostkowe funkcji czyszczących (`tests/`, ponad 90 testów)
- [x] parametryzacja z linii poleceń (`python -m scraper --help`)

## Analiza danych — `scraper/notebooks/analysis.ipynb`

- [x] liczba rekordów i braki w każdej kolumnie (sztuki i %)
- [x] duplikaty przed i po odrzuceniu
- [x] typy kolumn — liczbowe są liczbowe
- [x] wartości odstające z interpretacją (anomalia czy błąd parsera)
- [x] wniosek o poprawności parsera i wprowadzone poprawki
- [x] średnia, mediana, moda, kwartyle, min, max
- [x] histogram
- [x] wykres pudełkowy
- [x] korelacja min. dwóch cech z komentarzem

## Sprawozdanie (PDF) — `report/`

- [ ] technologia i uzasadnienie wyboru
- [ ] opis sklepu: struktura, generowanie, utrudnienia i powód wyboru
- [ ] opis scrapera: rozszerzenia, selektory i uzasadnienie
- [ ] odporność selektorów na zmianę wyglądu
- [ ] wyniki kontroli jakości danych
- [ ] statystyki i wnioski
- [ ] porównanie surowego HTML z drzewem DOM — konkretne liczby i wniosek (dane gotowe: `python -m scraper.raw_vs_dom`, 0 vs 448)

## Oddanie

- [ ] archiwum `LAB1_Nazwisko_Imie_Nazwisko_Imie.zip` na platformie Delta
- [ ] odpowiedź ustna
