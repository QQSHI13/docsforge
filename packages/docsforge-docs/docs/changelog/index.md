# Changelog

All notable changes to DocsForge are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [11.3.2] — 2026-06-26

### Changed

- **Build: skip the orphan-output scan when no source files were deleted.** `find_orphaned_outputs` walked the entire `site_dir` on every build, but orphaned outputs can only appear when a source is *removed*. The build now records the source-URI set (`sources.json`) and skips the `site_dir` walk when the set is unchanged or only grew since the last build. On a cache hit (typical incremental build) this removes a full output-tree traversal.

## [11.3.1] — 2026-06-26

### Changed

- **SW: conditional manifest fetch.** `fetchManifest` now uses `fetch(cache-manifest.json, { cache: 'no-cache' })` instead of cache-busting with `?v=Date.now()`. The static host returns **304** when the manifest is unchanged, so rapid navigations no longer re-download the full manifest each time — same freshness, less bandwidth.

## [11.3.0] — 2026-06-26

### Changed

- **Service worker redesigned around "current page first".** The SW now treats `docsforge serve` and a deployed site identically and prioritizes the page you're actually viewing:
  - **Install is non-blocking** — just `skipWaiting()`, no more pre-cache-all that held the SW inactive until every page was fetched.
  - **`serveCurrentPage(request, manifest)`** runs on every navigation/page-switch: it fetches the manifest once, serves the current page from cache instantly if its hash is current, otherwise fetches+caches the fresh page and displays it (falling back to the stale cache offline). This is a *separate function* from the background sync.
  - **`syncCacheFromManifest(manifest)`** runs in the background (throttled ≥10 min, deduped) using the *same* fetched manifest, caching every other page that is missing or whose hash changed.
  - **`activate` primes the visible page first** (the tab the user is on), then background-syncs the rest — so "first install caches the current page first" is literally true.
  - Applies to **page switches too**: programmatic HTML fetches (Material instant navigation) are detected via `Accept: text/html` and routed through `serveCurrentPage`, not just hard navigations.

### Fixed

- **Manifest sync no longer re-hashes every cached HTML body.** `cache-manifest.json` stores source-`.md` hashes but the SW caches built HTML, so the old body-hash comparison never matched and every page was re-fetched on every sync. The SW now diffs the manifest against the previously-synced per-file hashes **plus checks cache existence** — a page is re-fetched only when missing or actually changed. No body hashing.

## [11.2.1] — 2026-06-26

### Changed

- **Service worker: far more efficient cache syncing.** Previously `syncCacheFromManifest` ran on *every* navigation — a network fetch of `cache-manifest.json` plus a re-hash (SHA-256 of the full body) of *every* cached page on each navigation after a deploy. Now:
  - **Throttled** to at most once per 10 minutes (and deduped so concurrent navigations share one sync).
  - **Diff-based** — the previous manifest's per-file hashes are stored, so sync only re-fetches pages whose hash actually changed. Cached bodies are no longer re-hashed on every sync (only a one-time hash check the first time a URL is seen).
  - On the docs site (44 pages) this removes ~44 SHA-256 ops + a manifest fetch per navigation, replaced by a single throttled fetch that touches only changed pages.
  - The SW now posts a `docsforge-updated` message to open tabs when content changes (forward-compatible hook; harmless if no client listener is wired).

## [11.2.0] — 2026-06-26

### Changed

- **`docsforge serve` now uses the exact same service-worker caching strategy as a deployed site — no localhost special-casing.** The previous versions special-cased `localhost`/`127.0.0.1` (first a hard network-only bypass, then a network-first variant) to keep livereload fresh. That made dev behave differently from production and broke offline dev. The SW now treats localhost identically to any other host: cache-first for HTML/assets, stale-while-revalidate for the rest, with background manifest-sync. Consequence: livereload auto-reloads may serve cached content until the SW's background sync catches up — the same freshness model as the deployed site. Dev is now faithful to production, including offline support after the server stops.

## [11.1.9] — 2026-06-26

### Added

- **Docker image now publishes version-numbered tags.** Previously only `latest` and `sha-*` were pushed (the `type=semver` metadata never fired because the build job checks out a commit SHA, not the tag). Each release now also publishes `ghcr.io/qqshi13/docsforge:<version>` (e.g. `:11.1.9`) and `:<major>.<minor>` (e.g. `:11.1`) for stable releases.
- **Friendly, helpful GitHub release notes.** Release bodies are now generated from the matching CHANGELOG entry, with install/upgrade commands, Docker pull/run examples, and a VS Code extension download hint — instead of a bare "Full Changelog" link.

### Fixed

- **`docsforge serve` pages now work offline after the server stops.** The service worker had a hard localhost bypass: on `localhost`/`127.0.0.1` it fetched from the network with **no caching and no fallback**, so once you stopped the dev server (or went offline) every page was blank. It now uses **network-first** for localhost — fresh content while the server runs (so livereload stays loop-free, the original reason for the bypass) — and caches successful responses so visited pages survive after the server is closed. The stale-cache reload loop stays fixed because the SW never serves stale HTML during a reload.

## [11.1.8] — 2026-06-25

### Fixed

- **Config-check summary now appears at the start of `build`/`serve` output, not the end.** `check()` prints to stdout via `print()`, while the build logs to stderr via `logging` (unbuffered). When the two streams are merged and piped — i.e. CI, `docker run`, or any `| grep`/`| tail` — stdout is block-buffered and doesn't flush until process exit, so the check block landed after the build logs even though it ran first. `check()` now flushes stdout before returning. (Regression guard added: `test_regression_config_check_appears_before_build_logs`.)

## [11.1.7] — 2026-06-24

### Added

- **`docsforge serve --strict`** — the dev server now accepts `--strict` (matching `docsforge build`). Rebuilds treat warnings as errors; the server stays alive and logs the abort so you can fix issues without restarting. The flag propagates `strict=True` through `DevServer.serve` → `serve_module.serve` → `load_config`.
- **Docker: customizable PDF browser.** Documented how to point PDF export at a different Chromium/Chrome via `PLAYWRIGHT_CHROMIUM_EXECUTABLE` (override the path, fall back to Playwright's bundled browser, or mount a host binary). See `docs/advanced/docker.md`.

### Changed

- The Docker guide now lists all `--strict` / PDF-browser / `--jobs` options with copy-pasteable `docker run` examples.

## [11.1.6] — 2026-06-24

### Added

- **75 more tests** (154 total): `test_files.py` (File model, dest_uri/url mapping, `get_files` walk), `test_config.py` (load_config, defaults, env-tag substitution, validation), `test_init.py` (project scaffolding), `test_search.py` (SearchIndex entries/tags/jieba gating), `test_tags.py` (Tag model), `test_privacy.py` (FragmentParser, mime map), `test_minify.py` (JS/CSS/HTML minification), `test_meta.py` (meta-file merge).

### Fixed

- **`load_config` crashed with `NameError` on invalid YAML.** The `except yaml.YAMLError` handler referenced an unimported `yaml`, so a syntax error in `docsforge.yml` produced a raw `NameError: name 'yaml' is not defined` instead of a friendly error. (Found by `test_config.py::test_invalid_yaml_raises`.)

## [11.1.5] — 2026-06-24

### Added

- **Test suite.** DocsForge now ships a pytest suite (79 tests) covering the incremental cache, config loading, the CLI front-end, utils, end-to-end builds, and a regression file with one named guard per historical bug. Previously the project had zero tests.

### Fixed

Bugs found while writing the test suite:

- **Incremental cache now works for non-root pages.** `BuildPlanner.find_orphaned_outputs` only checked `docs/<name>/index.md` for an output at `site/<name>/index.html`, missing the common `use_directory_urls=True` mapping `docs/<name>.md` → `site/<name>/index.html`. Every non-root page was therefore deleted as "orphaned" at the start of each build and rebuilt from scratch, defeating the incremental cache for them. Second build of the docs site dropped from ~4.7s to ~0.9s.
- **`detect_environment` always reported `docs_dir_exists: False`.** It referenced `_open_config_file` without importing it (the import lived in a different function's scope); the resulting `NameError` was swallowed by a bare `except`, so `docs_dir_exists`/`has_index` were never populated.
- **`_open_config_file` rejected `pathlib.Path` arguments.** It only handled `str`/`IO`/`None`; a `Path` fell through to the file-descriptor branch and crashed on `.seek(0)`. Now accepts any `os.PathLike`.
- **`BuildPlanner.save` did not update the in-memory `config_hash`.** After writing the config hash to disk, a subsequent `should_full_rebuild` on the same planner instance still saw the stale (None) value and forced a full rebuild.
- **Blog plugin `on_shutdown` could crash the build.** `rmtree(self.temp_dir)` raised `FileNotFoundError` when the temp dir was already gone (repeated builds in one process); cleanup is now idempotent.

## [11.1.4] — 2026-06-24

### Fixed

- **Incremental cache dependency tracking actually works now.** The v11.1.3 implementation had two defects that made it a silent no-op:
  - `build.py` passed `page.content` (rendered HTML) to `DependencyTracker.get_file_deps`, but the `pymdownx.snippets` `--8<--` include markers are consumed during `md.convert()`. It now passes `page.markdown` (the raw source, which retains the markers).
  - Include paths were resolved only relative to the source file's directory, but `pymdownx.snippets` resolves relative to its configured `base_path` (docsforge doesn't set one, so the default is the current working directory / project root). Includes are now resolved against `docs_dir`, the source file's directory, and the cwd.
- **Failed builds are no longer cached.** In strict mode, `_build_page` re-raises, but the build loop still called `planner.update_cache` afterward — marking a broken page as up-to-date so the next run silently skipped it. The cache is now only updated for pages that built successfully.

## [11.1.3] — 2026-06-23

### Fixed

- **Incremental cache now tracks snippet includes.** `DependencyTracker.get_file_deps` was a stub returning `[]`, so editing a file included via `pymdownx.snippets` (`--8<-- "path"`) did not trigger a rebuild. Includes are now resolved relative to the source file and watched for changes. A latent bug in `BuildPlanner.update_cache` that never stored dependency hashes (making the dep check a no-op) was also fixed.
- **Removed dead `_OPTIONAL_PLUGINS` code path** in `cli_core._check_optional_deps` — the empty plugin→dependency map and its unused `plugin_names` loop. The real `jieba`/`docsforge[chinese]` check is retained.

### Changed

- **Repo hygiene — untracked build artifacts removed from git:**
  - Removed 42 committed PDF build outputs under `packages/docsforge-docs/pdf/`; the directory is now gitignored.
  - `docs/blog/index.md` (auto-generated by the blog plugin) untracked and properly gitignored at the package level. The previous root-level `docs/blog/index.md` pattern was slash-anchored and never matched the real path under `packages/docsforge-docs/`.
  - Deleted stale `docsforge-vscode-11.0.0-beta.2.vsix` from disk.

## [11.0.0b1] — 2026-06-19

### Added

- **VSCode Extension: Open Preview** — Sidebar button opens the dev server in VS Code's Simple Browser via `simpleBrowser.api.open`.
- **VSCode Extension: Open Docs** — Sidebar button opens the DocsForge documentation site.
- **VSCode Extension: Stop Build** — Sidebar button to cancel a running build.
- **VSCode Extension: Managed external server** — Detects `docsforge serve` started in a terminal via `.docsforge/server.json` pidfile.
- **Pidfile** — `docsforge serve` writes `.docsforge/server.json` with PID and URL for external tools.
- **Content-based cache busting** — Downloaded external assets include a content hash in the filename.
- **Docs badge** — Compact and standard DocsForge badges.

### Changed

- **Service worker: bypass cache for localhost** — SW detects `localhost`/`127.0.0.1` and fetches from network. Prevents stale-cache reload loop during dev.
- **Livereload: `_rebuilding` flag** — File changes during a build are queued, not acted on immediately. One final rebuild fires afterward.
- **Tags template layout flattened** — `fragments/tags/{layout}/tag.html` → `fragments/tags/{layout}-tag.html`, `listing.html` → `{layout}-listing.html`.

### Fixed

- **Asset optimizer: unquoted HTML attributes** — Made regex quotes optional to match Material's unquoted output.
- **Privacy plugin: `url_relative_to` argument order** — Path was from file to page instead of page to file.
- **Privacy plugin: path normalization** — Regex `/.` matched `.icons` → `_icons`. Fixed.
- **Webserver: `.well-known` route** — Chrome DevTools probes returned 404.
- **Infinite reload loop** — `_rebuilding` flag + SW localhost bypass.

### VSCode Extension

- Open Preview via `simpleBrowser.api.open`
- Open Docs sidebar button
- Progress notification dismisses on stop
- Pidfile detection with 3s polling
- Stop external server (kill by PID)
- Stop Build button
- Sidebar state sync for server and build status

## [10.9.9] — 2026-06-18

### Fixed

- **Favicon 404** — Asset optimizer regex made quotes optional.
- **Privacy font CSS path** — `url_relative_to()` argument order fixed.
- **Privacy path normalization** — `/.` regex too broad.

### Added

- **Pidfile** — `.docsforge-server.json` for external server detection.
- **VSCode Extension: Open Preview, Open Docs**.

## [10.9.8] — 2026-06-18

### Added

- **Unified release workflow** — `release.yml` with version bump, commit, tag, release, PyPI, VSIX.
- **DocsForge badges** — Compact (110×20) and standard SVG badges.
- **Docs: Render, DigitalOcean deployment guides**.

### Changed

- **Tags template layout flattened** — Subdirectory → prefix naming.

## [10.9.7] — 2026-06-18

### Added

- **Unified release workflow** — Replaces `publish.yml` + `bundle-extension.yml`.
- **VSCode Extension: sidebar improvements** — 10+ bug fixes.

## [10.9.6] — 2026-06-18

### Fixed

- **Privacy: nested URLs in downloaded CSS**.
- **Font-display swap for Google Fonts**.

### Added

- **Hash-based cache manifest** for offline sync.
- **`.well-known/` browser probes** — 200 + empty JSON.

## [10.9.5] — 2026-06-17

### Changed

- **Simplify build** — Always complete output.

### Fixed

- **WSL port detection** — Socket timeout.
- **SW only re-caches on content change**.

## [10.9.4] — 2026-06-17

### Fixed

- **Python `__version__` sync with release.**

## [10.9.3] — 2026-06-17

### Fixed

- **Hot-reload duplicate builds** — Race condition.

## [10.9.2] — 2026-06-17

### Fixed

- **Export plugin directory handling.**

## [10.9.1] — 2026-06-11

### Fixed

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
- **KaTeX math** — Vendored KaTeX (1.5MB) renders `$$...$$` inline and display math. No CDN calls for readers, no config.
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
