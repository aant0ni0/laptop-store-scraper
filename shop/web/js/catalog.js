import { fetchJson } from "./api.js";
import { LISTING_ATTRIBUTES, attributeList, cssClass, displayValue, element } from "./product-view.js";

const CHUNK_SIZE = 14;

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
    if (pagination.childElementCount === 0) {
      renderPagination(chunk.page_count);
    }
    if (chunk.has_more) {
      watchLoadTrigger();
    } else {
      loadTriggerObserver.disconnect();
    }
  } catch (error) {
    loadTriggerObserver.disconnect();
    if (error.status === 400) {
      showInvalidPageMessage();
    } else {
      showLoadError();
    }
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

function showInvalidPageMessage() {
  const firstPageLink = element("a", null, "Przejdź do strony 1");
  firstPageLink.href = "/?page=1";
  statusMessage.replaceChildren("Nieprawidłowy numer strony. ", firstPageLink);
}

function hideLoadError() {
  statusMessage.textContent = "";
  retryButton.hidden = true;
}

function fetchChunk(offset) {
  const query = new URLSearchParams({ page, offset, limit: CHUNK_SIZE });
  return fetchJson(`/api/products?${query}`);
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

  card.append(
    name,
    element("p", "price", product.price),
    attributeList(product, LISTING_ATTRIBUTES),
  );
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
