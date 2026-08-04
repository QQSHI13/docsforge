# i18n Architecture Rewrite Plan

## Status
Implementation in progress. Branch: `i18n-rewrite`.

## Decisions made

- **No backwards compatibility.** Old `/zh/page/` URLs will 404. Project is beta and has few users.
- **No automatic asset fallback.** Markdown authors explicitly reference the asset they want (`image.png` or `image.zh.png`). No build-time or SW-time asset swapping.
- **Keep pre-caching all pages.** The SW cache manifest includes every `index.<locale>.html`.
- **Instant nav cache disabled.** Instant navigation still intercepts clicks and swaps the DOM, but it always fetches through the SW instead of using its own in-memory page cache. This prevents stale content after locale switches.
- **Language switcher triggers full reload.** This resets instant nav state cleanly when the user changes language.

## Context

DocsForge currently builds i18n sites like mkdocs-static-i18n:

- Default language at site root: `/page/`
- Other locales under a path prefix: `/zh/page/`, `/de/page/`
- Each locale gets its own copy of assets under `/zh/assets/`, etc.
- Search indexes are per-locale (`/search/search_index.json` vs `/zh/search/search_index.json`), but the frontend on locale pages loads the wrong one because `base_url` is computed relative to the site root.

This architecture works but has three problems we want to fix:

1. **Search on locale pages uses the default-language index.** Root cause: `base_url` cannot be both site-root-relative (needed for theme assets) and locale-root-relative (needed for search).
2. **Storage bloat.** Fallback pages and docs assets are duplicated per locale.
3. **Reserved-name collisions.** A user file named `<locale>.md` collides with the locale homepage (`/zh/index.html`).

## Proposed new architecture

Locale-agnostic canonical URLs with locale-specific sibling files.

### Output layout

```
site/
├── page/
│   ├── index.html          # default / English
│   ├── index.zh.html       # Chinese translation
│   └── index.de.html       # German translation
├── assets/                 # shared once at root
├── search/
│   ├── search_index.json       # default
│   ├── search_index.zh.json    # Chinese
│   └── search_index.de.json    # German
└── sw.js
```

### URL semantics

- `/page/` serves English or a translated locale based on the user's stored preference.
- The service worker reads `preferred_locale` from `IndexedDB` and rewrites the request:
  - `/page/` → serve `/page/index.zh.html` if locale is `zh` and the file exists.
  - Otherwise serve `/page/index.html`.
- Hard refresh / first visit / no SW → default language is served.

### Storage model

- `preferred_locale` is stored in `IndexedDB` so the SW can read it.
- It is also mirrored to `localStorage` for synchronous page-side reads if needed.
- Palette stays in `localStorage` (page-only, sync read before first paint).

## Goals

1. Search on every page uses the correct per-locale index.
2. No duplication of fallback pages or untranslated docs assets.
3. No reserved-name collisions at the top level.
4. Offline behavior remains correct: the SW caches the pages the user visits in their preferred locale(s) plus default fallbacks.
5. Shared links still work; recipients may see their own preferred locale after SW activation.

## Non-goals

- Changing the nav configuration format (keeps explicit `nav` section in `docsforge.yml`).
- Supporting folder-mode locale detection (suffix only, already decided).
- Server-side redirects (zero backend).

## Breaking changes

This is a **breaking change** for any existing i18n deployment.

| Before | After |
|--------|-------|
| `/zh/page/` | `/page/` (SW serves `index.zh.html`) |
| `/zh/assets/...` | `/assets/...` |
| `/zh/search/search_index.json` | `/search/search_index.zh.json` |
| Language switcher links to `/zh/page/` | Sets `preferred_locale=zh` in IndexedDB and reloads same URL |

### Migration for existing sites

No backwards compatibility. Existing `/zh/...` URLs will 404. This is acceptable because the project is beta and has minimal usage.

## Detailed implementation changes

### 1. `docsforge/core/i18n.py`

- Change locale file output from `zh/page/index.html` to `page/index.zh.html`.
- Do **not** emit fallback pages. If `page.zh.md` does not exist, only `page/index.html` exists.
- Stop copying docs assets into `zh/assets/`. Assets stay at root and locale pages reference root assets.
- Remove internal-link locale rewriting (URLs are now locale-agnostic).
- Remove asset-link locale rewriting (authors explicitly reference assets).
- Update language-switcher generation: instead of emitting `/zh/page/` links, emit click handlers that set `preferred_locale` and reload.
- Keep `page.i18n_locale` metadata so templates know which physical file they are.

### 2. `docsforge/core/search.py`

- Emit per-locale indexes as siblings:
  - `search/search_index.json`
  - `search/search_index.zh.json`
  - `search/search_index.de.json`
- Each index contains only pages that have a translation for that locale.
- Default index contains all default-language pages.
- Include `search_index` URL in the page `__config`:
  - `index.html` → `"search_index": "search/search_index.json"`
  - `index.zh.html` → `"search_index": "search/search_index.zh.json"`

### 3. `docsforge/templates/assets/javascripts/sw.js`

- Open `IndexedDB` on activation/fetch and read `preferred_locale`.
- Intercept HTML requests (`isPageRequest`).
- For a request to `/page/` (or `/page/index.html`):
  - Determine active locale from IndexedDB.
  - Try cache match for `/page/index.<locale>.html`.
  - If found, serve it.
  - Otherwise serve `/page/index.html`.
- Update `syncCacheFromManifest` to cache all `index.<locale>.html` files listed in the manifest.
- Keep caching assets as today.

### 4. `docsforge/templates/base.html` and `bundle.min.js`

- Add inline script to:
  - Open IndexedDB and initialize `preferred_locale` if missing.
  - Mirror changes to `localStorage`.
  - Send current locale to the SW via `postMessage` as a fallback/sync mechanism.
- Patch `bundle.min.js`:
  - Use `config.search_index` for the search index URL.
  - Use `config.locale` for any locale-aware UI logic.
  - Disable instant nav's internal page cache so it always fetches through the SW.

### 5. `docsforge/build.py`

- Keep `base_url` site-root-relative for all pages (already true; no change needed).
- Update cache manifest generation to walk the new output structure correctly.
- Ensure `404.html`, `sitemap.xml`, and PWA manifest still work.

### 6. Tests

- `tests/unit/plugins/test_i18n.py`:
  - New output paths: `page/index.zh.html`.
  - No fallback page emitted for missing translations.
  - No `zh/assets/` duplication.
  - Locale-agnostic internal links.
- `tests/unit/plugins/test_search.py`:
  - Per-locale search indexes exist and contain only translated pages.
  - `__config` includes correct `search_index` URL.
- `tests/e2e/test_browser.py` or new SW tests:
  - SW serves `index.zh.html` when `preferred_locale=zh`.
  - SW falls back to `index.html` when no translation exists.
  - Hard refresh shows default language.

### 7. Documentation

- Update `packages/docsforge-docs/docs/setup/i18n.md` and `i18n.zh.md`:
  - Explain sibling-file output layout.
  - Explain IndexedDB locale preference.
  - Document that first visit / hard refresh shows default language.
  - Document search behavior per locale.
  - Document migration from old `/zh/page/` URLs.

## Risks and open questions

1. **SEO / social previews.** Search engines and crawlers see default language at canonical URLs. Accepted tradeoff, documented.
2. **Instant navigation interaction.** Decided: disable instant nav's internal cache; rely on SW. Language switcher triggers full reload.
3. ~~Redirect shims for old URLs~~ — decided: none.
4. ~~Asset fallback~~ — decided: none. Authors explicitly reference assets.
5. **Storage.** Fallback-page duplication is removed and docs assets are no longer copied per locale, but all `index.<locale>.html` files are still pre-cached. Net storage reduction depends on translation coverage.

## Testing strategy

1. Unit tests for new i18n file layout and search indexes.
2. Build `packages/docsforge-docs` and verify output structure.
3. Manual / Playwright test:
   - Open `/page/` with no SW → English.
   - Switch to Chinese → URL stays `/page/`, content is Chinese, `IndexedDB` has `zh`.
   - Reload → SW serves Chinese.
   - Hard refresh → English.
   - Search returns Chinese results only.
4. Verify old `/zh/page/` URLs 404 (no backwards compatibility).

## Rollback plan

- The branch `i18n-rewrite` is isolated from `main`.
- If the rewrite is rejected, delete the branch and `main` remains unchanged.
- If partially adopted, individual pieces (search fix, asset deduplication) can be cherry-picked separately.

## Decision checklist before implementation

- [x] Option A: language switcher sets locale and reloads same URL.
- [x] No backward-compatibility shims for old `/zh/page/` URLs.
- [x] No automatic asset fallback; authors explicitly reference assets.
- [x] Keep pre-caching all pages.
- [x] Disable instant nav's internal cache; rely on SW cache.
- [x] Language switcher triggers full reload.
