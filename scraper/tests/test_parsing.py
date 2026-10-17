from scraper.parsing import count_products, parse_catalog, parse_product_details

TABLE_PAGE = """
<main class="page"><section class="catalog"><table class="product-table">
  <thead><tr><th>Nazwa</th><th>Cena</th><th>Kategoria</th></tr></thead>
  <tbody>
    <tr class="product" data-id="7" data-currency="PLN">
      <td class="product-name">
        <a class="product-link" href="/product.html?id=7">Lenovo Legion 5</a>
      </td>
      <td class="price">4 199,00 zł</td><td class="category">Gamingowy</td>
      <td class="brand">Lenovo</td><td class="availability">Ostatnie sztuki</td>
      <td class="rating">—</td><td class="review-count">12</td>
      <td class="date-added">wczoraj</td><td class="warranty-months">24 mies.</td>
    </tr>
  </tbody>
</table></section></main>
"""

CARD_PAGE = """
<main class="page"><section class="catalog"><div class="product-grid">
  <article class="product product-card" data-id="8" data-currency="USD">
    <h2 class="product-name">
      <a class="product-link" href="/product.html?id=8">HP EliteBook 840</a>
    </h2>
    <p class="price">$1,239.99</p>
    <dl class="product-attributes">
      <dt>Gwarancja</dt><dd class="warranty-months">—</dd>
      <dt>Kategoria</dt><dd class="category">Biznesowy</dd>
      <dt>Producent</dt><dd class="brand">HP</dd>
      <dt>Ocena</dt><dd class="rating">4.6</dd>
    </dl>
  </article>
</div></section></main>
"""

DETAILS_PAGE = """
<main class="page product-page"><p class="status" role="status"></p>
<article class="product product-details" data-id="8" data-currency="USD">
  <h1 class="product-name">HP EliteBook 840</h1><p class="price">$1,239.99</p>
  <div class="tab-panels">
    <section class="tab-panel" id="panel-overview"><dl class="product-attributes">
      <dt>Kategoria</dt><dd class="category">Biznesowy</dd>
      <dt>Przekątna ekranu</dt><dd class="screen-size-in">14"</dd>
      <dt>Waga</dt><dd class="weight-kg">1.36 kg</dd>
      <dt>Rok premiery</dt><dd class="release-year">2025</dd>
    </dl></section>
    <section class="tab-panel" id="panel-specs"><dl class="product-attributes">
      <dt>Procesor</dt><dd class="cpu">Intel Core i5-1335U</dd>
      <dt>Pamięć RAM</dt><dd class="ram-gb">16 GB</dd>
      <dt>Bateria</dt><dd class="battery-wh">56 Wh</dd>
    </dl></section>
  </div>
</article></main>
"""


def test_table_rows_are_parsed_by_field_class():
    [row] = parse_catalog(TABLE_PAGE, page=1)
    assert row == {
        "id": "7",
        "name": "Lenovo Legion 5",
        "url": "/product.html?id=7",
        "price": "4 199,00 zł",
        "currency": "PLN",
        "category": "Gamingowy",
        "brand": "Lenovo",
        "availability": "Ostatnie sztuki",
        "rating": "—",
        "review_count": "12",
        "date_added": "wczoraj",
        "warranty_months": "24 mies.",
        "source_page": 1,
        "layout": "table",
    }


def test_cards_use_the_same_selectors_regardless_of_attribute_order():
    [row] = parse_catalog(CARD_PAGE, page=2)
    assert row["layout"] == "card"
    assert row["id"] == "8"
    assert row["currency"] == "USD"
    assert row["price"] == "$1,239.99"
    assert row["category"] == "Biznesowy"
    assert row["warranty_months"] == "—"
    assert row["rating"] == "4.6"


def test_missing_fields_become_none_instead_of_raising():
    [row] = parse_catalog(CARD_PAGE, page=2)
    assert row["availability"] is None
    assert row["date_added"] is None


def test_product_details_combine_overview_and_specs_panels():
    details = parse_product_details(DETAILS_PAGE)
    assert details["id"] == "8"
    assert details["screen_size_in"] == '14"'
    assert details["weight_kg"] == "1.36 kg"
    assert details["release_year"] == "2025"
    assert details["cpu"] == "Intel Core i5-1335U"
    assert details["ram_gb"] == "16 GB"
    assert details["gpu"] is None


def test_page_without_product_details_gives_empty_result():
    assert parse_product_details("<main><p class='status'>Nie znaleziono</p></main>") == {}


def test_count_products_counts_both_layouts():
    assert count_products(TABLE_PAGE) == 1
    assert count_products(CARD_PAGE) == 1
    assert count_products("<section class='catalog'></section>") == 0
