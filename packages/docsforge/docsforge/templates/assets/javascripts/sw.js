/**
 * DocsForge Service Worker - Visit once, use for a lifetime
 * Pre-caches all pages during install so everything works offline immediately.
 */

const BUILD_HASH = "__DOCSFORGE_BUILD_HASH__";
const PRE_CACHE_PAGES = __PRE_CACHE_PAGES__;
const CACHE_NAME = `docsforge-${BUILD_HASH}`;

// Compute base URL from SW location (SW is always at <site>/assets/javascripts/sw.js)
const BASE_URL = self.location.pathname.replace(/assets\/javascripts\/sw\.js$/, '');

// Assets to cache aggressively (fonts, styles, scripts, images)
const ASSET_DESTINATIONS = ["style", "script", "font", "image", "worker"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        // Pre-cache all pages - each page is cached independently so one failure
        // doesn't stop the rest
        return Promise.all(
          PRE_CACHE_PAGES.map(url => {
            return fetch(url)
              .then(response => {
                if (response.ok) {
                  return cache.put(url, response.clone());
                }
                console.warn('[SW] Pre-cache skipped (not OK):', url, response.status);
              })
              .catch(err => {
                console.warn('[SW] Pre-cache failed for:', url, err);
              });
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

  console.log('[SW] Fetch event:', request.url, 'destination:', request.destination, 'mode:', request.mode);

  // Same-origin only
  if (url.origin !== self.location.origin) {
    console.log('[SW] Skipping - different origin');
    return;
  }

  // HTML pages: cache-first with network fallback
  if (request.destination === "document" || request.mode === "navigate") {
    console.log('[SW] Intercepting page:', request.url);
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
  console.log('[SW] Cache check for:', request.url, 'found:', !!cached);

  if (cached) {
    // Update cache in background (stale-while-revalidate)
    fetch(request).then((networkResponse) => {
      if (networkResponse.ok) {
        cache.put(request, networkResponse.clone());
      }
    }).catch(() => {});
    return cached;
  }

  // Not in cache - notify clients we're fetching from network
  console.log('[SW] Cache miss - fetching from network:', request.url);
  broadcastFetchStatus('network', request.url, 'start');

  // Not in cache, fetch from network
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      cache.put(request, networkResponse.clone());
    }
    broadcastFetchStatus('network', request.url, 'done');
    return networkResponse;
  } catch (err) {
    broadcastFetchStatus('network', request.url, 'error');
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

// Helper to broadcast fetch status to all clients
async function broadcastFetchStatus(type, url, status) {
  console.log('[SW] Broadcasting status:', status, 'for', url);
  try {
    const clients = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
    console.log('[SW] Found', clients.length, 'clients');
    clients.forEach(client => {
      console.log('[SW] Posting to client:', client.id);
      client.postMessage({
        type: 'DOCSFORGE_FETCH_STATUS',
        fetchType: type,
        url: url,
        status: status
      });
    });
  } catch (e) {
    console.error('[SW] Broadcast error:', e);
  }
}
