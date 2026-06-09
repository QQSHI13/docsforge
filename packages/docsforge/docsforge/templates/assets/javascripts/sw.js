/**
 * DocsForge Service Worker - Full offline support with pre-caching
 * Pre-caches all pages during install, cache-first with network fallback
 */

const BUILD_HASH = "__DOCSFORGE_BUILD_HASH__";
const PRE_CACHE_PAGES = __PRE_CACHE_PAGES__;
const CACHE_NAME = `docsforge-${BUILD_HASH}`;

// Compute base URL from SW location (SW is always at <site>/assets/javascripts/sw.js)
const BASE_URL = self.location.pathname.replace(/assets\/javascripts\/sw\.js$/, '');

// Assets to cache aggressively (fonts, styles, scripts, images)
const ASSET_DESTINATIONS = ["style", "script", "font", "image", "worker"];

self.addEventListener("install", (e) => {
  // Don't block on pre-caching — just activate immediately so the page loads fast
  e.waitUntil(self.skipWaiting());
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

  // Start caching pages in the background after activation.
  // This is NON-BLOCKING — user can browse while other pages are cached.
  backgroundCachePages();
});

// Cache pages one by one in the background without blocking the user
async function backgroundCachePages() {
  const cache = await caches.open(CACHE_NAME);
  let cached = 0;
  let failed = 0;

  for (const url of PRE_CACHE_PAGES) {
    try {
      // Skip if already cached (e.g., the current page was just visited)
      const existing = await cache.match(url);
      if (existing) continue;

      const response = await fetch(url);
      if (response.ok) {
        await cache.put(url, response.clone());
        cached++;
      }
    } catch (err) {
      failed++;
      console.warn('[SW] Background cache failed for:', url, err);
    }
  }

  console.log(`[SW] Background caching complete: ${cached} cached, ${failed} failed`);

  // Notify clients that background caching is done
  const clients = await self.clients.matchAll({ type: 'window' });
  clients.forEach(client => {
    client.postMessage({
      type: 'DOCSFORGE_CACHE_COMPLETE',
      cached: cached,
      failed: failed
    });
  });
}

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
      if (networkResponse.ok) {
        cache.put(request, networkResponse.clone());
      }
    }).catch(() => {});
    return cached;
  }

  // Not in cache, fetch from network
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
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
