## [12.5.4] — Unreleased

### Added

- **Twemoji SVGs vendored** — the full twemoji set (4,000+ emojis, pinned
  to `jdecked/twemoji` v17.0.3, the maintained fork of the archived
  `twitter/twemoji`) ships inside the package. Unicode emojis
  (`:smile:`, `:us:`) are now inlined locally at build time, so no CDN
  (jsdelivr/maxcdn) is referenced anymore — falling back to the CDN only
  for codepoints missing from the vendored set.
- **License files shipped with bundled assets** — Mermaid (MIT) and KaTeX
  (MIT) licenses travel alongside the bundled scripts, and the lunr
  stemmer modules ship their MPL-1.1 license (the license must accompany
  the code in all cases).
- **Docker image runs as non-root** — the image now creates a `docsforge`
  user (uid 1000) and drops privileges (`USER docsforge`).
- **TikZ default math preamble** — bare diagram sources (no `\documentclass`)
  are now auto-wrapped in a standalone document with `amsmath`, `amssymb`,
  `tikz`, `pgfplots`, `tikz-cd` and `tkz-euclide` preloaded, so a diagram is
  just the `tikzpicture` body. New `tikz_preamble` config option injects extra
  preamble lines. `texlive-fonts-recommended` (amssymb/amsfonts) added to the
  Docker image — pgfplots, tikz-cd and tkz-euclide already ship in
  `texlive-pictures`.
- **TikZ SVGs embed fonts** — `dvisvgm` no longer runs with `--no-fonts`, so
  diagram text stays selectable and searchable; it falls back to outlined
  paths only when the TeX fonts are unavailable.

### Changed

- **Global `concurrency` setting** — new top-level `concurrency` key
  (default: CPU count − 1) sizes every parallel pool: Markdown page
  rendering, page building, TikZ compilation, social card generation and
  privacy downloads. The plugin-level `concurrency` options of `social` and
  `privacy` are removed — set `concurrency:` at the top level instead
  (breaking; plugin-level usage now warns).
- **PDF export tabs are memory-capped** — the base tab count comes from
  `--jobs`, else global `concurrency` (default CPU count − 1), and is capped
  by remaining memory (≈200 MiB per Chromium tab) so parallel rendering
  can't OOM the build.
- **`scripts/fetch_twemoji.py` merged into `build_frontend.py`** — refresh
  the vendored twemoji set with `python build_frontend.py --fetch-twemoji`
  (pinned tag), then a normal build syncs it into `docsforge/templates/`.
- **Migration scripts now served from the docs site** — `migrate.sh`,
  `migrate.ps1` and `migrate.py` live in the docs content and are copied
  into the built site (docsforge copies static files from `docs_dir`), so
  the one-liners are now:

  ```bash
  curl -fsSL https://qqshi13.github.io/docsforge/migrate.sh | bash
  ```

  ```powershell
  irm https://qqshi13.github.io/docsforge/migrate.ps1 | iex
  ```

  The scripts download `migrate.py` from the same site
  (`https://qqshi13.github.io/docsforge/migrate.py`) instead of the raw
  GitHub URL, and the getting-started migration guide now documents the
  automatic one-liner (was: "no automatic migration command").

## [12.5.3] — 2026-08-17

### Added

- **One-line migration scripts**: `curl | bash` (Unix) and `irm | iex`
  (PowerShell) convert an existing `mkdocs.yml` / `properdocs.yml` /
  `zensical.toml` to `docsforge.yml` automatically — navigation, theme,
  plugins, and extensions. Warns about anything it can't migrate
  (third-party plugins, `INHERIT`, hooks) and prints a report with contact
  info (email + issues).
- **`!!python/name:` tag support** in config loading — mkdocs configs
  commonly use `slugify: !!python/name:pymdownx.slugs.uslugify`; such
  configs (e.g. OI-wiki's) now parse and round-trip cleanly.
- **SECURITY.md** — private vulnerability reporting (GitHub advisory or
  email), supported-version policy.
- **Support page** (en + zh) with the migration one-liner, support channels,
  and a "what to include" checklist.
- **Sidebar navigation icons** on every docs page (Material set, en + zh).

### Changed

- **minify backend is now the Go minifier** (`minify-go`, wheels built from
  `tdewolff/minify` by our own cron workflow, incl. macOS arm64): the
  maintained forks (min-html, min-js, csscompress) are consolidated into one
  dependency. HTML pages now also minify inline `<style>`/`<script>` blocks;
  SVG default-valued attributes (e.g. `preserveAspectRatio="xMidYMid meet"`)
  are stripped, non-default values and case-sensitive names (`viewBox`) are
  preserved. Note: musllinux/Alpine is unsupported by the Go binding
  (c-shared `.so` cannot be dlopen'd on musl).
- **`paginate` vendored** into the package (`docsforge/paginate.py`) —
  another dormant dependency (2017) removed from the install.
- README: migration one-liner added; broken `install.sh`/`install.ps1`
  references fixed (the Studio extension ships as a release `.vsix`).

### Fixed

- Config parsing in `docsforge check` / CLI / PDF now routes through the
  docsforge YAML loader, so `!!python/name:` tags no longer crash config
  discovery.
- Migration script: `theme.name: null` (local-theme setups) defaults to
  `material`; external nav links are dropped with a hint (docsforge nav is
  internal-only).

## [12.5.2] — 2026-08-12

### Added

- **Blog RSS/Atom feeds**: the blog plugin now generates
  `feed_rss_created.xml`, `feed_rss_updated.xml`, and `feed_atom.xml` into
  the built site on every build (drafts excluded) — no more hand-maintained
  feed files. Disable with `plugins: [blog: {feed: false}]`.
- **Docs reference expansion**: 9 previously undocumented config keys
  (`exclude_docs`, `draft_docs`, `not_in_nav`, `extra_templates`, `tikz`,
  `hooks`, `watch`, legacy `remote_branch`/`remote_name`), `social` + `i18n`
  plugin option tables, a Lucide icon section, social-cards plugin docs, and
  the zero-config `extra.i18n_languages` form (en + zh).

### Fixed

- **Blog entrypoint stayed stale on incremental builds**: adding, editing, or
  removing a post did not re-render the blog index when the entrypoint's own
  source was unchanged. New `on_page_deps` plugin event + dependency-set
  change detection keep blog views fresh; no-op builds still skip.
- **Duplicate built-in plugin loading**: declaring a built-in plugin
  (`plugins: [blog: {...}]`) loaded a second auto-loaded instance with
  default config because the dedup check compared the un-namespaced name
  against the namespaced instance counter. Every declared core plugin was
  silently duplicated — now deduplicated correctly.
- **Demo content**: stale "31 extensions / 7 plugins" claims corrected;
  `i18n` added to the plugin list in the launch post.

### Changed

- **Dependency floor raised to current releases**: click 8.4.2, Jinja2 3.1.6,
  Markdown 3.10.3, PyYAML 6.0.3, watchdog 6.0.0, pymdown-extensions 11.0.1,
  backrefs 8.0, Pygments `>=2.20.0` (its `default` style output matches the
  committed `pygments.css`), and all other runtime deps; extras include
  playwright 1.62.0, pypdf 6.15.0, pillow 12.3.0, cairosvg 2.9.0.

## [12.5.1] — 2026-08-12

### Added

- **Incremental PDF export cache**: `docsforge build --pdf` now skips pages
  whose built HTML is unchanged since the last export (per-page content
  hashes in `.docsforge/cache/pdf.json`, the same mechanism as the site
  build). A single edited page re-renders only itself; orphaned PDFs are
  removed; only successfully rendered pages are recorded as cached.
- **`on_build_done` hook event**: runs once at the very end of a successful
  build — after page rendering, link/anchor validation, `on_post_build`
  plugins, asset optimization, PWA manifest + service worker generation, and
  the cache save — so hooks can inspect or post-process the final build
  output (e.g. `sw.js`, `cache-manifest.json`). Skipped when the build is
  aborted in strict mode.

### Changed

- **E2E tests honor `PLAYWRIGHT_CHROMIUM_EXECUTABLE`**: browser launch sites
  now use the same env var as `docsforge.pdf`, so a system browser can run
  the e2e suite locally without Playwright's bundled Chromium. Unset, the
  suite falls back to the bundled browser (CI) and skips gracefully when
  neither is available.

### Fixed

- **Docs corrections**: plugin count (8 core auto-load + social opt-in) and
  Markdown extension count (36 default + 3 built-ins) now match the engine;
  TikZ claims corrected (`.tex` files compiled at build, requires a LaTeX
  toolchain); stale "Insiders" references removed from the migration guide
  (mkdocs-material is migrating to Zensical); zh changelog backfilled for
  12.2.0–12.4.0; broken zh self-anchor fixed; icon counts corrected
  (16,500+ icons across five families).
- **Example-site integration test** pointed at the pre-12.5.0 `examples/site`
  path and silently skipped — now runs against `examples/sites/docsforge-demo`.
- **Demo site**: three new blog posts (TikZ diagrams, suffix-mode i18n,
  DocsForge Studio diagnostics); removed an orphaned page; `latex-equations.md`
  added to the nav; TikZ figures now resolve correctly.

## [12.5.0] — 2026-08-11

### Added

- **DocsForge Studio** (VS Code extension, `studio/`): renamed from
  `vscode-docsforge`. Full editor intelligence without a language server —
  diagnostics from the build's `validation.json` (broken links/anchors,
  footnotes), outline, folding, definition (ctrl+click), hover with
  broken-link notices, completion (`:material-`/`:lucide-` icons + doc
  paths), Find All References, and "Rename Document"/"Rename Anchor" that
  rewrite every inbound link (anchor-aware, translation-aware — renaming a
  `.zh` file renames its base + all locale variants). Explorer renames are
  intercepted automatically. "Fix all broken links (N)" code action, open
  link target, "Open Built Page" at the serve URL, format-on-save
  (opt-in), output panel inside the sidebar view.
- **Python environment management** in Studio: detects an interpreter
  (setting → remembered venv → `.venv` → PATH), checks pip + docsforge,
  offers venv / user / global installs.
- **Apache-2.0 license**: switched from LGPL-3.0-or-later; `NOTICE` with
  upstream attribution (ProperDocs/MkDocs BSD-2, Material MIT, icons).
- **Vendored KaTeX + Mermaid** as manifest-tracked devDependencies
  (previously frozen / hardcoded CDN): `copy_katex()` + `copy_mermaid()` in
  the frontend build; Mermaid loads from the local asset with a CDN fallback.
- **pygments.css generated at build time** from the installed Pygments
  (was a frozen snapshot).
- **Studio CI coverage**: `ci.yml` gained a `studio` job (npm ci + compile +
  lint + test) and absorbed `frontend.yml` as a `frontend` job.

### Changed

- **Social plugin is opt-in**: removed from the always-loaded core plugins
  (it needs pillow + cairosvg); enable via `plugins: [social]`. Docs and
  demo configs updated accordingly.
- **Link/anchor validation fixes**: anchor problems are now persisted to
  `validation.json` (they were logged but never stored — the Studio
  diagnostics had nothing to show); fixed a shared class-level
  `link_warnings` list that duplicated warnings across every page.
- **Renamed directories**: `vscode-docsforge/` → `studio/`,
  `docsforge-docs/` → `docs/`, `examples/site/` → `examples/sites/`
  (gitignore negation removed — the global `site/` rule covers it now).
- **TypeScript 6.0.3** in Studio (TS 7 is outside the typescript-eslint
  peer range).
- **Demo deploy**: wrangler-action v4 (no pinned wrangler version).

### Fixed

- **Social card font fetch could hang builds**: Google Fonts requests had no
  timeout (reverted, upstream-style). The default cache moved to
  `.docsforge/cache/social`.
- **Demo pipeline**: fixed the unprivileged `rm -rf /var/lib/apt/lists/*`
  that failed every run; `neural-network.tex` needed `amssymb`; added the
  missing `shannon-state-machine.tex`.

## [12.4.0] — 2026-08-09

### Added

- **Social cards plugin** (`social`): vendored port of mkdocs-material's
  social plugin, flattened into `docsforge/core/social.py` (OpenGraph card
  generation with two-stage parallel rendering, cache + manifest, font
  download). Each i18n locale page gets its own card. Needs
  `pip install "docsforge[social]"` (pillow + cairosvg).
- **Lucide icon set**: 2022 icons, usable as `:lucide-name:` inline or in
  theme icon configs; stroke-based rendering support for `.md-icon`.
- **Link/anchor validation on every build**: link and anchor problems are now
  reported on every build, not only the first — validation data is persisted
  per page in the build cache and re-checked for pages that are not re-rendered.
- **Programmatic palette API**: `window.docsforge.setPalette({scheme, primary,
  accent})` applies and persists themes from inline scripts/embeds (e.g. the
  theme playground), including combinations with no header toggle.
- Examples: the demo site now lives in-repo (`examples/site/docsforge-demo`),
  with a `custom_dir` override, a custom-filter plugin example, a hooks
  example, and a CI build test; the demo deploys to Cloudflare Pages via
  GitHub Actions (with TeX Live for TikZ).

### Changed

- **Repository hygiene**: all vendored mkdocs-material MIT headers removed
  (attribution consolidated in the license page); parity tooling removed;
  frontend reproducibility enforced in CI and at release time.
- The service worker revalidates the manifest on every real page load
  (Navigation Timing API) — a redeployed site is picked up without a hard
  refresh; the 5-minute update poll and the hard-refresh monitor were removed.
- Sidebar height uses `dvh` so the left (nav) and right (TOC) sidebars
  scroll identically on iOS/iPadOS.

## [12.3.0] — 2026-08-06

### Changed

- **Repository flattened.** The monorepo `packages/` level is gone: the core
  package, `pyproject.toml`, `src/`, `tests/`, and the frontend pipeline live
  at the repo root; the docs site is `docsforge-docs/` and the VS Code
  extension is `vscode-docsforge/`. All workflows, Dockerfile, dependabot
  config, and docs links updated; the full package README is now the root
  README.
- **svgo 4.** The icon pipeline now uses svgo 4 (config migrated; `viewBox`
  preservation unchanged). Verified byte-reproducible build output.
- **pnpm 11** for the frontend build (the workspace file uses pnpm 10+ syntax
  that pnpm 9 rejected), with the `minimumReleaseAge` supply-chain gate
  disabled so dependabot bumps to freshly published versions pass CI.
- **Frontend CI is reproducible again**: `frontend.yml` fails if the build
  output differs from the committed `docsforge/templates/`, and the release
  workflow rebuilds the frontend from `src/` before publishing the wheel.
- The transition-time parity harness and baseline snapshot were removed
  (their job is done); `build_frontend.py` moved to the repo root.
- CI runs the full test suite, including a dedicated Playwright e2e job.

## [12.2.0] — 2026-08-06

### Added

- **Frontend built from source.** The Material theme is vendored as source
  under `src/` (mkdocs-material v9.7.7) and built by an
  in-repo pipeline (`scripts/build_frontend.py`): esbuild bundles, sass +
  autoprefixer CSS, svgo icons, minified templates and service worker. Every
  shipped asset is reproducible, and parity gates
  (`scripts/check_frontend_parity.py`) verify it per area on CI.
- **DocsForge frontend customizations now live in source** instead of
  hand-patches to minified bundles: service worker (manifest-driven delta
  sync, locale-aware page serving, offline fast-404, manifest-aware candidate
  skipping), stateless i18n language switcher (IndexedDB-backed), per-locale
  search index, per-locale 404 pages, and the `X-DocsForge-Instant-Nav`
  header that keeps instant navigation on the preferred locale.

### Changed

- Service worker ships minified with `__DOCSFORGE_BASE_URL__` /
  `__DOCSFORGE_BUILD_HASH__` placeholders; `docsforge build` injects the real
  base path and a deterministic hash so SW bytes change between builds.
- The SW skips page candidates absent from `cache-manifest.json` — a stored
  preference for the (unsuffixed) default locale no longer requests
  `index.en.html` (404s).
- Blog posts without a `title:` front-matter key no longer crash the build
  when the meta plugin is active.
- `scripts/check_frontend_parity.py` gains `--vs-ref` (output diff vs a git
  ref, no build) and sentinel-marker checks.

## [12.0.0] — Unreleased

### Changed

- **BREAKING: Locale-agnostic i18n architecture.** Translated pages are now emitted as siblings (`index.html` and `index.<locale>.html` in the same directory) and share the same public URL. The service worker stores the user's preferred locale in IndexedDB and serves the matching sibling on every request. This removes `/<locale>/` sub-sites, fallback pages, per-locale asset copies, and link/asset rewriting.
- **i18n search is locale-aware.** Each locale has its own `search/search_index.<locale>.json`; the frontend loads the index for the currently displayed language instead of always searching the default locale.
- **i18n language switcher reloads the same URL.** Selecting a language writes the preference to IndexedDB and reloads the current page, so the switcher never produces stale locale-specific URLs.

### Removed

- **i18n `fallback_to_default` option.** It is now ignored because fallback pages are no longer generated.

## [11.5.4] — 2026-07-07

### Fixed

- **i18n link rewriting now handles unquoted and single-quoted `href` attributes.** The HTML minifier emits attributes like `href=second/`, which the link rewriter previously missed, causing locale pages to link back to the default-language site. It now rewrites double-quoted, single-quoted, and unquoted `href` values.
- **i18n `nav_translations` now apply to Page nav items.** Previously only Section titles were translated; Page nav items now use `nav_translations` too, with frontmatter titles used as the fallback when no explicit nav title or translation is configured.

## [11.5.3] — 2026-07-07

### Fixed

- **i18n fallback pages now inherit titles and nav overrides.** Fallback locale pages (and translated pages created before navigation runs) no longer render nav items as "None"; they use the default page title and any custom `nav` title configured for that entry.
- **Locale links now rewrite for all pages, not just nav pages.** Internal links from a translated page to a fallback/non-nav page now correctly stay inside the locale subtree instead of climbing out to the default-language URL.

## [11.5.2] — 2026-07-07

### Added

- **i18n asset fallback.** Translated assets (e.g. `assets/diagram.zh.png`) are emitted under the locale path (`zh/assets/diagram.png`). If a translation is missing, the default asset is copied there automatically, so locale sites never lose images, CSS, or other docs assets.
- **Per-locale Material UI language.** Translated pages now load the matching Material UI string file, so `<html lang>`, search placeholders, and the language-switcher label follow the page locale instead of staying in the default language.

### Fixed

- **False-positive nav warnings for translated pages.** `docsforge build` and `docsforge serve` no longer log "pages exist in the docs directory, but are not included in the nav" for translated `.zh.md` files handled by the i18n plugin.
- `docsforge check` now treats `material/i18n` as a built-in plugin instead of a third-party plugin.

## [11.5.1] — 2026-07-06

### Fixed

- **i18n language switcher used server-absolute URLs.** The alternate URLs included the `site_url` subpath, so when the template `url` filter resolved them relative to the current page on sites deployed under a path (e.g. `https://qqshi13.github.io/docsforge/`), the links pointed to `docsforge/docsforge/...`. The i18n plugin now emits page-relative URLs (`page.url`) so the switcher and `<link rel="alternate">` tags stay inside the docs root.

## [11.5.0] — 2026-07-06

### Added

- **Built-in i18n plugin (`material/i18n`).** Add translated files next to your default-language files (e.g. `index.zh.md` beside `index.md`) and DocsForge builds a default site at the root plus one sub-site per locale under `/<locale>/`. Supports fallback pages, per-language navigation/title translations, a header language switcher, `<link rel="alternate" hreflang="...">` tags, per-locale search indexes, and per-locale sitemaps.
- New documentation page: [Multi-language sites](../setup/i18n.md).

### Fixed

- Material theme now ships a default `palette` so builds no longer fail when `theme.palette` is omitted.
- Removed `properdocs_version`/`mkdocs_version` legacy fields from the template context.
- VS Code extension build restored by rolling TypeScript back to `^5.9.3` and `@types/node` to `^22.20.0` with `commonjs`/`node` module resolution.

## [11.3.12] — 2026-06-27

### Added

- **Browser E2E tests (Playwright).** A 5-test Chromium suite (`tests/e2e/`) covering the service-worker behavior that can't be unit-tested: SW installs and caches the visible page, offline reload serves the cached page, `search_index.json` is served, and hover-prefetch caches the destination so it loads offline. The tests skip gracefully when no browser is available (so the default `pytest` run is unaffected); a dedicated non-blocking `e2e` CI job on `ubuntu-latest` installs Chromium and runs `pytest -m e2e`.

## [11.3.11] — 2026-06-27

### Added

- **VS Code extension tests (10).** Added a mocha + ts-node suite for the extension's pure helpers: config-file discovery (`findConfig`/`hasConfig`, `.yml` preferred over `.yaml`) and server-URL extraction from stdout. Extracted the helpers into a vscode-free `src/pure.ts` (behavior-preserving) so they're testable without launching VS Code. CI now runs `npm test` in the `build-vsix` job; `test/` is excluded from the VSIX.

## [11.3.10] — 2026-06-27

### Added

- **Serve / live-reload unit tests (15).** Covers `_find_available_port` (free, in-use increment, all-in-use, firewall-dropped-SYN with the short-timeout WSL fix), `_serve_url`/`_normalize_mount_path`/`_try_relativize_path`, and the rebuild-queueing logic that guards against the infinite reload loop (events during a build are queued via `_pending_rebuild`, not signaled).

### Changed

- Extracted the live-reload file-watch callback to a testable `LiveReloadServer._on_file_event` method (behavior-preserving).

## [11.3.9] — 2026-06-26

### Added

- **Reproducible builds via `SOURCE_DATE_EPOCH`.** `get_build_datetime()` now honors the standard `SOURCE_DATE_EPOCH` environment variable (reproducible-builds.org). When set, the build date, page `update_date`, sitemap `<lastmod>`, and `sitemap.xml.gz` mtime are all derived from that timestamp instead of the wall clock — so two builds of the same source produce byte-identical output (verified: identical content hash across clean builds). Defaults to the current time when unset.

### Changed

- **Search index entries are now sorted by location** before serialization, guaranteeing byte-reproducible `search_index.json` even if the build loop populates entries in non-deterministic order.

## [11.3.8] — 2026-06-26

### Fixed

- **Template edits now trigger a full rebuild.** The build cache only tracked source-`.md` hashes, the config hash, and the package version — so editing `base.html`, a partial, or a `theme.custom_dir` template did not rebuild unchanged pages (stale output). The build now records a stat-only signature of all `.html`/`.xml` templates in the theme dirs (the 14k+ `.icons/` excluded) and forces a full rebuild when it changes. Editing `base.html` etc. now rebuilds every page.

## [11.3.7] — 2026-06-26

### Changed

- **Parallel Markdown rendering.** `_populate_page` (read source + `markdown.convert`, the CPU-heavy part of the build) now runs across a `ThreadPoolExecutor` (up to 32 workers). The per-thread `Markdown` instance makes `render()` thread-safe, so only the plugin event calls and `config._current_page` are serialized via a lock. Template rendering (`_build_page`) stays serial to avoid the sidebar-active race. Cold build of the docs site: ~10s → ~7s; output is byte-identical across builds (verified over 5 runs).

## [11.3.6] — 2026-06-26

### Fixed

- **DocsForge upgrades now trigger a full rebuild.** The build cache only tracked source-`.md` hashes and the `docsforge.yml` hash, so upgrading DocsForge (new theme templates / service worker / build logic) did not rebuild unchanged pages — the new SW and templates wouldn't reach the built site until a source file was edited. The cache now records the package version and forces a full rebuild when it changes.
- **Config changes now actually rebuild unchanged pages.** `cache.invalidate()` deleted disk files but left the planner's in-memory hashes intact, so a config/package change didn't rebuild pages whose source was unchanged (off-by-one: the change applied on the *next* build, not the current one). `planner.invalidate()` clears both in-memory and disk state. The `meta` (mtime/size hash cache) is retained across a version bump so the rebuild still skips re-reading unchanged sources.

## [11.3.5] — 2026-06-26

### Added

- **Hover/focus link prefetch.** Internal links are now prefetched on `mouseover`/`focusin` (fire-and-forget through the service worker's `serveCurrentPage`), so the destination page is already cached when the user clicks — page switches become instant. Same-origin only, deduped, skips same-page/anchor links.

### Fixed

- **SW update message aligned with the client.** The SW now posts `DOCSFORGE_UPDATE_READY` (the message name `base.html` already listens for) instead of the unused `docsforge-updated`.

## [11.3.4] — 2026-06-26

### Changed

- **Build: mtime+size pre-filter for file hashing.** `should_rebuild` and `cache-manifest.json` generation re-read and SHA-256'd every source `.md` on every build. They now consult a `{path: {mtime, size, hash}}` cache (`meta.json`) and reuse the cached hash when `stat()` reports the same mtime and size — a stat instead of a full read+hash. On a no-op build this makes the hashing phase stat-only (docs site: 0.87s → 0.66s; bigger gains on large sites).

## [11.3.3] — 2026-06-26

### Changed

- **Build: skip asset optimization when the site is unchanged.** `optimize_assets` re-scanned every HTML/CSS/JS on every build. It now runs only when a page was actually rebuilt or the source set changed; on a no-op incremental build it's skipped entirely (docs site: 1.61s → 0.87s).

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
  - Removed 42 committed PDF build outputs under `docsforge-docs/pdf/`; the directory is now gitignored.
  - `docs/blog/index.md` (auto-generated by the blog plugin) untracked and properly gitignored at the package level. The previous root-level `docs/blog/index.md` pattern was slash-anchored and never matched the real path under `docsforge-docs/`.
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
