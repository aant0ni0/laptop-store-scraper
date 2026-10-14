const MISSING_VALUE = "—";

export const LISTING_ATTRIBUTES = [
  { key: "category", label: "Kategoria" },
  { key: "brand", label: "Producent" },
  { key: "availability", label: "Dostępność" },
  { key: "rating", label: "Ocena" },
  { key: "review_count", label: "Liczba opinii" },
  { key: "date_added", label: "Data dodania" },
  { key: "warranty_months", label: "Gwarancja", format: (months) => `${months} mies.` },
];

export const DETAIL_ATTRIBUTES = [
  { key: "screen_size_in", label: "Przekątna ekranu", format: (inches) => `${inches}"` },
  { key: "resolution", label: "Rozdzielczość" },
  { key: "weight_kg", label: "Waga", format: (kilograms) => `${kilograms} kg` },
  { key: "os", label: "System operacyjny" },
  { key: "color", label: "Kolor" },
  { key: "release_year", label: "Rok premiery" },
];

export const SPEC_ATTRIBUTES = [
  { key: "cpu", label: "Procesor" },
  { key: "ram_gb", label: "Pamięć RAM", format: (gigabytes) => `${gigabytes} GB` },
  { key: "storage_gb", label: "Dysk", format: (gigabytes) => `${gigabytes} GB` },
  { key: "storage_type", label: "Typ dysku" },
  { key: "gpu", label: "Karta graficzna" },
  { key: "battery_wh", label: "Bateria", format: (wattHours) => `${wattHours} Wh` },
];

export function attributeList(product, attributes) {
  const list = element("dl", "product-attributes");
  for (const attribute of attributes) {
    list.append(
      element("dt", null, attribute.label),
      element("dd", cssClass(attribute), displayValue(product, attribute)),
    );
  }
  return list;
}

export function displayValue(product, attribute) {
  const value = product[attribute.key];
  if (value === null || value === undefined) {
    return MISSING_VALUE;
  }
  return attribute.format ? attribute.format(value) : String(value);
}

export function cssClass(attribute) {
  return attribute.key.replaceAll("_", "-");
}

export function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text !== undefined) {
    node.textContent = text;
  }
  return node;
}
