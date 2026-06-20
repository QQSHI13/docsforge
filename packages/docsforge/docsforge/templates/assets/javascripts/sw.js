/**
 * DocsForge Service Worker - Visit once, use for a lifetime
 * Pre-caches all pages during install so everything works offline immediately.
 */

const BUILD_HASH = "__DOCSFORGE_BUILD_HASH__";
const PRE_CACHE_PAGES = __PRE_CACHE_PAGES__;
const CACHE_NAME = `docsforge-${BUILD_HASH}`;

// Compute base URL from SW location (SW is now at <site>/sw.js)
const BASE_URL = self.location.pathname.replace(/sw\.js$/, '');

// Assets to cache aggressively (fonts, styles, scripts, images)
const ASSET_DESTINATIONS = ["style", "script", "font", "image", "worker"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return Promise.all(
          PRE_CACHE_PAGES.map(url => {
            return fetch(url)
              .then(response => {
                if (response.ok) return cache.put(url, response.clone());
              })
              .catch(() => {});
          })
        );
      })
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    ).then(() => {
      // Notify all clients that a new version is ready
      self.clients.matchAll({ type: 'window' }).then(clients => {
        clients.forEach(client => {
          client.postMessage({
            type: 'DOCSFORGE_UPDATE_READY',
            hash: BUILD_HASH
          });
        });
      });
      return self.clients.claim();
    })
  );
});

self.addEventListener("fetch", (e) => {
  const { request } = e;
  const url = new URL(request.url);

  // Same-origin only
  if (url.origin !== self.location.origin) return;

  // HTML pages: cache-first with network fallback
  if (request.destination === "document" || request.mode === "navigate") {
    e.respondWith(cacheFirstWithNetworkFallback(request));
    return;
  }

  // Assets: cache-first with network fallback
  if (ASSET_DESTINATIONS.includes(request.destination)) {
    e.respondWith(cacheFirstWithNetworkFallback(request));
    return;
  }

  // Everything else: stale-while-revalidate
  e.respondWith(staleWhileRevalidate(request));
});

async function cacheFirstWithNetworkFallback(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);

  if (cached) {
    // Update cache in background (stale-while-revalidate)
    fetch(request).then((networkResponse) => {
      if (networkResponse.ok) cache.put(request, networkResponse.clone());
    }).catch(() => {});
    return cached;
  }

  // Not in cache, fetch from network
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) cache.put(request, networkResponse.clone());
    return networkResponse;
  } catch (err) {
    // Offline and not cached — return offline page for HTML
    if (request.mode === "navigate" || request.destination === "document") {
      const offlinePage = await cache.match(BASE_URL + '404.html').catch(() => null);
      if (offlinePage) return offlinePage;
    }
    return new Response(
      "<h1>Offline</h1><p>This page is not available offline. Please connect to the internet.</p>",
      { status: 503, headers: { "Content-Type": "text/html" } }
    );
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);

  const networkPromise = fetch(request).then((networkResponse) => {
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  }).catch(() => cached);

  return cached || networkPromise;
}
