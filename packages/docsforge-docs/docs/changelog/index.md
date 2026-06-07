# Changelog

All notable changes to DocsForge are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [10.8.9] — 2026-06-07

### Added

- **Full PWA / offline support** — DocsForge now generates a `manifest.json` and pre-caches all HTML pages during the service worker install phase, enabling full offline browsing of all documentation pages after the first visit.
  - **`manifest.json`** — Generated automatically with site name, description, theme color (extracted from palette), and start URL. Linked via `<link rel="manifest">` in the `<head>` of every page.
  - **Pre-caching all pages** — The service worker now receives a `__PRE_CACHE_PAGES__` placeholder that is replaced at build time with the complete list of all built HTML page URLs. During `install`, the SW caches every page so they work offline immediately without needing to visit each page first.
  - **Cache-first strategy** — The service worker now uses `cacheFirstWithNetworkFallback` for HTML documents (was `staleWhileRevalidate` which caused network requests on every navigation). This means pages load instantly from cache even online, with a background update.
  - **Offline fallback** — If a page is not cached and the user is offline, the SW serves the 404 page (or a generic offline message if 404 isn't cached).

### Changed

- **Service worker strategy** — Switched from `staleWhileRevalidate` to `cacheFirstWithNetworkFallback` for HTML pages and assets. This prioritizes offline reliability and instant loads over always-fresh content. For most documentation sites, this is the desired behavior.

### Fixed

- **Removed "Cyrus" from all docs** — Eliminated all remaining references to "Cyrus" from documentation, site footer, and copyright strings. The `license.md` and `docsforge.yml` site author/copyright now use "QQ" only.

## [10.8.8] — 2026-06-06

### Changed

- **Always dirty builds** — Removed the `build_type` parameter from `serve()` and all `dirty=False` defaults. All builds are now incremental by default. The `dirty` flag was a legacy concept that caused confusion — full rebuilds are only triggered when the config file changes (detected by hash), and `clean_directory` + `cache.invalidate()` are skipped unless the config changes.

## [10.8.7] — 2026-06-06

### Fixed

- **`docsforge serve` cache invalidation** — `DevServer.serve()` was not passing `build_type='dirty'` to `serve_module.serve()`, causing the dev server to do full rebuilds with cache invalidation on every file change. This made live reload painfully slow. The `build` command already did dirty/incremental builds by default; now `serve` does too.

## [10.8.6] — 2026-06-06

### Fixed

- **Asset 404s on sub-pages** — `base_url` computed by `get_relative_url()` returned `..` without trailing slash for pages at subdirectories. Without the trailing slash, `_get_relative_url` treated it as a filename (stripped it), causing CSS/JS/asset paths to resolve relative to the page directory instead of the site root. Added trailing slash normalization to `get_context()` and `_build_template()`.

## [10.8.5] — 2026-06-06

### Fixed

- **Sidebar race condition** — ThreadPoolExecutor parallel page builds caused multiple pages to be marked `active` simultaneously. Each `Page.active` setter propagates to its parent `Section`, so concurrent builds leaked active state between pages. This resulted in the sidebar showing multiple sections as expanded when only the current section should be. Restructured `_build_page` to hold the existing `RLock` for the entire template render + file write phase, ensuring only one page is ever active at a time.

## [10.8.4] — 2026-06-06

### Fixed

- **Search index 404 on non-root pages** — `base_url` in `build.py` was computed backwards: `get_relative_url('.', page.url)` returned the path *from* root *to* page instead of *from* page *to* root. The JS injected this into page config as `base`, then resolved `search/search_index.json` against it, producing a duplicated path like `/docsforge/getting-started/getting-started/search/search_index.json`. Fixed to `get_relative_url(page.url, '.')`.
- **Sidebar overlapping footer on desktop** — Added `max-height: calc(100vh - 2.4rem)` to `.md-sidebar__scrollwrap` at `min-width: 60em` to prevent the sidebar from extending past the viewport and overlapping the footer.

## [10.3.3] — 2026-05-17

### Added

- **Versioned service worker** — Each build generates a unique hash in the SW, ensuring browsers install the new version and purge old caches
- **Auto cache cleanup** — Old caches automatically deleted when new SW activates
- **Offline support** — All same-origin files cached; HTML uses network-first, assets use cache-first
- **PWA-ready** — Service worker registration in every built page

### Fixed

- Service worker scope set to `/` (root) instead of `/assets/javascripts/` so it can intercept all requests

## [10.3.2] — 2026-05-17

### Fixed

- Service worker scope fixed to `/` so it can cache blog posts and documentation pages
- Added `request.mode === "navigate"` check for better HTML page detection

## [10.3.1] — 2026-05-17

### Fixed

- `.icons/` directory now included in PyPI wheel build
- Added `artifacts` pattern in `pyproject.toml` to ensure Material theme icons are packaged

## [10.3.0] — 2026-05-17

### Added

- **TikZ diagram support** — Write TikZ diagrams in Markdown, automatically compiled to SVG at build time
- **Theme playground** — Interactive palette switcher with live preview
- **Blog plugin** — Built-in blogging with authors, tags, archive, pagination, and RSS feeds

### Fixed

- Source repo blank spot fixed (removed fixed 234px width when no stars/forks)
- Theme persistence across page navigation (uses `__md_scope` instead of per-page URLs)
- Palette toggle button highlight sync
- 404 page styling

### Changed

- Cleaned up unrelated development files from repo
- All repos use `main` as default branch

## [10.2.0] — 2026-05-16

### Added

- **Vendored mkdocs + Material** — Self-contained, no external dependencies
- **GitHub Pages deployment** — GitHub Actions workflow for auto-deployment
- **PyPI publishing** — Automated releases via GitHub Actions

## [10.1.0] — 2026-05-10

### Added

- **Zero-config Markdown** — 31 extensions loaded by default (all pymdownx + python-markdown). No `markdown_extensions:` config needed.
- **KaTeX math** — Vendored KaTeX (1.5MB) renders `$$...$$` inline and display math. No CDN, no config.
- **Pygments highlighting** — Syntax-colored code blocks at build time. No client-side JS.
- **Dark mode toggle** — Light/dark mode switch in header. Auto-detects system preference.
- **Auto-loaded plugins** — search, tags, blog, info, meta, minify, privacy all work without config.
- **Self-hosted fonts** — Privacy plugin downloads and caches Google Fonts locally.

### Changed

- **Config file** renamed from `properdocs.yml` to `docsforge.yml`
- **Theme namespace** changed from `mkdocs.themes` to `docsforge.themes`
- **Plugin system** — 6 plugins removed, 7 remain as built-in defaults

### Removed

- `typeset` — Users can write Unicode directly
- `optimize` — Requires external `pngquant` binary
- `social` — Requires Pillow + CairoSVG
- `projects` — Niche multi-project feature
- `offline` — Privacy plugin covers most use cases
- `group` — Plugin orchestrator (niche)

## [0.1.0] — 2025-05-10

### Added

- Initial release
