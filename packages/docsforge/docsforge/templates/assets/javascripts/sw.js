/**
 * DocsForge Service Worker — Load once, use for a lifetime
 *
 * Strategy:
 *   1. Install: pre-cache all pages from PRE_CACHE_PAGES
 *   2. Activate: fetch cache-manifest.json, update any stale pages
 *   3. Runtime: serve cached, then sync manifest in background
 */
const BUILD_HASH = "__DOCSFORGE_BUILD_HASH__";
const PRE_CACHE_PAGES = __PRE_CACHE_PAGES__;
const CACHE_NAME = `docsforge-${BUILD_HASH}`;
const MANIFEST_URL = "cache-manifest.json";
const HASH_KEY = "docsforge-manifest-version";

// Compute base URL from SW location
const BASE_URL = self.location.pathname.replace(/sw\.js$/, '');
const ASSET_DESTINATIONS = ["style", "script", "font", "image", "worker"];

// === Byte comparison helper ===
function _buffersEqual(a, b) {
  if (a.byteLength !== b.byteLength) return false;
  const ua = new Uint8Array(a), ub = new Uint8Array(b);
  for (let i = 0; i < ua.length; i++) if (ua[i] !== ub[i]) return false;
  return true;
}

// === Manifest-based cache sync ===
async function syncCacheFromManifest() {
  try {
    // Always fetch fresh manifest (bypass SW cache for this request)
    const resp = await fetch(`${MANIFEST_URL}?v=${Date.now()}`);
    if (!resp.ok) return;
    const manifest = await resp.json();
    const newVersion = manifest.version;
    const storedVersion = await _readStoredVersion();

    if (newVersion === storedVersion) return; // No changes

    console.log(`[SW] Cache manifest changed (${storedVersion || 'none'} → ${newVersion})`);

    const cache = await caches.open(CACHE_NAME);
    const files = manifest.files || {};
    let updated = 0, skipped = 0;

    for (const [url, expectedHash] of Object.entries(files)) {
      try {
        const cached = await cache.match(url);
        if (cached) {
          const body = await cached.clone().arrayBuffer();
          const actualHash = await _sha256(body);
          if (actualHash === expectedHash) { skipped++; continue; }
        }
        // Fetch updated page
        const netResp = await fetch(url);
        if (netResp.ok) {
          await cache.put(url, netResp.clone());
          updated++;
          console.log(`[SW] Updated: ${url}`);
        }
      } catch (e) { /* skip inaccessible pages */ }
    }

    await _writeStoredVersion(newVersion);
    console.log(`[SW] Sync complete: ${updated} updated, ${skipped} unchanged`);
  } catch (e) {
    console.log('[SW] Manifest sync failed:', e.message);
  }
}

async function _readStoredVersion() {
  const cache = await caches.open('docsforge-meta');
  const resp = await cache.match(HASH_KEY);
  return resp ? resp.text() : null;
}

async function _writeStoredVersion(version) {
  const cache = await caches.open('docsforge-meta');
  await cache.put(HASH_KEY, new Response(version));
}

async function _sha256(buffer) {
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('').slice(0, 16);
}

// === Install: pre-cache everything ===
self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(async cache => {
      let cached = 0, failed = 0;

      console.log(`[SW] Pre-caching ${PRE_CACHE_PAGES.length} pages...`);
      await Promise.all(PRE_CACHE_PAGES.map(url =>
        fetch(url).then(resp => {
          if (resp.ok) {
            console.log(`[SW] Cached: ${url}`);
            cached++;
            return cache.put(url, resp.clone());
          } else { failed++; }
        }).catch(err => {
          console.log(`[SW] Failed: ${url} (${err.message})`);
          failed++;
        })
      ));

      console.log(`[SW] Pre-cache done: ${cached} cached, ${failed} failed`);
    }).then(() => self.skipWaiting())
  );
});

// === Activate: sync cache from manifest ===
self.addEventListener("activate", (e) => {
  e.waitUntil(
    self.clients.claim().then(() => syncCacheFromManifest())
  );
});

// === Fetch: cache-first with manifest sync in background ===
self.addEventListener("fetch", (e) => {
  const { request } = e;
  const url = new URL(request.url);

  // Same-origin only
  if (url.origin !== self.location.origin) return;
  // Skip live reload
  if (url.pathname.includes('/livereload/')) return;

  // During local dev, always fetch from network — the SW cache interferes
  // with livereload by serving stale pages, causing continuous reload loops.
  if (url.hostname === 'localhost' || url.hostname === '127.0.0.1') {
    e.respondWith(fetch(request));
    return;
  }

  // HTML pages: cache-first + trigger manifest sync
  if (request.destination === "document" || request.mode === "navigate") {
    e.respondWith(cacheFirst(request));
    e.waitUntil(syncCacheFromManifest()); // Background: sync all pages
    return;
  }

  // Assets: cache-first with network fallback
  if (ASSET_DESTINATIONS.includes(request.destination)) {
    e.respondWith(cacheFirst(request));
    return;
  }

  // Everything else: stale-while-revalidate
  e.respondWith(staleWhileRevalidate(request));
});

async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  if (cached) return cached;

  try {
    const netResp = await fetch(request);
    if (netResp.ok) {
      console.log(`[SW] Cached new: ${request.url}`);
      cache.put(request, netResp.clone());
    }
    return netResp;
  } catch (err) {
    if (request.mode === "navigate" || request.destination === "document") {
      const offlinePage = await cache.match(BASE_URL + '404.html').catch(() => null);
      if (offlinePage) return offlinePage;
    }
    return new Response("<h1>Offline</h1><p>This page is not available offline.</p>",
      { status: 503, headers: { "Content-Type": "text/html" } });
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);

  const networkPromise = fetch(request).then(async (netResp) => {
    if (netResp.ok) {
      const netClone = netResp.clone();
      if (cached) {
        const cBody = await cached.clone().arrayBuffer();
        const nBody = await netClone.arrayBuffer();
        if (nBody.byteLength !== cBody.byteLength || !_buffersEqual(nBody, cBody)) {
          cache.put(request, netResp);
          console.log(`[SW] Updated: ${request.url}`);
        }
      } else {
        cache.put(request, netResp);
      }
    }
    return netResp;
  }).catch(() => {
    return cached || new Response("Offline",
      { status: 503, headers: { "Content-Type": "text/plain" } });
  });

  if (cached) return cached;
  return networkPromise;
}
