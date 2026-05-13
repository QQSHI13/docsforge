/**
 * DocsForge Service Worker - Basic offline caching
 * Caches: HTML pages, CSS, JS, icons, KaTeX fonts
 */

const CACHE_NAME = "docsforge-v1";

// Assets to cache on install
const PRECACHE_ASSETS = [
  "assets/stylesheets/main.min.css",
  "assets/stylesheets/palette.min.css",
  "assets/javascripts/bundle.min.js",
  "assets/katex/katex.min.css",
  "assets/katex/katex.min.js",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (e) => {
  const { request } = e;
  const url = new URL(request.url);

  // Same-origin only
  if (url.origin !== self.location.origin) return;

  // Cache-first for assets, network-first for HTML
  if (request.destination === "document") {
    e.respondWith(networkFirst(request));
  } else if (["style", "script", "font", "image"].includes(request.destination)) {
    e.respondWith(cacheFirst(request));
  }
});

async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    const cache = await caches.open(CACHE_NAME);
    cache.put(request, networkResponse.clone());
    return networkResponse;
  } catch {
    const cached = await caches.match(request);
    return cached || new Response("Offline", { status: 503 });
  }
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;
  try {
    const networkResponse = await fetch(request);
    const cache = await caches.open(CACHE_NAME);
    cache.put(request, networkResponse.clone());
    return networkResponse;
  } catch {
    return new Response("", { status: 204 });
  }
}
