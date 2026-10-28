const askForm = document.getElementById("ask-form");
const form = document.getElementById("search-form");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");

const TOP_RESULTS = 5;  // matches the server: only the closest 5 are shown and explained
const FIRST_RADII_KM = [3, 8];  // the server's first radius: 3 km near a place, 8 km for a whole city

const money = new Intl.NumberFormat("en-CA", {
  style: "currency", currency: "CAD", maximumFractionDigits: 0,
});

// The filters button in the search bar opens and closes the manual filters.
const filtersToggle = document.getElementById("filters-toggle");
filtersToggle.addEventListener("click", () => setFiltersOpen(form.hidden));

function setFiltersOpen(open) {
  form.hidden = !open;
  filtersToggle.setAttribute("aria-expanded", String(open));
}

// Plain-English search: Gemini turns the sentence into filters, then we search.
askForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = new FormData(askForm).get("text");

  startSearch(askForm, "Understanding your request…");

  try {
    const { filters, center, radius_m, total, results } = await requestJSON("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    fillForm(filters);
    // The server widens the search when nothing is close; say so, so farther results make sense.
    let note = null;
    if (center && results.length && !FIRST_RADII_KM.includes(radius_m / 1000)) {
      note = `Nothing closer matched, so showing up to ${radius_m / 1000} km away.`;
    }
    showResults(results, total, describeFilters(filters), center, note);
    explainTop(text, results, center);
  } catch (error) {
    showError(error);
  } finally {
    endSearch(askForm);
  }
});

// Manual filters.
form.addEventListener("submit", async (event) => {
  event.preventDefault();

  // Only send fields the user filled in, so empty filters are left out.
  const params = new URLSearchParams();
  for (const [key, value] of new FormData(form)) {
    if (value !== "") params.set(key, value);
  }

  startSearch(form, "Searching…");

  try {
    const listings = await requestJSON(`/search?${params}`);
    showResults(listings.slice(0, TOP_RESULTS), listings.length);
  } catch (error) {
    showError(error);
  } finally {
    endSearch(form);
  }
});

// Switch to the results layout and show placeholder cards while we wait.
function startSearch(sourceForm, message) {
  document.body.classList.add("searched");
  setFiltersOpen(false);  // tuck the filters away so the results and map are visible
  sourceForm.querySelector("button[type=submit]").disabled = true;
  statusEl.className = "";
  statusEl.textContent = message;
  resultsEl.innerHTML = "";
  for (let i = 0; i < 3; i++) {
    const skeleton = document.createElement("li");
    skeleton.className = "listing skeleton";
    resultsEl.append(skeleton);
  }
  MapView.show([]);  // clear old pins so a failed search doesn't show stale results
}

function endSearch(sourceForm) {
  sourceForm.querySelector("button[type=submit]").disabled = false;
}

function showError(error) {
  resultsEl.innerHTML = "";
  statusEl.className = "error";
  statusEl.textContent = `Search failed: ${error.message}`;
}

async function requestJSON(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    // FastAPI puts the reason in "detail", e.g. 'Could not find "xyz"'.
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : `Server returned ${response.status}`;
    throw new Error(detail);
  }
  return response.json();
}

function showResults(listings, total, tags = [], center, note) {
  let count;
  if (!listings.length) count = "No listings found. Try a bigger radius or fewer filters.";
  else if (total > listings.length) count = `Top ${listings.length} of ${total} matches`;
  else count = `${total} listing${total === 1 ? "" : "s"} found`;

  // Status: the count, then what was understood as small tags.
  statusEl.className = "";
  statusEl.textContent = "";
  const countEl = document.createElement("span");
  countEl.className = "count";
  countEl.textContent = tags.length ? `${count} for:` : count;
  statusEl.append(countEl);
  if (tags.length) {
    const tagsEl = document.createElement("span");
    tagsEl.className = "tags";
    for (const tag of tags) {
      const tagEl = document.createElement("span");
      tagEl.className = "tag";
      tagEl.textContent = tag;
      tagsEl.append(tagEl);
    }
    statusEl.append(tagsEl);
  }
  if (note) {
    const noteEl = document.createElement("span");
    noteEl.className = "note";
    noteEl.textContent = note;
    statusEl.append(noteEl);
  }

  resultsEl.innerHTML = "";
  listings.forEach((listing, i) => resultsEl.append(renderListing(listing, i + 1)));
  MapView.show(listings, center);
}

// Clicking a pin highlights its card; clicking a card shows its pin.
MapView.onSelect = (id) => selectCard(id, true);

resultsEl.addEventListener("click", (event) => {
  const card = event.target.closest(".listing");
  if (!card || card.classList.contains("skeleton")) return;
  const id = Number(card.dataset.id);
  selectCard(id, false);
  MapView.focus(id);
});

function selectCard(id, scroll) {
  resultsEl.querySelectorAll(".listing.selected").forEach((el) => el.classList.remove("selected"));
  const card = resultsEl.querySelector(`[data-id="${id}"]`);
  if (!card) return;
  card.classList.add("selected");
  if (scroll) card.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

// Show what Gemini understood in the manual form, so the user can check and adjust it.
function fillForm(filters) {
  form.elements.near.value = filters.near ?? "";
  form.elements.bedrooms_min.value = filters.bedrooms_min ?? "";
  form.elements.price_max.value = filters.price_max ?? "";
  form.elements.property_type.value = filters.property_type ?? "";
}

function describeFilters(f) {
  return [
    f.property_type,
    f.bedrooms_min != null ? `${f.bedrooms_min}+ bed` : null,
    f.price_max != null ? `under ${money.format(f.price_max)}` : null,
    f.near ? `near ${f.near}` : "anywhere in Metro Vancouver",
    ...(f.preferences ? f.preferences.split(/,\s*/) : []),
  ].filter(Boolean);
}

// Explanations load after the list, so slow AI never blocks the results.
async function explainTop(text, listings, center) {
  const top = listings.slice(0, TOP_RESULTS);
  if (!top.length) return;

  const slots = top.map((l) => {
    const slot = document.createElement("p");
    slot.className = "explanation loading";
    slot.textContent = "Writing why this fits…";
    resultsEl.querySelector(`[data-id="${l.id}"]`).append(slot);
    return [l.id, slot];
  });

  try {
    const explanations = await requestJSON("/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, listing_ids: top.map((l) => l.id), center }),
    });
    for (const [id, slot] of slots) {
      if (explanations[id]) {
        slot.textContent = explanations[id];
        slot.classList.remove("loading");
      } else {
        slot.remove();
      }
    }
  } catch {
    slots.forEach(([, slot]) => slot.remove());  // results still work without explanations
  }
}

function renderListing(l, number) {
  const li = document.createElement("li");
  li.className = "listing";
  li.dataset.id = l.id;

  // textContent (not innerHTML) so text from the database or AI is never run as HTML.
  const badge = document.createElement("span");
  badge.className = "badge";
  badge.textContent = number;  // matches the number on the map pin

  const price = document.createElement("p");
  price.className = "price";
  price.textContent = money.format(l.price);

  const address = document.createElement("h2");
  address.className = "address";
  address.textContent = l.address;

  const chips = document.createElement("ul");
  chips.className = "chips";
  for (const text of [
    l.property_type[0].toUpperCase() + l.property_type.slice(1),
    `${l.bedrooms ?? "?"} bed`,
    `${l.washrooms ?? "?"} bath`,
    l.sqft ? `${l.sqft.toLocaleString()} sqft` : null,
    formatDistance(l.distance_m),
  ]) {
    if (!text) continue;
    const chip = document.createElement("li");
    chip.textContent = text;
    chips.append(chip);
  }

  const description = document.createElement("p");
  description.className = "description";
  description.textContent = l.description ?? "";

  li.append(badge, price, address, chips, description);
  return li;
}

function formatDistance(metres) {
  return metres < 1000 ? `${metres} m away` : `${(metres / 1000).toFixed(1)} km away`;
}
