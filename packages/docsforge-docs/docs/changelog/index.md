# Changelog

All notable changes to DocsForge are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [10.9.1] — 2026-06-11

### Fixed

- **CLI `--strict` flag moved to `build` subcommand** — The `--strict` flag was previously defined on the base `docsforge` group command, which was confusing since it only applied to `build`. Now it's only on `docsforge build --strict` where it belongs.

- **Streamlined `docsforge serve` CLI** — Removed unnecessary options:
  - `--no-open` removed — browser auto-open is harmless, always enabled
  - `--port` removed — automatically finds an available port starting from the configured one (e.g., 8000 → 8001 → 8002 if taken)
  - `--host` removed — replaced with single `--lan` flag that binds to `0.0.0.0` for network access
  - New usage: `docsforge serve --lan` to serve on all interfaces

## [10.9.1] — 2026-06-11

### Fixed

- **CLI `--strict` flag moved to `build` subcommand** — The `--strict` flag was previously defined on the base `docsforge` group command, which was confusing since it only applied to `build`. Now it's only on `docsforge build --strict` where it belongs.

- **Streamlined `docsforge serve` CLI** — Removed unnecessary options:
  - `--no-open` removed — browser auto-open is harmless, always enabled
  - `--port` removed — automatically finds an available port starting from the configured one (e.g., 8000 → 8001 → 8002 if taken)
  - `--host` removed — replaced with single `--lan` flag that binds to `0.0.0.0` for network access
  - New usage: `docsforge serve --lan` to serve on all interfaces

## [10.9.0] — 2026-06-11

### Added

- **Git revision dates** — Every page now automatically shows "Last updated" and "Created" dates from git history. No configuration required — works out of the box for any docs site in a git repository. The dates are read from `git log` and formatted as human-readable strings (e.g., "Jun 11, 2026"). The existing `source-file.html` template already supported this — now it's actually populated. Disable with `extra.git_revision_date: false` in docsforge.yml.

- **CLI serve options** — Added `--no-open`, `--port`, and `--host` flags to `docsforge serve`:
  ```bash
  docsforge serve --no-open          # Don't auto-open browser
  docsforge serve --port 3000        # Serve on port 3000
  docsforge serve --host 0.0.0.0     # Serve on all interfaces
  ```

### Changed

- **All theme features enabled by default** — The material theme now enables a rich set of features out of the box, so new sites get the full experience without needing a long `features:` list in docsforge.yml. New defaults include:
  - `content.action.edit`, `content.action.view`
  - `content.code.annotate`, `content.code.copy`
  - `content.tooltips`
  - `navigation.footer`, `navigation.indexes`, `navigation.sections`, `navigation.tabs`, `navigation.top`, `navigation.tracking`, `navigation.instant`, `navigation.instant.progress`
  - `search.highlight`, `search.share`, `search.suggest`
  - `toc.follow`

## [10.8.12] — 2026-06-11

### Optimized

- **Markdown instance reuse** — Added per-thread caching of `markdown.Markdown` instances in `pages.py`. Previously, every page created a new Markdown instance, re-initializing all extensions (pymdownx, codehilite, etc.) from scratch. With 36 pages and 10+ extensions, this was a significant overhead. Now:
  - Each thread gets a cached Markdown instance keyed by `(extensions, configs)`
  - Instances are `reset()` between pages instead of recreated
  - **Build time improvement**: ~2.5s (was ~3.4s) — **~25% faster**
  - Especially impactful for large sites with many Markdown extensions

- **Streamlined build.py** — Multiple internal optimizations:
  - Removed redundant `if _page_lock: with _page_lock:` branching in `_populate_page` (it was always called sequentially, no lock needed)
  - Removed nested `_do_build()` closure in `_build_page` that added function call overhead per page
  - Cached `files.documentation_pages()` result instead of calling it 3 times per build
  - Moved `hashlib` import from inline (inside `_inject_sw_build_hash`) to module top level
  - Simplified lock handling: always acquire lock in `_build_page`, removed `None` fallback path

- **Removed "Cyrus" from copyright headers** — Found and fixed 3 remaining files that still had "Cyrus" in the copyright string: `theme.py`, `preview.py`, `filter_config.py`

## [10.8.11] — 2026-06-08

### Changed

- **Lazy background caching** — Replaced the blocking `cache.addAll()` during service worker install with non-blocking incremental background caching. Previously, the SW tried to download all pages at once during install, which could block the initial page load. Now:
  1. The SW installs and activates immediately — the current page loads without delay.
  2. After activation, other pages are cached one by one in the background via `backgroundCachePages()`.
  3. The current page is already cached by the `fetch` handler when visited.
  4. A `DOCSFORGE_CACHE_COMPLETE` message is sent to all clients when done, so the UI can show a subtle indicator (e.g., "All pages available offline").

## [10.8.10] — 2026-06-08

### Fixed

- **Service worker pre-cache URL resolution** — `PRE_CACHE_PAGES` URLs were relative to the site root (e.g., `"./"`, `"advanced/customization/"`), but `cache.addAll()` inside the SW resolves URLs relative to the **SW script location** (`/assets/javascripts/sw.js`). This caused all pre-cache requests to fail silently, leaving the cache empty and breaking offline support. All pre-cache URLs now prefixed with `../../` so they correctly resolve from the SW to the site root.
- **Offline 404 fallback for subpath deployments** — `cache.match("/404.html")` was hardcoded to the domain root, which is wrong for sites deployed under a subpath (e.g., `/docsforge/`). The SW now computes `BASE_URL` from its own location and uses `BASE_URL + '404.html'` for the fallback.

### Added

- **PWA update notification** — When a new DocsForge version is deployed, the service worker activates and sends a `DOCSFORGE_UPDATE_READY` message to all open tabs. The page displays a fixed banner at the top: *"A new version of this documentation is available."* with **Refresh** and **Dismiss** buttons. Users can click Refresh to immediately load the new content, or Dismiss to keep reading the current version.
- **Periodic update checks** — The page checks for service worker updates every 5 minutes (`registration.update()`), so users get notified of new content even on long-running sessions without needing to reload manually.

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
- **KaTeX math** — Vendored KaTeX (1.5MB) renders `$$...$$` inline and display math. No CDN calls in the browser, no config.
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
