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
      .then(async cache => {
        let cached = 0;
        let failed = 0;
        
        // First cache critical assets (CSS, JS, favicon, logo) - needed for basic functionality
        console.log('[SW] Pre-caching critical assets...');
        const criticalAssets = [
          'images/favicon.png',
          'assets/stylesheets/main.484c7ddc.min.css',
          'assets/javascripts/bundle.79ae519e.min.js',
          'assets/katex/katex.min.css',
          'assets/katex/katex.min.js',
          'assets/external/unpkg.com/mermaid@11.15.0/dist/mermaid.min.js'
        ];
        await Promise.all(
          criticalAssets.map(url => {
            return fetch(url)
              .then(response => {
                if (response.ok) {
                  console.log('[SW] Cached asset:', url);
                  cached++;
                  return cache.put(url, response.clone());
                } else {
                  console.log('[SW] Failed to cache asset (status', response.status, '):', url);
                  failed++;
                }
              })
              .catch(err => {
                console.log('[SW] Failed to cache asset (error):', url, err.message);
                failed++;
              });
          })
        );
        console.log('[SW] Critical assets cached:', cached, 'cached,', failed, 'failed');
        
        // Then cache all pages
        console.log('[SW] Pre-caching', PRE_CACHE_PAGES.length, 'pages...');
        let pageCached = 0;
        let pageFailed = 0;
        
        await Promise.all(
          PRE_CACHE_PAGES.map(url => {
            return fetch(url)
              .then(response => {
                if (response.ok) {
                  console.log('[SW] Cached page:', url);
                  pageCached++;
                  return cache.put(url, response.clone());
                } else {
                  console.log('[SW] Failed to cache page (status', response.status, '):', url);
                  pageFailed++;
                }
              })
              .catch(err => {
                console.log('[SW] Failed to cache page (error):', url, err.message);
                pageFailed++;
              });
          })
        );
        
        console.log('[SW] Pages cached:', pageCached, 'cached,', pageFailed, 'failed');
        console.log('[SW] Pre-caching complete:', (cached + pageCached), 'total cached,', (failed + pageFailed), 'total failed');
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

  // Skip livereload requests
  if (url.pathname.includes('/livereload/')) return;

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
    console.log('[SW] Background update started:', request.url);
    fetch(request).then((networkResponse) => {
      if (networkResponse.ok) {
        cache.put(request, networkResponse.clone());
        console.log('[SW] Background update complete:', request.url);
      }
    }).catch((err) => {
      console.log('[SW] Background update failed:', request.url, err);
    });
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
      console.log('[SW] Stale-while-revalidate updated:', request.url);
    }
    return networkResponse;
  }).catch((err) => {
    console.log('[SW] Stale-while-revalidate failed:', request.url);
    // Return cached if available, otherwise a 503 response
    return cached || new Response(
      "Offline - resource not cached",
      { status: 503, headers: { "Content-Type": "text/plain" } }
    );
  });

  // If we have cached content, return it immediately while network updates in background
  if (cached) return cached;
  
  // No cache, wait for network
  return networkPromise;
}
