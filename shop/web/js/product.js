import { fetchJson, requestErrorMessage } from "./api.js";
import {
  DETAIL_ATTRIBUTES,
  LISTING_ATTRIBUTES,
  SPEC_ATTRIBUTES,
  attributeList,
  element,
} from "./product-view.js";

const productId = new URLSearchParams(location.search).get("id");
const details = document.querySelector(".product-details");
const statusMessage = document.querySelector(".status");
const overviewTab = document.querySelector("#tab-overview");
const specsTab = document.querySelector("#tab-specs");
const overviewPanel = document.querySelector("#panel-overview");
const specsPanel = document.querySelector("#panel-specs");

let specsRequest = null;

overviewTab.addEventListener("click", () => selectTab(overviewTab));
specsTab.addEventListener("click", openSpecsTab);
loadProduct();

async function loadProduct() {
  if (!productId) {
    showNotFound();
    return;
  }
  try {
    renderProduct(await fetchJson(`/api/products/${encodeURIComponent(productId)}`));
  } catch (error) {
    if (error.status === 404) {
      showNotFound();
    } else {
      statusMessage.textContent = requestErrorMessage(
        error,
        "Nie udało się wczytać produktu. Odśwież stronę.",
      );
    }
  }
}

function renderProduct(product) {
  document.title = `${product.name} – Laptop Store`;
  details.dataset.id = product.id;
  details.dataset.currency = product.currency;
  details.querySelector(".product-name").textContent = product.name;
  details.querySelector(".price").textContent = product.price;
  overviewPanel.append(attributeList(product, [...LISTING_ATTRIBUTES, ...DETAIL_ATTRIBUTES]));
  details.hidden = false;
}

function openSpecsTab() {
  selectTab(specsTab);
  specsRequest ??= loadSpecs();
}

async function loadSpecs() {
  try {
    const specs = await fetchJson(`/api/products/${encodeURIComponent(productId)}/specs`);
    specsPanel.replaceChildren(attributeList(specs, SPEC_ATTRIBUTES));
  } catch (error) {
    const message = requestErrorMessage(
      error,
      "Nie udało się wczytać specyfikacji. Kliknij zakładkę ponownie.",
    );
    specsPanel.replaceChildren(element("p", "status", message));
    specsRequest = null;
  }
}

function selectTab(selectedTab) {
  for (const tab of [overviewTab, specsTab]) {
    const isSelected = tab === selectedTab;
    tab.setAttribute("aria-selected", String(isSelected));
    document.getElementById(tab.getAttribute("aria-controls")).hidden = !isSelected;
  }
}

function showNotFound() {
  const catalogLink = element("a", null, "Przejdź do katalogu");
  catalogLink.href = "/";
  statusMessage.replaceChildren("Nie znaleziono produktu. ", catalogLink);
}
