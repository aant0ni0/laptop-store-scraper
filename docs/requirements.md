# Wymagania — poziom 5.0

Kontrakt projektu. Każdy punkt odhaczamy dopiero z dowodem (test, komenda albo zrzut).

## Sklep (AUTOR) — `shop/`

### Obowiązkowe

- [ ] min. 400 rekordów (plan: 438 unikalnych + 10 duplikatów = 448 wpisów)
- [ ] min. 22 atrybuty (plan: 24 — 12 na liście, 12 na stronie szczegółów)
- [ ] paginacja — min. 5 podstron (plan: 8 po 56 wpisów)
- [ ] strona szczegółów dla każdego rekordu z min. 8 dodatkowymi atrybutami
- [ ] dwie struktury: tabela (podstrony nieparzyste) i karty `article` (parzyste)
- [ ] semantyczne klasy i atrybuty (`product`, `price`, `data-id`), bez generowanych nazw
- [ ] rekordy w pliku JSON, wstawiane przez `fetch` — w źródle HTML (Ctrl+U) brak rekordów
- [ ] doładowywanie porcjami przy przewijaniu strony (infinite scroll)
- [ ] sztuczne opóźnienie 300–2000 ms przy każdej porcji

### Utrudnienia z 4.0 (min. 3 — wybrane 4)

- [ ] ceny jako „1 299,00 zł”, część w EUR/USD
- [ ] braki w dwóch polach (`rating`, `warranty_months`) u min. 15% rekordów
- [ ] min. 8 duplikatów rozrzuconych po różnych podstronach (plan: 10)
- [ ] niespójne formaty dat: `2026-08-26`, `26.08.2026`, „wczoraj”

### Utrudnienia z 5.0 (min. 2)

- [ ] własny serwer Flask zwracający 429 z nagłówkiem `Retry-After`
- [ ] atrybuty widoczne dopiero po interakcji — zakładka „Specyfikacja” ładowana po kliknięciu

## Scraper (PARSER) — `scraper/`

### Obowiązkowe

- [ ] Selenium
- [ ] jawne oczekiwanie — `WebDriverWait` z warunkiem, bez sztywnego `sleep`
- [ ] doładowywanie aż do wyczerpania rekordów, na wszystkich podstronach
- [ ] wejście w szczegóły i połączenie danych z listy i szczegółów
- [ ] ponawianie z opóźnieniem wykładniczym (1 s, 2 s, 4 s…) i limitem prób
- [ ] czyszczenie: ceny jako liczby, ujednolicone formaty, usunięte duplikaty
- [ ] brak danych jako pusta wartość, nie wyjątek
- [ ] opóźnienie min. 0,5 s między żądaniami
- [ ] zapis do CSV/XLSX w UTF-8, poprawne polskie znaki

### Rozszerzenia z 5.0 (min. 2)

- [ ] obsługa 429 z poszanowaniem `Retry-After`
- [ ] wykrycie i wykorzystanie źródła danych strony (JSON) + omówienie, dlaczego szybsze

## Analiza danych

- [ ] liczba rekordów i braki w każdej kolumnie (sztuki i %)
- [ ] duplikaty przed i po odrzuceniu
- [ ] typy kolumn — liczbowe są liczbowe
- [ ] wartości odstające z interpretacją (anomalia czy błąd parsera)
- [ ] wniosek o poprawności parsera i wprowadzone poprawki
- [ ] średnia, mediana, moda, kwartyle, min, max
- [ ] histogram
- [ ] wykres pudełkowy
- [ ] korelacja min. dwóch cech z komentarzem

## Sprawozdanie (PDF) — `report/`

- [ ] technologia i uzasadnienie wyboru
- [ ] opis sklepu: struktura, generowanie, utrudnienia i powód wyboru
- [ ] opis scrapera: rozszerzenia, selektory i uzasadnienie
- [ ] odporność selektorów na zmianę wyglądu
- [ ] wyniki kontroli jakości danych
- [ ] statystyki i wnioski
- [ ] porównanie surowego HTML z drzewem DOM — konkretne liczby i wniosek

## Oddanie

- [ ] archiwum `LAB1_Nazwisko_Imie_Nazwisko_Imie.zip` na platformie Delta
- [ ] odpowiedź ustna
