// The map behind the whole page. app.js calls MapView.show / MapView.focus, and
// MapView.onSelect tells app.js when a pin is clicked.
// If no browser key is configured, the map stays hidden and the list still works.
const MapView = (() => {
  const mapEl = document.getElementById("map");
  const resultsPanelEl = document.getElementById("results-panel");
  const phoneLayout = window.matchMedia("(max-width: 700px)");  // same breakpoint as style.css
  const METRO_VANCOUVER = { lat: 49.215, lng: -122.98 };
  const LANDING_ZOOM = 11;
  const MAX_ZOOM = 15;  // one result alone would zoom to street level; keep some context
  const FLY_MS = 1800;

  let map, infoWindow, ready;
  let markers = new Map();  // listing id -> marker
  let centerMarker = null;
  let flight = null;  // the running zoom animation: { frame, center, zoom } of where it's heading

  ready = (async () => {
    const { maps_browser_key: key } = await fetch("/config").then((r) => r.json());
    if (!key) return false;

    await loadGoogleMaps(key);
    const { Map: GoogleMap, InfoWindow, RenderingType } = await google.maps.importLibrary("maps");
    await google.maps.importLibrary("marker");

    mapEl.hidden = false;
    map = new GoogleMap(mapEl, {
      center: METRO_VANCOUVER,
      zoom: LANDING_ZOOM,
      // Our Map ID from Google Cloud: its style hides city and neighbourhood names.
      // (A Map ID is also needed for AdvancedMarkerElement pins.)
      mapId: "c0fa37559b1193ad18ffd584",
      renderingType: RenderingType.VECTOR,  // vector maps can zoom smoothly
      streetViewControl: false,
      mapTypeControl: false,
      fullscreenControl: false,
      clickableIcons: false,
      gestureHandling: "greedy",  // the map fills the page, so scroll-to-zoom without Ctrl
    });
    infoWindow = new InfoWindow({ disableAutoPan: true });  // focus() does its own panning
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

    const points = [];

    listings.forEach((l, i) => {
      const position = { lat: l.lat, lng: l.lon };
      const pin = new PinElement({ glyphText: String(i + 1), background: "#153541", borderColor: "#0c2230", glyphColor: "#fff" });
      const marker = new AdvancedMarkerElement({ map, position, content: pin, title: l.address, gmpClickable: true });
      marker.addEventListener("gmp-click", () => {
        highlight(l.id);
        openInfo(l.id);
        MapView.onSelect?.(l.id);
      });
      marker.listing = l;
      marker.pin = pin;
      markers.set(l.id, marker);
      points.push(position);
    });

    if (center) {
      const position = { lat: center.lat, lng: center.lon };
      const pin = new PinElement({ background: "#e8590c", borderColor: "#b3440a", glyphColor: "#fff", scale: 0.9 });
      centerMarker = new AdvancedMarkerElement({ map, position, content: pin, title: "Searched place" });
      points.push(position);
    }

    // No pins (a new search is starting, or nothing matched): leave the map where it is,
    // so the next results zoom in from the current view.
    if (points.length) flyTo(points);
  }

  // ---------- Zooming to the results ----------

  // The search bar and results float over the map, so leave room for them when fitting pins.
  // The bar may still be gliding to its corner, so use where it ends up (from style.css),
  // not where it is right now. Extra room at the top because pins stick up above their spot.
  function padding() {
    if (phoneLayout.matches) {
      return {
        top: 12 + 52 + 56,  // bar's top + bar's height + room for pins
        right: 32,
        bottom: window.innerHeight - resultsPanelEl.offsetTop + 24,  // the bottom sheet
        left: 32,
      };
    }
    return { top: 80, right: 56, bottom: 56, left: 16 + 440 + 56 };  // sidebar's left + width + gap
  }

  // Web Mercator: turns lat/lng into flat "world" coordinates (0..256) that zoom can scale.
  function toWorld({ lat, lng }) {
    const sin = Math.min(Math.max(Math.sin((lat * Math.PI) / 180), -0.9999), 0.9999);
    return {
      x: ((lng + 180) / 360) * 256,
      y: (0.5 - Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI)) * 256,
    };
  }

  function fromWorld({ x, y }) {
    return {
      lat: (Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / 256))) * 180) / Math.PI,
      lng: (x / 256) * 360 - 180,
    };
  }

  // Where the map's centre must be so `world` lands in the middle of the uncovered area.
  function shiftedCenter(world, zoom, pad) {
    const scale = 2 ** zoom;
    return {
      x: world.x - (pad.left - pad.right) / 2 / scale,
      y: world.y - (pad.top - pad.bottom) / 2 / scale,
    };
  }

  // Work out the zoom and centre that fit all points, then animate there.
  function flyTo(points) {
    const pad = padding();
    const world = points.map((p) => toWorld(p));
    const xs = world.map((w) => w.x);
    const ys = world.map((w) => w.y);
    const width = Math.max(mapEl.clientWidth - pad.left - pad.right, 50);
    const height = Math.max(mapEl.clientHeight - pad.top - pad.bottom, 50);
    const zoom = Math.min(
      Math.log2(width / (Math.max(...xs) - Math.min(...xs) || 1e-9)),
      Math.log2(height / (Math.max(...ys) - Math.min(...ys) || 1e-9)),
      MAX_ZOOM,
    );
    const middle = { x: (Math.min(...xs) + Math.max(...xs)) / 2, y: (Math.min(...ys) + Math.max(...ys)) / 2 };
    animateCamera(shiftedCenter(middle, zoom, pad), zoom);
  }

  // Raster maps can only jump between whole zoom levels, so smooth zooming needs a vector map.
  function animateCamera(targetWorld, targetZoom) {
    stopFlight(false);
    const target = fromWorld(targetWorld);

    // Hidden tabs pause animations, so just jump there.
    if (document.hidden) {
      map.moveCamera({ center: target, zoom: targetZoom });
      return;
    }

    if (map.getRenderingType() !== google.maps.RenderingType.VECTOR) {
      map.setZoom(Math.floor(targetZoom));
      map.panTo(target);
      return;
    }

    const startWorld = toWorld(map.getCenter().toJSON());
    const startZoom = map.getZoom();
    const startTime = performance.now();
    const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

    const step = (now) => {
      const t = Math.min((now - startTime) / FLY_MS, 1);
      const e = ease(t);
      map.moveCamera({
        center: fromWorld({
          x: startWorld.x + (targetWorld.x - startWorld.x) * e,
          y: startWorld.y + (targetWorld.y - startWorld.y) * e,
        }),
        zoom: startZoom + (targetZoom - startZoom) * e,
      });
      if (t < 1) flight.frame = requestAnimationFrame(step);
      else flight = null;
    };
    flight = { frame: requestAnimationFrame(step), center: target, zoom: targetZoom };
    // Safety net: if the browser stops drawing frames, still end up in the right place.
    const thisFlight = flight;
    setTimeout(() => flight === thisFlight && stopFlight(true), FLY_MS + 300);
  }

  // Stop a running zoom; `finish` jumps straight to where it was heading.
  function stopFlight(finish) {
    if (!flight) return;
    cancelAnimationFrame(flight.frame);
    if (finish) map.moveCamera({ center: flight.center, zoom: flight.zoom });
    flight = null;
  }

  // ---------- Selecting a listing ----------

  // Make the chosen pin bigger so it's easy to spot.
  function highlight(id) {
    markers.forEach((marker, markerId) => {
      marker.pin.scale = markerId === id ? 1.35 : 1;
      marker.zIndex = markerId === id ? 1 : 0;
    });
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
    stopFlight(true);  // clicked mid-zoom: finish zooming first so the pan uses the final zoom
    // Pan so the pin sits in the uncovered part of the map, not under the panel.
    const world = toWorld({ lat: marker.listing.lat, lng: marker.listing.lon });
    map.panTo(fromWorld(shiftedCenter(world, map.getZoom(), padding())));
    highlight(id);
    openInfo(id);
  }

  return { show, focus, onSelect: null };
})();
