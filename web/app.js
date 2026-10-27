const askForm = document.getElementById("ask-form");
const form = document.getElementById("search-form");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");

const TOP_RESULTS = 5;  // matches the server: only the closest 5 are shown and explained
const FIRST_RADII_KM = [3, 8];  // the server's first radius: 3 km near a place, 8 km for a whole city

const money = new Intl.NumberFormat("en-CA", {
  style: "currency", currency: "CAD", maximumFractionDigits: 0,
});

// Plain-English search: Gemini turns the sentence into filters, then we search.
askForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = new FormData(askForm).get("text");

  statusEl.textContent = "Understanding your request…";
  resultsEl.innerHTML = "";
  MapView.show([]);  // clear old pins so a failed search doesn't show stale results

  try {
    const { filters, center, radius_m, total, results } = await requestJSON("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    fillForm(filters);
    let understood = describeFilters(filters);
    // The server widens the search when nothing is close; say so, so farther results make sense.
    if (center && results.length && !FIRST_RADII_KM.includes(radius_m / 1000)) {
      understood += ` (nothing closer matched, so showing up to ${radius_m / 1000} km away)`;
    }
    showResults(results, total, understood, center);
    explainTop(text, results, center);
  } catch (error) {
    statusEl.textContent = `Search failed: ${error.message}`;
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

  statusEl.textContent = "Searching…";
  resultsEl.innerHTML = "";
  MapView.show([]);

  try {
    const listings = await requestJSON(`/search?${params}`);
    showResults(listings.slice(0, TOP_RESULTS), listings.length);
  } catch (error) {
    statusEl.textContent = `Search failed: ${error.message}`;
  }
});

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

function showResults(listings, total, understood, center) {
  let count;
  if (!listings.length) count = "No listings found. Try a bigger radius or fewer filters.";
  else if (total > listings.length) count = `Top ${listings.length} of ${total} matches`;
  else count = `${total} listing${total === 1 ? "" : "s"} found`;
  statusEl.textContent = understood ? `${count} for: ${understood}` : count;
  listings.forEach((listing, i) => resultsEl.append(renderListing(listing, i + 1)));
  MapView.show(listings, center);
}

// Clicking a pin highlights its card; clicking a card shows its pin.
MapView.onSelect = (id) => selectCard(id, true);

resultsEl.addEventListener("click", (event) => {
  const card = event.target.closest(".listing");
  if (!card) return;
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
    f.preferences,
  ].filter(Boolean).join(", ");
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
  const title = document.createElement("h2");
  const badge = document.createElement("span");
  badge.className = "badge";
  badge.textContent = number;  // matches the number on the map pin
  title.append(badge, l.address);

  const meta = document.createElement("p");
  meta.className = "meta";
  meta.textContent = [
    l.property_type[0].toUpperCase() + l.property_type.slice(1),
    money.format(l.price),
    `${l.bedrooms ?? "?"} bed`,
    `${l.washrooms ?? "?"} bath`,
    l.sqft ? `${l.sqft.toLocaleString()} sqft` : null,
    formatDistance(l.distance_m),
  ].filter(Boolean).join(" · ");

  const description = document.createElement("p");
  description.textContent = l.description ?? "";

  li.append(title, meta, description);
  return li;
}

function formatDistance(metres) {
  return metres < 1000 ? `${metres} m away` : `${(metres / 1000).toFixed(1)} km away`;
}
