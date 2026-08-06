# DocsForge frontend — upstream delta inventory

Base: **mkdocs-material v9.7.7** (vendored under `packages/docsforge/src/`).
Built by `scripts/build_frontend.py` into `packages/docsforge/docsforge/templates/`.

This is the living list of every intentional deviation from upstream Material.
Keep it in sync when you touch `src/`. Area-by-area parity checks (Phase 3)
whitelist these deltas; anything NOT listed here is a regression.

## Build pipeline (new, no upstream equivalent)

- `scripts/build_frontend.py` — esbuild (TS/JS bundles, `--jsx-factory=h` for
  preact so JSX never references `React`), sass + autoprefixer + esbuild (CSS),
  `html-minifier-terser --case-sensitive` (templates), `svgo` (icons), esbuild
  minify for `sw.js`, lunr stemmer copies.
- `svgo.config.js` — `removeViewBox: false` + `removeDimensions`.

## Templates (`src/templates/`)

- `base.html`
  - `/* DocsForge: Fix blank spot in source repository when no facts */`
  - `/* DocsForge: Fix sidebar height to prevent content overlapping footer */`
  - `Fix: pymdownx.tabbed generates labels without .tabbed-labels wrapper` —
    wraps `:scope > label` into `.tabbed-labels` before the bundle runs, also
    after instant navigation.
  - `Fix: Ensure palette toggle is visible and clickable even if bundle.js
    crashes` — inline palette init/migration independent of the bundle.
  - DocsForge i18n: inline `window.docsforge.setLocale` (IndexedDB +
    `DOCSFORGE_SET_LOCALE` postMessage to the SW).
  - Unregister stale out-of-scope service workers before registering the
    scoped one.
  - `DOCSFORGE_UPDATE_READY` / `DOCSFORGE_CACHE_COMPLETE` once-per-session logs.
  - Per-locale `search_index_url` (suffix-mode i18n: `search_index.zh.json`).
  - i18n alternate `<link rel=alternate>` loop with duplicate locale-agnostic
    hrefs (needs the alternate-integration fix, see JS section).
- `partials/i18n.html` — stateless language switcher: links are `href="#"`,
  click does `preventDefault()` + `stopPropagation()` (so instant navigation
  never sees the click), `setLocale(locale)` then `location.reload()` with no
  delay.

## JavaScript (`src/assets/javascripts/`)

- `integrations/instant/index.ts`
  - `handle()` skips clicks inside `[data-md-component="i18n"]` (language
    switcher owns its own navigation).
  - Updates the language-switcher active state after instant navigation.
- `integrations/alternate/index.ts` — upstream v9.7.7 selects **all**
  `link[rel=alternate]` (older bundles used `:not([hreflang])`). Under
  suffix-mode i18n the alternates are duplicate hrefs, so this integration
  fetches per-page `sitemap.xml` (404s). Must be disabled or the duplicate
  links suppressed when i18n is active.
- `sw.js` — DocsForge service worker: manifest-driven delta sync, locale-aware
  `servePage` (IndexedDB `preferred_locale`), `keyToUrl`/`urlToKey` inverse for
  `./`, orphan eviction only for previously-manifest-tracked entries.
- Preact JSX factory (`--jsx-factory=h`, `--jsx-fragment=Fragment`) so the
  bundle never references a global `React`.

## Other

- KaTeX used for math (vendored `assets/katex/`), mermaid via privacy-fetched
  asset, twemoji/fonts fetched by the privacy plugin (unhashed dest names —
  referenced name always matches copied file).
