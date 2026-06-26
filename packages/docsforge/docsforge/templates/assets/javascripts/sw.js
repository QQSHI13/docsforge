/**
 * DocsForge Service Worker
 *
 * Model: the SW treats `docsforge serve` and a deployed site identically —
 * no localhost special-casing. The current page is always served/updated
 * first; everything else is synced in the background.
 *
 *   install    : minimal (skipWaiting) — non-blocking, no pre-cache-all.
 *   activate   : claim + clean old caches + prime the visible page, then sync.
 *   fetch      : page request -> fetch manifest once, serveCurrentPage()
 *                (check + update the current page, return it), and in the
 *                background syncCacheFromManifest(manifest) for the rest.
 *
 * Manifest keys in cache-manifest.json are source-.md hashes; the SW never
 * hashes cached HTML bodies. It diffs the manifest against the previously
 * synced per-file hashes (prevFiles) and re-fetches a page only when it is
 * missing from the cache OR its hash changed.
 */
const BUILD_HASH = "__DOCSFORGE_BUILD_HASH__";
const CACHE_NAME = `docsforge-${BUILD_HASH}`;
const MANIFEST_URL = "cache-manifest.json";
const VERSION_KEY = "docsforge-manifest-version";
const FILES_KEY = "docsforge-manifest-files";
const SYNC_MIN_INTERVAL_MS = 10 * 60 * 1000; // throttle background sync only

// Compute base URL from SW location (handles subpath deploys).
const BASE_URL = self.location.pathname.replace(/sw\.js$/, '');
const ORIGIN_BASE = self.location.origin + BASE_URL;
const ASSET_DESTINATIONS = ["style", "script", "font", "image", "worker"];

// Throttle / dedupe state for background sync.
let _syncPromise = null;
let _lastSyncAt = 0;
// Lookup cache (pathname -> {key, hash}), rebuilt only when the manifest
// version changes.
let _lookupVersion = null;
let _lookupMap = null;

// === Byte comparison helper (used by staleWhileRevalidate) ===
function _buffersEqual(a, b) {
  if (a.byteLength !== b.byteLength) return false;
  const ua = new Uint8Array(a), ub = new Uint8Array(b);
  for (let i = 0; i < ua.length; i++) if (ua[i] !== ub[i]) return false;
  return true;
}

// === Manifest fetch (shared per navigation) ===
// `cache: 'no-cache'` sends a conditional request — the static host returns
// 304 when the manifest is unchanged, instead of a full 200 every navigation.
// (SW-initiated fetches are not intercepted by this SW, so this bypasses the
// runtime cache correctly.)
async function fetchManifest() {
  try {
    const resp = await fetch(MANIFEST_URL, { cache: 'no-cache' });
    if (!resp.ok) return null;
    return await resp.json();
  } catch (e) {
    console.log('[SW] Manifest fetch failed:', e.message);
    return null;
  }
}

// Build a Map: request pathname+search -> { key (relative manifest key), hash }.
function _buildLookup(manifest) {
  const map = new Map();
  const files = (manifest && manifest.files) || {};
  for (const [key, hash] of Object.entries(files)) {
    try {
      const u = new URL(key, ORIGIN_BASE);
      map.set(u.pathname + u.search, { key, hash });
    } catch (e) { /* skip malformed entry */ }
  }
  return map;
}

function getLookup(manifest) {
  const v = manifest ? manifest.version : null;
  if (v === _lookupVersion && _lookupMap) return _lookupMap;
  _lookupMap = _buildLookup(manifest);
  _lookupVersion = v;
  return _lookupMap;
}

// === prevFiles store (per-URL hashes recorded as pages are cached) ===
async function _readPrevFiles() {
  const cache = await caches.open('docsforge-meta');
  const resp = await cache.match(FILES_KEY);
  if (!resp) return {};
  try { return await resp.json() || {}; } catch { return {}; }
}
async function _writePrevFiles(files) {
  const cache = await caches.open('docsforge-meta');
  await cache.put(FILES_KEY, new Response(JSON.stringify(files)));
}
async function _readStoredVersion() {
  const cache = await caches.open('docsforge-meta');
  const resp = await cache.match(VERSION_KEY);
  return resp ? await resp.text() : null;
}
async function _writeStoredVersion(version) {
  const cache = await caches.open('docsforge-meta');
  await cache.put(VERSION_KEY, new Response(version));
}

// === Current page: check + update if needed, return the Response to display ===
async function serveCurrentPage(request, manifest) {
  const cache = await caches.open(CACHE_NAME);
  const lookup = getLookup(manifest);
  const reqUrl = new URL(request.url);
  const entry = lookup.get(reqUrl.pathname + reqUrl.search);
  const newHash = entry ? entry.hash : undefined;
  const relKey = entry ? entry.key : undefined;

  const prevFiles = await _readPrevFiles();
  const prevHash = relKey ? prevFiles[relKey] : undefined;
  const cached = await cache.match(request);

  // Cached AND its manifest hash is unchanged since last sync -> serve now,
  // no network fetch of the page.
  if (cached && newHash && prevHash === newHash) {
    return cached;
  }

  // Missing or outdated -> fetch fresh, cache, display.
  try {
    const netResp = await fetch(request);
    if (netResp && netResp.ok) {
      await cache.put(request, netResp.clone());
      if (relKey && newHash) {
        prevFiles[relKey] = newHash;
        await _writePrevFiles(prevFiles);
      }
      return netResp;
    }
    if (cached) return cached; // network returned non-ok, serve stale
  } catch (e) {
    if (cached) return cached; // offline, serve stale
  }

  // Nothing available -> offline fallback.
  const offline = await cache.match(BASE_URL + '404.html').catch(() => null);
  if (offline) return offline;
  return new Response("<h1>Offline</h1><p>This page is not available offline.</p>",
    { status: 503, headers: { "Content-Type": "text/html" } });
}

// === Background sync: cache every page that is missing or outdated ===
async function maybeSyncCache(manifest) {
  if (_syncPromise) return _syncPromise;                    // dedupe concurrent
  if (Date.now() - _lastSyncAt < SYNC_MIN_INTERVAL_MS) return; // throttle
  _syncPromise = syncCacheFromManifest(manifest).finally(() => {
    _syncPromise = null;
    _lastSyncAt = Date.now();
  });
  return _syncPromise;
}

async function syncCacheFromManifest(manifest) {
  try {
    if (!manifest) manifest = await fetchManifest();
    if (!manifest) return;
    const newVersion = manifest.version;
    const storedVersion = await _readStoredVersion();
    if (newVersion === storedVersion) return; // no changes

    console.log(`[SW] Cache manifest changed (${storedVersion || 'none'} → ${newVersion})`);
    const prevFiles = await _readPrevFiles();
    const newFiles = manifest.files || {};
    const cache = await caches.open(CACHE_NAME);
    let updated = 0, skipped = 0;

    for (const [relKey, newHash] of Object.entries(newFiles)) {
      try {
        const prevHash = prevFiles[relKey];
        const fullUrl = new URL(relKey, ORIGIN_BASE);
        const inCache = await cache.match(fullUrl);
        // Skip only if cached AND hash unchanged since last sync.
        if (inCache && prevHash === newHash) { skipped++; continue; }
        const netResp = await fetch(fullUrl);
        if (netResp && netResp.ok) {
          await cache.put(fullUrl, netResp.clone());
          prevFiles[relKey] = newHash;
          updated++;
        }
      } catch (e) { /* skip inaccessible page */ }
    }

    await _writePrevFiles(prevFiles);
    await _writeStoredVersion(newVersion);
    console.log(`[SW] Sync complete: ${updated} updated, ${skipped} unchanged`);

    if (updated > 0) {
      self.clients.matchAll({ includeUncontrolled: true }).then(cls =>
        cls.forEach(c => c.postMessage({ type: 'DOCSFORGE_UPDATE_READY', count: updated }))
      ).catch(() => {});
    }
  } catch (e) {
    console.log('[SW] Manifest sync failed:', e.message);
  }
}

// === Install: minimal, non-blocking ===
self.addEventListener("install", (e) => {
  e.waitUntil(self.skipWaiting());
});

// === Activate: claim, clean old caches, prime the visible page, then sync ===
self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    await self.clients.claim();
    await caches.keys().then(names => Promise.all(
      names.filter(n => n !== CACHE_NAME && n !== 'docsforge-meta').map(n => caches.delete(n))
    ));

    const manifest = await fetchManifest();

    // Prime the page the user is currently viewing first.
    const clients = await self.clients.matchAll({ includeUncontrolled: true, type: 'window' });
    const visible = clients.find(c => c.visibilityState === 'visible') || clients[0];
    if (visible && manifest) {
      try {
        const cache = await caches.open(CACHE_NAME);
        const lookup = getLookup(manifest);
        const u = new URL(visible.url);
        const entry = lookup.get(u.pathname + u.search);
        const cached = await cache.match(visible.url);
        const prevFiles = await _readPrevFiles();
        const prevHash = entry ? prevFiles[entry.key] : undefined;
        if (!(cached && entry && prevHash === entry.hash)) {
          const resp = await fetch(visible.url);
          if (resp && resp.ok) {
            await cache.put(visible.url, resp.clone());
            if (entry) { prevFiles[entry.key] = entry.hash; await _writePrevFiles(prevFiles); }
            console.log('[SW] Primed current page:', visible.url);
          }
        }
      } catch (e) { /* non-fatal */ }
    }

    await maybeSyncCache(manifest).catch(() => {});
  })());
});

// === Fetch ===
self.addEventListener("fetch", (e) => {
  const { request } = e;
  const url = new URL(request.url);

  if (url.origin !== self.location.origin) return;
  if (url.pathname.includes('/livereload/')) return;

  // Page request: hard navigation OR programmatic HTML fetch (Material
  // instant navigation). Always handle the current page first.
  if (isPageRequest(request)) {
    const manifestP = fetchManifest(); // fetched once, shared
    e.respondWith((async () => {
      const manifest = await manifestP;
      return serveCurrentPage(request, manifest);
    })());
    e.waitUntil((async () => {
      const manifest = await manifestP;
      return maybeSyncCache(manifest);
    })());
    return;
  }

  // Assets: cache-first with network fallback.
  if (ASSET_DESTINATIONS.includes(request.destination)) {
    e.respondWith(cacheFirst(request));
    return;
  }

  // Everything else: stale-while-revalidate.
  e.respondWith(staleWhileRevalidate(request));
});

function isPageRequest(request) {
  if (request.destination === 'document' || request.mode === 'navigate') return true;
  // Programmatic HTML fetch (e.g. Material "instant navigation").
  if (request.method !== 'GET') return false;
  const accept = request.headers.get('accept') || '';
  return accept.includes('text/html');
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  if (cached) return cached;
  try {
    const netResp = await fetch(request);
    if (netResp.ok) cache.put(request, netResp.clone());
    return netResp;
  } catch (err) {
    return new Response("Offline", { status: 503, headers: { "Content-Type": "text/plain" } });
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
        }
      } else {
        cache.put(request, netResp);
      }
    }
    return netResp;
  }).catch(() => cached || new Response("Offline",
    { status: 503, headers: { "Content-Type": "text/plain" } }));

  if (cached) return cached;
  return networkPromise;
}
