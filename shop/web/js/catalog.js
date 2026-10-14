const CHUNK_SIZE = 14;
const MISSING_VALUE = "—";

const LISTING_ATTRIBUTES = [
  { key: "category", label: "Kategoria" },
  { key: "brand", label: "Producent" },
  { key: "availability", label: "Dostępność" },
  { key: "rating", label: "Ocena" },
  { key: "review_count", label: "Liczba opinii" },
  { key: "date_added", label: "Data dodania" },
  { key: "warranty_months", label: "Gwarancja", format: (months) => `${months} mies.` },
];

const page = currentPageNumber();
const catalogSection = document.querySelector(".catalog");
const pagination = document.querySelector(".pagination");
const statusMessage = document.querySelector(".status");
const loadTrigger = document.querySelector(".load-trigger");
const retryButton = document.querySelector(".retry");

const productLayout = page % 2 === 1 ? createTableLayout() : createCardLayout();
const loadTriggerObserver = new IntersectionObserver(
  (entries) => {
    if (entries.some((entry) => entry.isIntersecting)) {
      loadNextChunk();
    }
  },
  { rootMargin: "0px 0px 300px 0px" },
);
let loadedCount = 0;
let isLoading = false;

retryButton.addEventListener("click", loadNextChunk);
watchLoadTrigger();

async function loadNextChunk() {
  if (isLoading) {
    return;
  }
  isLoading = true;
  hideLoadError();
  try {
    const chunk = await fetchChunk(loadedCount);
    for (const product of chunk.items) {
      productLayout.container.append(productLayout.renderProduct(product));
    }
    loadedCount += chunk.items.length;
    renderPagination(chunk.page_count);
    if (chunk.has_more) {
      watchLoadTrigger();
    } else {
      loadTriggerObserver.disconnect();
    }
  } catch {
    loadTriggerObserver.disconnect();
    showLoadError();
  } finally {
    isLoading = false;
  }
}

function watchLoadTrigger() {
  loadTriggerObserver.unobserve(loadTrigger);
  loadTriggerObserver.observe(loadTrigger);
}

function showLoadError() {
  statusMessage.textContent = "Nie udało się wczytać produktów.";
  retryButton.hidden = false;
}

function hideLoadError() {
  statusMessage.textContent = "";
  retryButton.hidden = true;
}

async function fetchChunk(offset) {
  const query = new URLSearchParams({ page, offset, limit: CHUNK_SIZE });
  const response = await fetch(`/api/products?${query}`);
  if (!response.ok) {
    throw new Error(`Catalog request failed with status ${response.status}`);
  }
  return response.json();
}

function currentPageNumber() {
  const requestedPage = Number.parseInt(new URLSearchParams(location.search).get("page"), 10);
  return Number.isNaN(requestedPage) ? 1 : requestedPage;
}

function createTableLayout() {
  const table = element("table", "product-table");
  const headerRow = element("tr");
  for (const label of ["Nazwa", "Cena", ...LISTING_ATTRIBUTES.map((attribute) => attribute.label)]) {
    headerRow.append(element("th", null, label));
  }
  const head = element("thead");
  head.append(headerRow);
  const body = element("tbody");
  table.append(head, body);
  catalogSection.append(table);
  return { container: body, renderProduct: productRow };
}

function createCardLayout() {
  const grid = element("div", "product-grid");
  catalogSection.append(grid);
  return { container: grid, renderProduct: productCard };
}

function productRow(product) {
  const row = productElement("tr", product);
  const nameCell = element("td", "product-name");
  nameCell.append(productLink(product));
  row.append(nameCell, element("td", "price", product.price));
  for (const attribute of LISTING_ATTRIBUTES) {
    row.append(element("td", cssClass(attribute), displayValue(product, attribute)));
  }
  return row;
}

function productCard(product) {
  const card = productElement("article", product);
  card.classList.add("product-card");
  const name = element("h2", "product-name");
  name.append(productLink(product));

  const attributes = element("dl", "product-attributes");
  for (const attribute of LISTING_ATTRIBUTES) {
    attributes.append(
      element("dt", null, attribute.label),
      element("dd", cssClass(attribute), displayValue(product, attribute)),
    );
  }
  card.append(name, element("p", "price", product.price), attributes);
  return card;
}

function productElement(tag, product) {
  const node = element(tag, "product");
  node.dataset.id = product.id;
  node.dataset.currency = product.currency;
  return node;
}

function productLink(product) {
  const link = element("a", "product-link", product.name);
  link.href = product.url;
  return link;
}

function renderPagination(pageCount) {
  const links = [];
  for (let pageNumber = 1; pageNumber <= pageCount; pageNumber++) {
    const link = element("a", "page-link", String(pageNumber));
    link.href = `/?page=${pageNumber}`;
    if (pageNumber === page) {
      link.setAttribute("aria-current", "page");
    }
    links.push(link);
  }
  pagination.replaceChildren(...links);
}

function displayValue(product, attribute) {
  const value = product[attribute.key];
  if (value === null || value === undefined) {
    return MISSING_VALUE;
  }
  return attribute.format ? attribute.format(value) : String(value);
}

function cssClass(attribute) {
  return attribute.key.replaceAll("_", "-");
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text !== undefined) {
    node.textContent = text;
  }
  return node;
}
