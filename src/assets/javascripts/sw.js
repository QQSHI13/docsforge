/**
 * DocsForge Service Worker
 *
 * Strategy: cache-everything, manifest-driven delta updates, no localhost
 * special-casing. After the first install every build output is cached, so
 * going offline gives the same experience as online.
 *
 *   install    : skipWaiting, no pre-cache.
 *   activate   : open cache, preload locale, prime the visible page through
 *                servePage(), claim, delete old caches, then fetch
 *                cache-manifest.json and sync every changed file.
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
const ACCESS_KEY = 'docsforge-access-times';

const BASE_URL = "__DOCSFORGE_BASE_URL__".replace(/\/?$/, '/') || self.location.pathname.replace(/sw\.js$/, '');
const ORIGIN_BASE = self.location.origin + BASE_URL;

const I18N_DB_NAME = 'docsforge-i18n';
const I18N_DB_STORE = 'preferences';
const I18N_LOCALE_KEY = 'preferred_locale';

const SYNC_CONCURRENCY = 6;
// Conservative per-download cost when budgeting the manifest sync against
// free space: each changed file reserved at a flat 20 MiB regardless of its
// real size, because the browser's quota-usage estimate lags behind in-flight
// writes. The sync stops downloading once the budget is exhausted instead of
// fetching files that will only be evicted again.
const DOWNLOAD_COST_BYTES = 20 * 1024 * 1024;
const QUOTA_MARGIN_RATIO = 0.1;

// In-memory manifest + dedupe promises.
let _manifest = null;
let _manifestRefresh = null;
let _syncPromise = null;
let _preferredLocale = null;
// URLs evicted by makeSpaceIfNeeded() since the last reconciliation. The
// manifest sync removes them from the persisted previous-files list before
// writing, so evicted files are never falsely recorded as cached.
let _evicted = new Set();

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
  // Always read from IndexedDB instead of trusting the cached value: the page
  // writes the preference BEFORE reloading, and the DOCSFORGE_SET_LOCALE
  // message may not have been processed when the reload's fetch arrives.
  // Caching (especially caching '') made the first locale switch serve the
  // previous language until a later reload.
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

async function getManifest() {
  const cached = await loadManifestFromCache();
  return cached;
}

// === Per-file hash and access-time stores (cross-SW-version) ===

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

async function readAccessTimes() {
  const cache = await caches.open(META_CACHE);
  const resp = await cache.match(ACCESS_KEY);
  if (!resp) return {};
  try { return await resp.json() || {}; } catch { return {}; }
}

async function writeAccessTimes(times) {
  const cache = await caches.open(META_CACHE);
  await cache.put(ACCESS_KEY, new Response(JSON.stringify(times)));
}

async function touchAccessTime(url) {
  try {
    const times = await readAccessTimes();
    times[url] = Date.now();
    await writeAccessTimes(times);
  } catch (e) { /* ignore */ }
}

// === Concurrency helper ===

async function runWithConcurrency(tasks, limit) {
  const results = [];
  const executing = [];
  for (const [index, task] of tasks.entries()) {
    const p = Promise.resolve().then(() => task());
    results[index] = p;
    const e = p.then(() => undefined);
    executing.push(e);
    if (executing.length >= limit) {
      await Promise.race(executing);
      const doneIndex = executing.findIndex(x => x === e);
      if (doneIndex !== -1) executing.splice(doneIndex, 1);
    }
  }
  await Promise.all(executing);
  return Promise.all(results);
}

// === Cache sync ===

function keyToUrl(key) {
  return new URL(key, ORIGIN_BASE).href;
}

function urlToKey(url) {
  const href = typeof url === 'string' ? url : url.href;
  if (!href.startsWith(ORIGIN_BASE)) return null;
  let key = href.slice(ORIGIN_BASE.length);
  // keyToUrl('./') resolves to ORIGIN_BASE itself (the root page), so its
  // inverse must map back to './', not the empty string. Otherwise the root
  // page is treated as an orphan and evicted on every manifest sync.
  return key || './';
}

// Does the build ship the file for this candidate URL? The manifest lists
// every output; a candidate absent from it cannot exist on the server. The
// manifest stores directory-index pages under their directory URL
// ('reference/'), not the 'reference/index.html' form, so normalize that.
// Returns true when no manifest is available (first load) to never block.
function manifestHasFile(manifest, url) {
  if (!manifest || !manifest.files) return true;
  let key = urlToKey(url);
  if (key === null) return true;
  if (key.endsWith('/index.html')) key = key.slice(0, -'index.html'.length) || './';
  return Object.prototype.hasOwnProperty.call(manifest.files, key);
}

// Actual byte size of a cached entry. Content-Length is exact for network
// responses (the stored body is exactly what the server sent); synthesized
// responses (404 pages, etc.) have no header, so measure the body directly.
async function measuredSize(cache, url) {
  try {
    const resp = await cache.match(url);
    if (!resp) return 0;
    const header = parseInt(resp.headers.get('content-length'), 10);
    if (Number.isFinite(header) && header > 0) return header;
    const body = await resp.clone().arrayBuffer();
    return body.byteLength;
  } catch (e) {
    return 0;
  }
}

// Storage estimate (usage + quota), or null when unavailable/unusable (the
// caller then relies on reactive quota handling).
async function storageEstimate() {
  if (!navigator.storage || !navigator.storage.estimate) return null;
  try {
    const est = await navigator.storage.estimate();
    if (est && typeof est.usage === 'number' && typeof est.quota === 'number' && est.quota > 0) return est;
  } catch (e) { /* ignore */ }
  return null;
}

// Free space per storage.estimate(), or null when unavailable.
async function availableBytes() {
  const est = await storageEstimate();
  return est ? Math.max(0, est.quota - est.usage) : null;
}

// Evict least-recently-used entries until `available + freed` covers
// requiredBytes, accounting each entry at its ACTUAL byte size (no guesses).
// Evicted entries are removed from the persisted previous-files list so a
// later manifest sync re-fetches them; returns true when enough space was
// freed for the caller to retry its cache.put().
async function makeSpaceIfNeeded(requiredBytes = 0) {
  const est = await storageEstimate();
  if (!est) return false;
  const available = Math.max(0, est.quota - est.usage);
  // A single resource larger than the whole quota can never be cached.
  if (requiredBytes > 0 && requiredBytes > est.quota) return false;
  const targetFree = Math.max(requiredBytes, Math.floor(est.quota * QUOTA_MARGIN_RATIO));
  if (available >= targetFree) return true;

  const cache = await caches.open(CACHE_NAME);
  const times = await readAccessTimes();
  const entries = [];
  for (const req of await cache.keys()) {
    const key = urlToKey(req.url);
    if (!key) continue;
    // Never evict the manifest itself or sw.js.
    if (key === MANIFEST_URL || key === 'sw.js') continue;
    entries.push({ url: req.url, time: times[req.url] || 0 });
  }
  entries.sort((a, b) => a.time - b.time);

  let freed = 0;
  for (const entry of entries) {
    if (available + freed >= targetFree) break;
    const size = await measuredSize(cache, entry.url);
    const deleted = await cache.delete(entry.url);
    if (deleted) {
      delete times[entry.url];
      _evicted.add(entry.url);
      freed += size;
    }
  }
  await writeAccessTimes(times);

  // Drop evicted entries from the persisted previous-files list so the next
  // manifest sync re-fetches them instead of believing they are cached.
  const evictedKeys = [];
  for (const url of _evicted) {
    const key = manifestKeyOf(url);
    if (key) evictedKeys.push(key);
  }
  if (evictedKeys.length > 0) {
    const prev = await readPrevFiles();
    let changed = false;
    for (const key of evictedKeys) {
      if (Object.prototype.hasOwnProperty.call(prev, key)) {
        delete prev[key];
        changed = true;
      }
    }
    if (changed) await writePrevFiles(prev);
  }
  return available + freed >= targetFree;
}

// Normalize a URL to its manifest key form ('./', 'second/', ...), matching
// how the build emits directory-index pages. Returns null for URLs outside
// the site or for the manifest/sw.js files themselves.
function manifestKeyOf(url) {
  let key = urlToKey(url);
  if (key === null) return null;
  if (key === MANIFEST_URL || key === 'sw.js') return null;
  if (key.endsWith('/index.html')) key = key.slice(0, -'index.html'.length) || './';
  return key;
}

async function putWithQuotaHandling(cache, request, response) {
  try {
    await cache.put(request, response.clone());
    await touchAccessTime(request.url);
    return true;
  } catch (e) {
    if (e && (e.name === 'QuotaExceededError')) {
      log('Quota exceeded, evicting LRU entries (measured)...');
      const sizeHint = response.headers.get('content-length');
      const required = sizeHint ? parseInt(sizeHint, 10) : 0;
      const freedEnough = await makeSpaceIfNeeded(required);
      if (freedEnough) {
        try {
          await cache.put(request, response.clone());
          await touchAccessTime(request.url);
          return true;
        } catch (e2) {
          log('Still failed after eviction:', e2.message);
        }
      } else {
        log('Could not free enough space for', request.url, '(required', required, 'bytes)');
      }
    } else {
      throw e;
    }
    return false;
  }
}

async function deleteOrphans(newFiles, prevFiles) {
  const cache = await caches.open(CACHE_NAME);
  const keys = await cache.keys();
  let deleted = 0;
  for (const req of keys) {
    const key = urlToKey(req.url);
    if (!key) continue;
    if (key === MANIFEST_URL || key === 'sw.js') continue;
    // Only evict entries that a previous manifest tracked and that have since
    // disappeared from the build. Ad-hoc entries cached at runtime (a page
    // served for a locale candidate, instant-navigation fetches, etc.) are not
    // listed in either manifest and must be kept.
    if (!Object.prototype.hasOwnProperty.call(prevFiles, key)) continue;
    if (Object.prototype.hasOwnProperty.call(newFiles, key)) continue;
    await cache.delete(req.url);
    deleted++;
  }
  if (deleted > 0) log('Deleted', deleted, 'orphaned cache entries');
}

async function syncCacheFromManifest(manifest) {
  if (!manifest) return;
  if (_syncPromise) return _syncPromise;
  _syncPromise = (async () => {
    const prevFiles = await readPrevFiles();
    const newFiles = manifest.files || {};
    const cache = await caches.open(CACHE_NAME);
    let updated = 0;

    // Budget the sync against the free space available NOW: every download
    // costs a flat DOWNLOAD_COST_BYTES (the estimate lags behind in-flight
    // writes), and the sync stops once the budget is exhausted instead of
    // fetching files that would only be evicted again. Files skipped here are
    // cached on demand when actually visited. A null budget (no usable
    // estimate) falls back to reactive quota handling.
    let budget = await availableBytes();
    const entries = Object.keys(newFiles);
    log('Syncing', entries.length, 'files from manifest...');

    const tasks = [];
    for (const key of entries) {
      const newHash = newFiles[key];
      if (prevFiles[key] === newHash) continue;
      if (budget !== null) {
        if (budget < DOWNLOAD_COST_BYTES) {
          log('Quota budget exhausted, stopping sync at', key);
          break;
        }
        budget -= DOWNLOAD_COST_BYTES;
      }
      tasks.push(key);
    }
    log('Syncing', tasks.length, 'changed files within quota budget...');

    const runTask = async (key) => {
      const newHash = newFiles[key];
      try {
        const fullUrl = keyToUrl(key);
        log('Caching:', key);
        const resp = await fetch(fullUrl, { cache: 'no-cache' });
        if (resp && resp.ok) {
          const ok = await putWithQuotaHandling(cache, fullUrl, resp);
          if (ok) {
            prevFiles[key] = newHash;
            updated++;
          } else {
            log('Not cached (quota):', key);
          }
        }
      } catch (e) {
        log('Failed to cache:', key, e.message);
      }
    };

    await runWithConcurrency(tasks.map(k => () => runTask(k)), SYNC_CONCURRENCY);

    // Never record evicted files as cached: drop every URL evicted during
    // this sync (or while it was running) from the previous-files list so the
    // next sync re-fetches what actually got evicted.
    for (const url of _evicted) {
      const key = manifestKeyOf(url);
      if (key && Object.prototype.hasOwnProperty.call(prevFiles, key)) {
        delete prevFiles[key];
        log('Unmarked evicted file:', key);
      }
    }
    _evicted.clear();
    await writePrevFiles(prevFiles);
    await deleteOrphans(newFiles, prevFiles);
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
  const locale = await readPreferredLocale();
  const candidates = [];
  if (locale) {
    candidates.push(BASE_URL + '404.' + locale + '.html');
  }
  candidates.push(BASE_URL + '404.html');
  for (const url of candidates) {
    const cached404 = await cache.match(url).catch(() => null);
    if (cached404) {
      const body = await cached404.text();
      return new Response(body, { status: 404, headers: { 'Content-Type': 'text/html' } });
    }
  }
  return new Response('<h1>404 Not Found</h1>', { status: 404, headers: { 'Content-Type': 'text/html' } });
}

// === Request handlers ===

function buildPageCandidates(url, preferredLocale) {
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
  // The locale-agnostic directory URL is the canonical default-locale address.
  candidates.push(url.href);
  if (url.pathname.endsWith('/')) {
    candidates.push(new URL(url.pathname + 'index.html', url.origin).href);
  }
  return candidates;
}

async function servePage(request) {
  const cache = await caches.open(CACHE_NAME);
  const url = new URL(request.url);
  const preferredLocale = await readPreferredLocale();
  const manifest = await loadManifestFromCache();

  const candidates = buildPageCandidates(url, preferredLocale);

  for (const candidate of candidates) {
    const cached = await cache.match(candidate);
    if (cached) {
      log('Serving page from cache:', candidate);
      await touchAccessTime(candidate);
      return cached;
    }
  }

  // Fetch the first candidate that exists on the server. Start with the
  // locale-specific file so translated HTML is cached under its real path.
  // When offline, skip the network attempts entirely — they can only fail —
  // and serve the cached 404 page immediately.
  if (navigator.onLine === false) {
    return respond404();
  }
  for (const candidate of candidates) {
    // Skip candidates the build never ships (e.g. index.en.html when 'en' is
    // the unsuffixed default locale): requesting them 404s on the server.
    if (!manifestHasFile(manifest, candidate)) {
      log('Skipping page candidate not in manifest:', candidate);
      continue;
    }
    log('Fetching page candidate:', candidate);
    try {
      const resp = await fetch(candidate);
      if (resp && resp.ok) {
        await putWithQuotaHandling(cache, candidate, resp);
        return resp;
      }
    } catch (e) { /* try next candidate */ }
  }

  log('Page unavailable, returning 404:', request.url);
  return respond404();
}

async function serveAsset(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  if (cached) {
    await touchAccessTime(request.url);
    return cached;
  }

  try {
    const resp = await fetch(request);
    if (resp && resp.ok) {
      await putWithQuotaHandling(cache, request, resp);
      return resp;
    }
  } catch (e) { /* network failed */ }

  return new Response('Not found', { status: 404 });
}

function isPageRequest(request) {
  if (request.destination === 'document' || request.mode === 'navigate') return true;
  if (request.method !== 'GET') return false;
  if (request.headers.get('X-DocsForge-Instant-Nav') === '1') return true;
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
    // Preload locale preference so servePage() doesn't open IndexedDB on the
    // first fetch.
    await readPreferredLocale();

    // Open content cache first so it appears first in caches.keys().
    const cache = await caches.open(CACHE_NAME);

    // Prime the visible page through servePage() so the cached file respects
    // the stored locale and is cached under its locale-specific path.
    try {
      const clients = await self.clients.matchAll({ includeUncontrolled: true, type: 'window' });
      const visible = clients.find(c => c.visibilityState === 'visible') || clients[0];
      if (visible) {
        log('Priming visible page:', visible.url);
        const resp = await servePage(new Request(visible.url));
        if (resp && resp.ok) {
          log('Primed visible page:', visible.url);
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
      await getManifest();
      return servePage(request);
    })());
    return;
  }

  e.respondWith(serveAsset(request));
});
