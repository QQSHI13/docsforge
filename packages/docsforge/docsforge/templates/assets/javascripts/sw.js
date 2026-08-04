/**
 * DocsForge Service Worker
 *
 * Strategy: cache-everything, manifest-driven delta updates, no localhost
 * special-casing. After the first install every build output is cached, so
 * going offline gives the same experience as online.
 *
 *   install    : skipWaiting, no pre-cache.
 *   activate   : open cache, prime the visible page, claim, delete old caches,
 *                then fetch cache-manifest.json and sync every changed file.
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

const I18N_DB_NAME = 'docsforge-i18n';
const I18N_DB_STORE = 'preferences';
const I18N_LOCALE_KEY = 'preferred_locale';

// In-memory manifest + dedupe promises.
let _manifest = null;
let _manifestRefresh = null;
let _syncPromise = null;
let _preferredLocale = null;

function log(...args) {
  console.log('[SW]', ...args);
}

// === i18n preference (IndexedDB) ===

function openI18nDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(I18N_DB_NAME, 1);
    req.onupgradeneeded = (e) => {
      e.target.result.createObjectStore(I18N_DB_STORE);
    };
    req.onsuccess = (e) => resolve(e.target.result);
    req.onerror = (e) => reject(e);
  });
}

async function readPreferredLocale() {
  if (_preferredLocale !== null) return _preferredLocale;
  try {
    const db = await openI18nDB();
    const tx = db.transaction(I18N_DB_STORE, 'readonly');
    const store = tx.objectStore(I18N_DB_STORE);
    const result = await new Promise((resolve, reject) => {
      const req = store.get(I18N_LOCALE_KEY);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    _preferredLocale = result || '';
  } catch (e) {
    _preferredLocale = '';
  }
  return _preferredLocale;
}

self.addEventListener('message', (e) => {
  if (e.data && e.data.type === 'DOCSFORGE_RELOAD_DETECTED') {
    log('Reload detected by page; refreshing manifest in background');
    refreshManifest().catch(() => {});
  }
  if (e.data && e.data.type === 'DOCSFORGE_SET_LOCALE') {
    const locale = e.data.locale || '';
    _preferredLocale = locale;
    openI18nDB().then((db) => {
      const tx = db.transaction(I18N_DB_STORE, 'readwrite');
      const store = tx.objectStore(I18N_DB_STORE);
      if (locale) {
        store.put(locale, I18N_LOCALE_KEY);
      } else {
        store.delete(I18N_LOCALE_KEY);
      }
    }).catch(() => {});
  }
});

// === Manifest helpers ===

async function loadManifestFromCache() {
  if (_manifest) return _manifest;
  try {
    const cache = await caches.open(META_CACHE);
    const resp = await cache.match(MANIFEST_URL);
    if (resp) {
      _manifest = await resp.json();
      log('Manifest loaded from meta cache:', _manifest.version);
      return _manifest;
    }
  } catch (e) { /* ignore */ }
  return null;
}

async function refreshManifest() {
  if (_manifestRefresh) return _manifestRefresh;
  _manifestRefresh = (async () => {
    try {
      log('Fetching manifest...');
      const resp = await fetch(MANIFEST_URL, { cache: 'no-cache' });
      if (resp.ok) {
        const clone = resp.clone();
        const data = await resp.json();
        const cache = await caches.open(META_CACHE);
        await cache.put(MANIFEST_URL, clone);
        _manifest = data;
        log('Manifest fetched:', data.version);
        await syncCacheFromManifest(data);
      } else {
        log('Manifest fetch returned non-ok status:', resp.status);
      }
    } catch (e) {
      log('Manifest refresh failed:', e.message);
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

    const entries = Object.keys(newFiles);
    log('Syncing', entries.length, 'files from manifest...');

    for (const key of entries) {
      const newHash = newFiles[key];
      if (prevFiles[key] === newHash) continue;

      try {
        const fullUrl = new URL(key, ORIGIN_BASE);
        log('Caching:', key);
        const resp = await fetch(fullUrl);
        if (resp && resp.ok) {
          await cache.put(fullUrl, resp.clone());
          prevFiles[key] = newHash;
          updated++;
        }
      } catch (e) {
        log('Failed to cache:', key, e.message);
      }
    }

    await writePrevFiles(prevFiles);
    log('Sync complete:', updated, 'files updated');

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
  const url = new URL(request.url);
  const preferredLocale = await readPreferredLocale();

  // Build locale-aware candidates. The cache manifest stores translated
  // siblings as <dir>/index.<locale>.html, while the default locale lives
  // under the locale-agnostic directory URL (e.g. <dir>/).
  const candidates = [];
  if (preferredLocale) {
    if (url.pathname.endsWith('/')) {
      candidates.push(new URL(url.pathname + 'index.' + preferredLocale + '.html', url.origin).href);
    } else if (url.pathname.endsWith('.html')) {
      candidates.push(new URL(url.pathname.slice(0, -5) + '.' + preferredLocale + '.html', url.origin).href);
    } else {
      candidates.push(new URL(url.pathname + '.' + preferredLocale + '.html', url.origin).href);
    }
  }

  // The request URL itself is the canonical locale-agnostic address for the
  // default locale (cached by syncCacheFromManifest as a directory URL).
  candidates.push(request.url);

  // Fallback to an explicit index.html for directory URLs.
  if (url.pathname.endsWith('/')) {
    candidates.push(new URL(url.pathname + 'index.html', url.origin).href);
  }

  for (const candidate of candidates) {
    const cached = await cache.match(candidate);
    if (cached) {
      log('Serving page from cache:', candidate);
      return cached;
    }
  }

  log('Page not in cache, fetching:', request.url);
  try {
    const resp = await fetch(request);
    if (resp && resp.ok) {
      await cache.put(request, resp.clone());
      return resp;
    }
  } catch (e) { /* network failed */ }

  log('Page unavailable, returning 404:', request.url);
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
  log('Installing...');
  e.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', (e) => {
  log('Activating...');
  e.waitUntil((async () => {
    // Open content cache first so it appears first in caches.keys().
    const cache = await caches.open(CACHE_NAME);

    // Prime the visible page so the current tab is offline-ready immediately.
    try {
      const clients = await self.clients.matchAll({ includeUncontrolled: true, type: 'window' });
      const visible = clients.find(c => c.visibilityState === 'visible') || clients[0];
      if (visible) {
        log('Priming visible page:', visible.url);
        const resp = await fetch(visible.url);
        if (resp && resp.ok) {
          await cache.put(visible.url, resp.clone());
          log('Cached visible page:', visible.url);
        } else {
          log('Failed to prime visible page:', visible.url, resp.status);
        }
      }
    } catch (e) {
      log('Error priming visible page:', e.message);
    }

    // Take control of existing clients.
    await self.clients.claim();
    log('Clients claimed');

    // Delete old content caches (but keep meta cache).
    await caches.keys().then(names => Promise.all(
      names.filter(n => n !== CACHE_NAME && n !== META_CACHE).map(n => caches.delete(n))
    ));

    // Fetch manifest and sync every build output in the background.
    log('Fetching manifest and syncing all files...');
    const manifest = await refreshManifest();
    if (!manifest) {
      log('No manifest available after activation');
    }
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

