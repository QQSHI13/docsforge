/**
 * DocsForge Service Worker
 *
 * Strategy: cache-everything, manifest-driven delta updates, no localhost
 * special-casing. After the first install every page/asset needed to render the
 * site is cached, so going offline gives the same experience as online.
 *
 *   install    : skipWaiting, no pre-cache.
 *   activate   : claim, fetch manifest, sync every listed page into cache.
 *   fetch      : cache-first for everything.
 *                - Hard refresh refreshes the manifest in the background.
 *                - Normal navigation and instant navigation use the cached
 *                  manifest only.
 *                - Missing/uncached resources return 404, never an "Offline" page.
 */
const BUILD_HASH = "__DOCSFORGE_BUILD_HASH__";
const CACHE_NAME = `docsforge-${BUILD_HASH}`;
const META_CACHE = 'docsforge-meta';
const MANIFEST_URL = 'cache-manifest.json';
const FILES_KEY = 'docsforge-manifest-files';

const BASE_URL = "__DOCSFORGE_BASE_URL__".replace(/\/?$/, '/') || self.location.pathname.replace(/sw\.js$/, '');
const ORIGIN_BASE = self.location.origin + BASE_URL;

// In-memory manifest + dedupe promises.
let _manifest = null;
let _manifestRefresh = null;
let _syncPromise = null;

// === Manifest helpers ===

async function loadManifestFromCache() {
  if (_manifest) return _manifest;
  try {
    const cache = await caches.open(META_CACHE);
    const resp = await cache.match(MANIFEST_URL);
    if (resp) {
      _manifest = await resp.json();
      return _manifest;
    }
  } catch (e) { /* ignore */ }
  return null;
}

async function refreshManifest() {
  if (_manifestRefresh) return _manifestRefresh;
  _manifestRefresh = (async () => {
    try {
      const resp = await fetch(MANIFEST_URL, { cache: 'no-cache' });
      if (resp.ok) {
        const clone = resp.clone();
        const data = await resp.json();
        const cache = await caches.open(META_CACHE);
        await cache.put(MANIFEST_URL, clone);
        _manifest = data;
        await syncCacheFromManifest(data);
      }
    } catch (e) {
      console.log('[SW] Manifest refresh failed:', e.message);
    }
    return _manifest;
  })().finally(() => { _manifestRefresh = null; });
  return _manifestRefresh;
}

function isHardRefresh(request) {
  // Hard reload (Ctrl/Cmd+Shift+R or Ctrl/Cmd+F5) sets cache to 'reload' or
  // 'no-store'. Normal link clicks and new-tab navigations use 'default'.
  return request && ['reload', 'no-store'].includes(request.cache);
}

async function getManifest(request) {
  const cached = await loadManifestFromCache();
  // Refresh the manifest only on hard refresh, not on normal navigation or
  // instant navigation. This keeps network usage minimal.
  if (isHardRefresh(request)) {
    refreshManifest().catch(() => {});
  }
  return cached;
}

function buildLookup(manifest) {
  const map = new Map();
  const files = (manifest && manifest.files) || {};
  for (const [key, hash] of Object.entries(files)) {
    try {
      const u = new URL(key, ORIGIN_BASE);
      map.set(u.pathname + u.search, { key, hash });
    } catch (e) { /* skip malformed */ }
  }
  return map;
}

// === Per-file hash store (cross-SW-version) ===

async function readPrevFiles() {
  const cache = await caches.open(META_CACHE);
  const resp = await cache.match(FILES_KEY);
  if (!resp) return {};
  try { return await resp.json() || {}; } catch { return {}; }
}

async function writePrevFiles(files) {
  const cache = await caches.open(META_CACHE);
  await cache.put(FILES_KEY, new Response(JSON.stringify(files)));
}

// === Cache sync ===

async function syncCacheFromManifest(manifest) {
  if (!manifest) return;
  if (_syncPromise) return _syncPromise;
  _syncPromise = (async () => {
    const prevFiles = await readPrevFiles();
    const newFiles = manifest.files || {};
    const cache = await caches.open(CACHE_NAME);
    let updated = 0;

    for (const [key, newHash] of Object.entries(newFiles)) {
      try {
        if (prevFiles[key] === newHash) continue;
        const fullUrl = new URL(key, ORIGIN_BASE);
        const resp = await fetch(fullUrl);
        if (resp && resp.ok) {
          await cache.put(fullUrl, resp.clone());
          prevFiles[key] = newHash;
          updated++;
        }
      } catch (e) { /* skip inaccessible page */ }
    }

    await writePrevFiles(prevFiles);

    if (updated > 0) {
      self.clients.matchAll({ includeUncontrolled: true }).then(cls =>
        cls.forEach(c => c.postMessage({ type: 'DOCSFORGE_UPDATE_READY', count: updated }))
      ).catch(() => {});
    }
  })().finally(() => { _syncPromise = null; });
  return _syncPromise;
}

// === 404 fallback ===

async function respond404() {
  const cache = await caches.open(CACHE_NAME);
  const cached404 = await cache.match(BASE_URL + '404.html').catch(() => null);
  if (cached404) {
    const body = await cached404.text();
    return new Response(body, { status: 404, headers: { 'Content-Type': 'text/html' } });
  }
  return new Response('<h1>404 Not Found</h1>', { status: 404, headers: { 'Content-Type': 'text/html' } });
}

// === Request handlers ===

async function servePage(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  if (cached) return cached;

  try {
    const resp = await fetch(request);
    if (resp && resp.ok) {
      await cache.put(request, resp.clone());
      return resp;
    }
  } catch (e) { /* network failed */ }

  return respond404();
}

async function serveAsset(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  if (cached) return cached;

  try {
    const resp = await fetch(request);
    if (resp && resp.ok) {
      await cache.put(request, resp.clone());
      return resp;
    }
  } catch (e) { /* network failed */ }

  return new Response('Not found', { status: 404 });
}

function isPageRequest(request) {
  if (request.destination === 'document' || request.mode === 'navigate') return true;
  if (request.method !== 'GET') return false;
  const accept = request.headers.get('accept') || '';
  return accept.includes('text/html');
}

// === Events ===

self.addEventListener('install', (e) => {
  e.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    await self.clients.claim();
    await caches.keys().then(names => Promise.all(
      names.filter(n => n !== CACHE_NAME && n !== META_CACHE).map(n => caches.delete(n))
    ));

    // Open content cache first so it appears first in caches.keys().
    const cache = await caches.open(CACHE_NAME);

    // Fetch manifest and sync all pages.
    const manifest = await refreshManifest();

    // Prime the visible page immediately.
    try {
      const clients = await self.clients.matchAll({ includeUncontrolled: true, type: 'window' });
      const visible = clients.find(c => c.visibilityState === 'visible') || clients[0];
      if (visible) {
        const resp = await fetch(visible.url);
        if (resp && resp.ok) {
          await cache.put(visible.url, resp.clone());
        }
      }
    } catch (e) { /* non-fatal */ }
  })());
});

self.addEventListener('fetch', (e) => {
  const { request } = e;
  const url = new URL(request.url);

  if (url.origin !== self.location.origin) return;

  if (isPageRequest(request)) {
    e.respondWith((async () => {
      await getManifest(request);
      return servePage(request);
    })());
    return;
  }

  e.respondWith(serveAsset(request));
});
