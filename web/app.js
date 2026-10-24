const form = document.getElementById("search-form");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");

const money = new Intl.NumberFormat("en-CA", {
  style: "currency", currency: "CAD", maximumFractionDigits: 0,
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  // Only send fields the user filled in, so empty filters are left out.
  const params = new URLSearchParams();
  for (const [key, value] of new FormData(form)) {
    if (value !== "") params.set(key, value);
  }

  statusEl.textContent = "Searching…";
  resultsEl.innerHTML = "";

  try {
    const response = await fetch(`/search?${params}`);
    if (!response.ok) {
      // FastAPI puts the reason in "detail", e.g. 'Could not find "xyz"'.
      const body = await response.json().catch(() => ({}));
      const detail = typeof body.detail === "string" ? body.detail : `Server returned ${response.status}`;
      throw new Error(detail);
    }
    const listings = await response.json();

    statusEl.textContent = listings.length
      ? `${listings.length} listing${listings.length === 1 ? "" : "s"} found`
      : "No listings found. Try a bigger radius or fewer filters.";
    listings.forEach((listing) => resultsEl.append(renderListing(listing)));
  } catch (error) {
    statusEl.textContent = `Search failed: ${error.message}`;
  }
});

function renderListing(l) {
  const li = document.createElement("li");
  li.className = "listing";

  // textContent (not innerHTML) so text from the database is never run as HTML.
  const title = document.createElement("h2");
  title.textContent = l.address;

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
