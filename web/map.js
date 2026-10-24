// The map beside the results. app.js calls MapView.show / MapView.focus, and
// MapView.onSelect tells app.js when a pin is clicked.
// If no browser key is configured, the map stays hidden and the list still works.
const MapView = (() => {
  const mapEl = document.getElementById("map");
  const VANCOUVER = { lat: 49.2610, lng: -123.1140 };

  let map, infoWindow, ready;
  let markers = new Map();  // listing id -> marker
  let centerMarker = null;

  ready = (async () => {
    const { maps_browser_key: key } = await fetch("/config").then((r) => r.json());
    if (!key) return false;

    await loadGoogleMaps(key);
    const { Map: GoogleMap, InfoWindow } = await google.maps.importLibrary("maps");
    await google.maps.importLibrary("marker");

    mapEl.hidden = false;
    map = new GoogleMap(mapEl, {
      center: VANCOUVER,
      zoom: 12,
      mapId: "DEMO_MAP_ID",  // needed for AdvancedMarkerElement; fine for development
      streetViewControl: false,
      mapTypeControl: false,
    });
    infoWindow = new InfoWindow();
    return true;
  })().catch((error) => {
    console.warn("Map unavailable:", error);
    return false;
  });

  // The script finishing download isn't enough: Google calls `callback` once
  // the API is actually ready to use.
  function loadGoogleMaps(key) {
    return new Promise((resolve, reject) => {
      window.__onGoogleMapsReady = resolve;
      const script = document.createElement("script");
      script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}&v=weekly&loading=async&callback=__onGoogleMapsReady`;
      script.async = true;
      script.onerror = () => reject(new Error("Could not load Google Maps"));
      document.head.append(script);
    });
  }

  async function show(listings, center) {
    if (!(await ready)) return;
    const { AdvancedMarkerElement, PinElement } = google.maps.marker;

    markers.forEach((m) => (m.map = null));
    markers = new Map();
    if (centerMarker) centerMarker.map = null;
    centerMarker = null;
    infoWindow.close();

    const bounds = new google.maps.LatLngBounds();

    listings.forEach((l, i) => {
      const position = { lat: l.lat, lng: l.lon };
      const pin = new PinElement({ glyphText: String(i + 1), background: "#2b6cb0", borderColor: "#1a4a80", glyphColor: "#fff" });
      const marker = new AdvancedMarkerElement({ map, position, content: pin, title: l.address, gmpClickable: true });
      marker.addListener("gmp-click", () => {
        openInfo(l.id);
        MapView.onSelect?.(l.id);
      });
      marker.listing = l;
      markers.set(l.id, marker);
      bounds.extend(position);
    });

    if (center) {
      const position = { lat: center.lat, lng: center.lon };
      const pin = new PinElement({ background: "#d9534f", borderColor: "#a94442", glyphColor: "#fff", scale: 0.9 });
      centerMarker = new AdvancedMarkerElement({ map, position, content: pin, title: "Searched place" });
      bounds.extend(position);
    }

    if (bounds.isEmpty()) {
      map.setCenter(VANCOUVER);
      map.setZoom(12);
    } else {
      map.fitBounds(bounds, 48);
      // One point would zoom in to street level; keep some context.
      google.maps.event.addListenerOnce(map, "idle", () => {
        if (map.getZoom() > 15) map.setZoom(15);
      });
    }
  }

  function openInfo(id) {
    const marker = markers.get(id);
    if (!marker) return;
    const content = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = marker.listing.address;  // textContent: never run listing text as HTML
    content.append(title);
    infoWindow.setContent(content);
    infoWindow.open({ map, anchor: marker });
  }

  async function focus(id) {
    if (!(await ready)) return;
    const marker = markers.get(id);
    if (!marker) return;
    map.panTo(marker.position);
    openInfo(id);
  }

  return { show, focus, onSelect: null };
})();
