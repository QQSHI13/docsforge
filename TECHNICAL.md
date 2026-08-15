# DocsForge — Technical Reference

This file documents what every part of the codebase does, how the pieces fit
together, and the design decisions behind them. It is the canonical reference
for anyone (human or agent) working in this repository. `CONTRIBUTING.md` is
the shorter contributor entry point; `AGENTS.md` is a symlink to it.

---

## 1. Architecture overview

DocsForge is a static site generator that bundles **everything** in one Python
package:

```
Markdown + docsforge.yml
        │
        ▼
docsforge/ (Python engine: ProperDocs/MkDocs fork + core plugins)
        │
        ▼
rendered pages + static assets
        │
        ├── docsforge/templates/  ← Material theme + JS/CSS/icons (built from src/)
        ├── .docsforge/cache/     ← incremental build cache (hashes, deps, validation.json)
        └── site/                 ← final output
```

Key properties:

- **Zero-config**: core plugins auto-load; 31 Markdown extensions
  pre-configured; no `plugins:` section needed (social is the only opt-in core
  plugin).
- **Offline-first**: a service worker with a build-hash manifest caches every
  page and asset; the site works without a network after first load.
- **Incremental**: content-hash dirty detection, dependency tracking, per-page
  validation persisted to the cache and re-checked every build.
- **i18n by suffix**: `index.md` + `index.zh.md` + any locale, single-file
  variants instead of per-locale trees.

---

## 2. CLI (`docsforge`)

`__main__.py` (Click) exposes:

| Command | What it does |
|---------|-------------|
| `docsforge` (bare) | Shows help, or starts interactive init if no project |
| `docsforge build` | Production build (always incremental). Flags: `--strict`, `--pdf`, `--jobs` |
| `docsforge serve` | Dev server (`--no-open`, `--lan`) |
| `docsforge check` | Config validation (lightweight) or `--fix` to auto-repair |
| `docsforge init` | Interactive project wizard |

`cli_core.py` holds the backend logic (independent of the CLI): config
discovery (`docsforge.yml`/`docsforge.yaml`), `Validator.check`,
`BuildEngine`, `DevServer`, `AutoRouter` (bare invocation routing), and the
optional-dependency checker (`_check_optional_deps`).

---

## 3. Config

- `config_base.py` — `Config` base class + `load_config()` (YAML → config
  object), schema generation.
- `config_defaults.py` — `DocsForgeConfig`: every config key. Notable ones:
  `site_name`, `site_url`, `nav`, `theme`, `docs_dir` (default `docs`),
  `site_dir` (default `site`), `use_directory_urls` (default True),
  `markdown_extensions` (31 preconfigured), `tikz` (bool, optional),
  `plugins` (default `[]` — core plugins still auto-load), `privacy`
  (default True — external assets fetched + inlined), `hooks` (Python module
  plugins), `watch`, and `validation` (link/anchor warning levels, see §6).
- `config_options.py` — the option type system (`Type`, `Choice`, `Optional`,
  `URL`, `Dir`, `Plugins`, `Nav`, `MarkdownExtensions`, `SubConfig`,
  `PropagatingSubConfig`, `Deprecated`, `ListOfItems`, `DictOfItems`, ...).
  `Plugins.run_validation` decides which core plugins auto-load.
- `filter_config.py` — `get_schema()` for JSON schema export.

### Nav

Explicit schema (`nav:`) is the modern form:

```yaml
nav:
  - title: Getting started
    path: getting-started.md
    i18n:
      zh: 入门
    children:
      - title: Installation
        path: getting-started.md
```

Legacy shorthand (`- Title: path`) still works but warns. `nav.py` builds
`Navigation`/`Section`/`Link`, adds parent links, previous/next links, and
resolves explicit entries (including i18n titles).

---

## 4. Build pipeline (`build.py`)

The `build()` function, in order:

1. `_collect_files_and_nav()` — compiles TikZ (if enabled), collects files
   from `docs_dir` + theme, runs `on_files` plugins, sets exclusions
   (`exclude_docs`, `draft_docs`, `not_in_nav`), removes orphaned outputs,
   builds navigation.
2. Renders pages (thread pool, one thread per page): `Page.render()` applies
   the Markdown pipeline (preprocessors → convert → treeprocessors →
   postprocessors), extracts anchors (`present_anchor_ids`), links
   (`links_to_anchors`), titles, TOC; per-page `link_warnings` collected by
   the relative-path treeprocessor.
3. `_write_outputs()` — writes rendered pages, updates the cache
   (`planner.update_cache`), serializes per-page validation
   (`_serialize_validation`).
4. `_finalize_build()` — restores validation for un-rendered pages
   (`_restore_validation`), runs the anchor/link validation pass **on every
   build** (validate first, then emit), re-serializes validation for all
   pages, runs `on_post_build`, optimizes assets (`optimize_assets`),
   generates the PWA manifest + service worker (see §8), saves the cache.

### Incremental cache (`cache.py`)

- `CACHE_DIR = .docsforge/cache`, `CACHE_VERSION = 1`.
- `FileHasher` — SHA-256 content hashing (`hash_file`, `hash_string`).
- `DependencyTracker` — tracks snippet includes (`--8<-- "path"` and
  `-8<-- 'path'` lines, with optional `file:5,10` line ranges) so a change to
  an included file dirties its consumers. `get_file_deps()` parses a page's
  raw markdown for include markers.
- `BuildPlanner` — dirty-page detection from hashes/deps/config/theme/nav
  signatures; orphan-output cleanup (skipped when the source set is unchanged
  or only grew); `validation.json` persistence (`get_validation`/
  `set_validation`), keyed by source uri →
  `{warnings: [[level, msg]], links: {target: {anchor: original}}, anchors: []}`.
  `save()` writes hashes/deps/config-hash/version/sources/meta/pkg-version/
  theme-sig/nav-sig/validation atomically (tmp + rename).

### Files / pages

- `files.py` — `Files` collection, `File` (src_uri, dest_uri, url, page),
  `InclusionLevel` (included/not_in_nav/excluded), `get_files()`,
  `set_exclusions()`, `file_sort_key`.
- `pages.py` — `Page` (render, TOC, anchors, `link_warnings`,
  `validate_anchor_links`), markdown treeprocessors:
  - `_ExtractAnchorsTreeprocessor` — collects element `id`/`name` attributes.
  - `_RelativePathTreeprocessor` — resolves relative links/images against
    the source file, rewrites them relative to the output page, records
    `links_to_anchors`, and **collects warnings** (missing targets,
    unrecognized links, excluded targets, absolute-link hints with
    suggestions) into `page.link_warnings`.
  - `_RawHTMLPreprocessor`/`_HTMLHandler` — parses raw HTML blocks so
    anchors/links inside them are validated too.
  - `_ExtractTitleTreeprocessor` — pulls the first `# Heading` as the page
    title when front-matter has none.
  - `validate_anchor_links()` — cross-checks every recorded
    `target#anchor` against the target page's `present_anchor_ids`;
    appends deduped warnings (self-links: "no such anchor on this page";
    cross-links: "the doc 'x' does not contain an anchor '#y'").

---

## 5. Core plugins (`docsforge/core/`)

### Plugin system (`plugin_base.py`)

- `BasePlugin` with the mkdocs-compatible event API:
  `on_startup`, `on_shutdown`, `on_serve`, `on_config`, `on_pre_build`,
  `on_files`, `on_nav`, `on_env`, `on_post_build`, `on_page_deps`,
  `on_build_error`, `on_build_done`,
  `on_pre_template`, `on_template_context`, `on_post_template`,
  `on_pre_page`, `on_page_read_source`, `on_page_markdown`,
  `on_page_content`, `on_page_context`, `on_post_page`.
- `event_priority(priority)` decorator for ordering.
- Entry points: `docsforge.plugins` group; theme-namespaced (`material/*`).
  `get_plugins()` reads them via importlib.metadata. Core plugins load
  automatically via `config_options.Plugins.run_validation` — except
  **social** (opt-in, needs pillow + cairosvg) and **privacy** (loaded only
  when `privacy: true` config).

### The plugins

| Plugin | What it does | Load |
|--------|-------------|------|
| `search` | Lunr.js full-text search index (client-side, offline); per-locale indexes; Chinese via jieba when installed; entries cache in `.docsforge/cache` | auto |
| `meta` | OpenGraph / social metadata injection | auto |
| `tags` | Tag system with tag pages (`/tags/` + per-tag listings) | auto |
| `blog` | Blog: posts, authors, categories, archive, RSS; auto-generates `docs/blog/index.md` at build | auto |
| `info` | Admonition callouts (material's info plugin) | auto |
| `minify` | HTML/CSS/JS minification (min-html fork of the minify-html Rust crate + csscompress + min-js fork); source-map stripping | auto |
| `i18n` | Suffix-mode i18n (see §7) | auto |
| `privacy` | Fetches + inlines external assets (Google Fonts, CDN scripts) at build; cache under `.docsforge/cache/privacy` | when `privacy: true` |
| `social` | Social cards (OpenGraph PNG generation), two-stage parallel rendering, font download, cache under `.docsforge/cache/social` | opt-in via `plugins: [social]` |

`docsforge/check.py`'s `BUILTIN_PLUGINS` includes all 9; `AUTOLOAD_PLUGINS`
excludes social (declaring it doesn't warn). Social's heavy deps
(pillow + cairosvg) are the `docsforge[social]` extra; `docsforge[pdf]` is
playwright + pypdf; `docsforge[chinese]` is jieba; `docsforge[all]` is all of
them.

---

## 6. Validation (`validation.*` config)

`DocsForgeConfig.validation` controls warning levels (Python logging levels:
`debug/info/warn/error`):

- `validation.nav.omitted_files` (info), `.not_found` (warn),
  `.absolute_links` (info)
- `validation.links.not_found` (warn), `.absolute_links` (info),
  `.unrecognized_links` (info), `.anchors` (info)

Link/anchor problems are collected per page (`page.link_warnings`) during
render, persisted to `.docsforge/cache/validation.json` (keyed by src_uri:
`{warnings: [[level, msg]], links: {target: {anchor: original}}, anchors: []}`),
restored for un-rendered pages, and re-emitted **every build** — a broken
cross-link surfaces even when only the *target* page changed. The VS Code
extension reads this file for diagnostics.

Warning message formats (parsed by the extension):
- `Doc file 'x.md' contains a link 'y.md', but the target is not found among documentation files.` (+ "Did you mean '...'?" suggestions)
- `Doc file 'x.md' contains a link to 'y.md' which is excluded from the built site.`
- `Doc file 'x.md' contains a link '#anchor', but there is no such anchor on this page.`
- `Doc file 'x.md' contains a link 'y.md#a', but the doc 'y.md' does not contain an anchor '#a'.`
- `Doc file 'x.md' contains an unrecognized relative link '...'`

---

## 7. i18n (suffix mode)

`core/i18n.py` — configured via `extra.i18n_languages`:

```yaml
extra:
  i18n_languages:
    - locale: en
      name: English
      default: true
    - locale: zh
      name: 中文
```

- Locale variants are **sibling files**: `index.md` (default) + `index.zh.md`.
- `on_files` creates per-locale File objects (locale suffix parsed from the
  filename); `on_nav` clones nav with per-locale titles (`i18n: {zh: 首页}`);
  `on_page_context` fixes locale titles; `on_page_content` injects
  alternate-language `<link rel="alternate">` tags; `on_post_build` writes
  the locale switcher data; `on_serve` handles locale reconfiguration.
- The theme's i18n widget is **stateless** (fixed the instant-nav state bug),
  persists language in localStorage + IndexedDB (`docsforge-i18n` DB,
  `preferences` store, `preferred_locale` key), works on 404 pages too.
- `window.docsforge.setLocale(locale)` is the programmatic API; it notifies
  the service worker (`DOCSFORGE_SET_LOCALE`) so fetches honor the preference.

---

## 8. Service worker & PWA

### Build-time injection (`build.py`)

`_generate_pwa_manifest_and_precache()`:

1. Collects pre-cache URLs: every documentation page (`file.url`), static
   templates (`404.html` → `/404.html`, others → `name/`), the homepage
   (`./`), plus `cache-manifest.json`.
2. Converts them relative to the SW script location (site root) and dedupes.
3. Injects into `sw.js` (copied from `assets/javascripts/sw.js` to site root):
   - `__PRE_CACHE_PAGES__` → the JSON URL list (legacy field; the new SW is
     manifest-driven and ignores it, but the substitution remains).
   - `__DOCSFORGE_BASE_URL__` → the site base path from `site_url`
     (e.g. `/docs/`), so the SW works under a subpath.
   - `__DOCSFORGE_BUILD_HASH__` → a **deterministic** 12-hex hash of (SW
     content + precache list + config file bytes). Identical inputs → same
     hash, so no-op builds don't churn the SW; any change → new hash → the
     browser installs a new worker.
4. Writes `site/sw.js` and removes the template copy from `assets/`.
5. Writes `manifest.json` (name, short_name, description, start_url,
   display, theme_color, icons).

### `cache-manifest.json` format

Lists every built file with its content hash:

```json
{
  "version": "<hash of all file hashes>",
  "files": { "assets/javascripts/bundle.min.js": "abc123...", "index.html": "def456..." }
}
```

Used by the SW for hash-based invalidation: on sync, files whose hash changed
are re-fetched; files no longer in the manifest are evicted.

### Service worker (`src/assets/javascripts/sw.js`)

- **Caches**: `docsforge-<BUILD_HASH>` (content), `docsforge-meta`
  (manifest + previous-files list).
- **Constants**: `BUILD_HASH`, `BASE_URL` (with trailing-slash normalization),
  `ORIGIN_BASE`, `SYNC_CONCURRENCY = 6`, quota margins.
- **IndexedDB**: `docsforge-i18n` (locale preference).
- **Messages**:
  - `DOCSFORGE_RELOAD_DETECTED` (from the page, on Navigation Timing
    `nav.type === 'reload' || 'navigate'`) → refresh the manifest in the
    background and sync changed files.
  - `DOCSFORGE_SET_LOCALE` → persist the locale to IDB (the page writes
    localStorage *before* reloading so the fetch sees it).
  - `DOCSFORGE_UPDATE_READY` → broadcast to clients after a sync updated N
    files.
- **Manifest sync**: fetch `cache-manifest.json` (`cache: 'no-cache'`),
  diff against the previous files list, fetch changed URLs (concurrency 6),
  evict orphaned entries (LRU by access time when quota exceeded, plus
  manifest-driven eviction for files no longer tracked).
- **Fetch strategy**: pages served from cache with background revalidation;
  static assets cache-first; navigation requests matched against the manifest
  (`manifestHasFile`) so pages absent from the manifest never 404 as
  `index.en.html` style false positives. Hard refreshes and back/forward
  (`nav.type === 'back_forward'`) are deliberately **not** treated as
  revalidation triggers (design decision).
- **Quota handling**: on QuotaExceeded, evicts LRU entries (using
  `docsforge-access-times`), with a configurable margin, and retries.

---

## 9. Frontend build (`build_frontend.py`) + `src/`

- `ROOT` = repo root, `SRC = src/`, `OUT = docsforge/templates/`,
  `NODE_MODULES = node_modules/`.
- Steps:
  - `copy_icons` — svgo-optimize icon sets from node_modules into
    `src/templates/.icons/` (material from `@mdi/svg`, lucide from
    `lucide-static`, octicons from `@primer/octicons`, fontawesome, simple
    icons), plus their license files.
  - `copy_icons_to_out` — sync `.icons/` into `docsforge/templates/`.
  - `copy_templates` — copy + minify HTML templates (html-minifier-terser),
    skipping `.icons/`.
  - `build_typescript` — esbuild bundles `src/assets/javascripts/*.ts` →
    `bundle.min.js` + `workers/search.min.js`.
  - `build_styles` — sass → autoprefixer → postcss (with inline-svg for
    `svg-load()` icons) → cssnano → `main.min.css` + `palette.min.css`.
  - `generate_pygments_css` — Pygments `HtmlFormatter(style='default')`
    `.highlight` rules → `assets/stylesheets/pygments.css`.
  - `copy_lunr` — lunr-languages stemmers (20+ locales) + `tinyseg.js` +
    `wordcut.js`.
  - `copy_katex` — katex dist (min.js, min.css, contrib, fonts).
  - `copy_mermaid` — mermaid.min.js.
  - `copy_sw` — esbuild-minify `sw.js`, preserving the `__DOCSFORGE_*__`
    placeholders for build.py injection.
- `src/assets/javascripts/sw.js` — the service worker source; build.py
  injects base URL + build hash at site-build time (see §8). Mermaid loads
  from the local asset via `window.docsforge.mermaidUrl` (set in base.html),
  with an unpkg CDN fallback.
- The **frontend CI job** asserts `git diff --exit-code -- docsforge/templates`
  after a rebuild — committed templates must match the build exactly.

### Theme templates (`src/templates/` / `docsforge/templates/`)

Vendored Material for MkDocs v9.7.7 with intentional deviations (commented in
source): `base.html` (palette persistence, `window.docsforge` API: `setLocale`,
`setPalette({scheme, primary, accent})`, `mermaidUrl`), `partials/i18n.html`
(stateless switcher), the SW registration + reload-detection script, and
`docsforge_theme.yml`. Keep `src/` close to upstream and comment deviations.

---

## 10. DocsForge Studio (`studio/`) — the VS Code extension

No language server: everything is computed from the docs tree and the build's
`validation.json`.

| File | Purpose |
|------|---------|
| `extension.ts` | Activation, command registration, provider/rename wiring |
| `serverManager.ts` | Spawns `docsforge serve`/`build`, pidfile adoption (`.docsforge/server.json`), status bar, browser opening |
| `initWizard.ts` | Interactive project init (calls `docsforge init` via Python) |
| `environment.ts` | Python detection (setting → remembered venv → `.venv` → PATH), pip + docsforge check, venv/user/global install |
| `logPanel.ts` | WebviewView (`docsforge.output`) in the sidebar streaming build/serve logs (ANSI-stripped, 5000-line buffer) |
| `sidebarProvider.ts` | Sidebar action tree |
| `pure.ts` | vscode-free helpers (findConfig, extractServerUrl, stripAnsi, venvPythonPath, parseDocsforgeVersion) |
| `links.ts` | Pure link/anchor engine: extractLinks, extractHeadings, resolveLinkTarget, linesOfLink, slugifyHeading, checkFootnotes, formatMarkdown, computeRenameEdits, computeAnchorRenameEdits, computeDocumentRename, computeFolderRename |
| `diagnostics.ts` | Reads `.docsforge/cache/validation.json` → `DiagnosticCollection`; watches the cache dir + polls mtime; footnote checks |
| `providers.ts` | DocumentSymbol, FoldingRange, Definition, Hover, Reference, Completion (icons + paths), DocumentHighlight, DocumentLink, CodeActions (fix link / open target / fix-all), DocumentFormatting |
| `rename.ts` | Rename Document (base + locale variants), Rename Anchor, auto-rename via `onDidRenameFiles` (renames companions, updates links) |

Key behaviors:

- **Diagnostics**: from validation.json; a broken link appearing N times gets
  a squiggle at **every** occurrence (line-of-link scan). Refreshed on file
  change + after builds; a running `docsforge serve` keeps it live. Footnote
  checks (unresolved / duplicate `[^x]`) run extension-side on every refresh.
- **Rename**: `computeDocumentRename` renames the base doc + all locale
  variants (`foo.md`, `foo.zh.md`, `foo.fr.md`, ...) and rewrites every link
  resolving to any of them, anchor-aware. `computeAnchorRenameEdits` rewrites
  links to a renamed heading slug. Explorer renames are intercepted by
  `onDidRenameFiles` and auto-apply (companion files renamed too, warnings on
  collisions; folder renames via `computeFolderRename`).
- **Code actions**: per-link "Fix link: use <existing file>" (finds a same
  basename), "Open link target", and "Fix all broken links (N)" across the
  file. The lightbulb appears on every occurrence because the provider also
  scans the cursor line directly, not only `context.diagnostics`.
- **Providers scope**: markdown files under the workspace `docs_dir` (from
  `docsforge.yml`), via a `DocumentSelector` pattern.
- **Commands**: `init, serve, stop, build, stopBuild, openServer, openDocs,
  openLog, setupEnvironment, renameDocument, renameAnchor, refreshDiagnostics,
  openLinkTarget, openPage`.
- **Settings**: `docsforge.pythonPath`, `lan`, `openBrowser`,
  `rememberedPython`, `formatOnSave` (opt-in; format markdown on save).
- **Packaging**: `docsforge-studio`, displayName "DocsForge Studio",
  Apache-2.0, zero runtime deps (no vscode-languageclient).

---

## 11. Asset optimization (`asset_optimizer.py`)

`optimize_assets(site_dir, built_any, sources_changed, cache_dir)`:

- Parses every HTML file for asset references (`<link>`, `<script>`, `<img>`,
  `srcset`, inline styles with `url()`).
- Removes **unused assets** (files in `site_dir` never referenced) — only
  when something changed (expensive reference scan skipped on no-op builds).
- Strips **source maps** from JS files (incremental: skips unchanged files by
  cached mtime+size).
- Drops old font formats (e.g. legacy woff when woff2 exists).
- Uses a reference cache to avoid re-scanning unchanged pages.

---

## 12. Tests

- `tests/unit/` — per-module unit tests (build, cache, check, cli, config,
  files, nav, pages, pdf, rendering, serve, social, templates, theme,
  asset_optimizer, livereload_observer, ...).
- `tests/regression/test_regressions.py` — historical bug regressions.
- `tests/integration/` — build e2e, i18n build, example-site build,
  link-validation-incremental (anchor warnings surface on incremental builds).
- `tests/e2e/` — Playwright browser tests (`-m e2e`).
- `pytest.ini`: markers `slow` (deselect `-m "not slow"`) and `e2e`;
  DeprecationWarnings from docsforge are errors.
- Studio: `studio/test/*.test.ts` (mocha + ts-node), pure helpers only
  (links, pure).

---

## 13. CI / release (`.github/workflows/`)

- `ci.yml` — on push/PR to main: `test` (Python suite), `e2e` (Playwright),
  `frontend` (pnpm install → build → parity check → `pip install -e .` for
  pygments — requires `setup-python` so pip's resolution shadows the runner's
  system pygments), `studio` (npm ci → compile → lint → test).
- `pages.yml` — deploy the docs site (`docs/`) to GitHub Pages.
- `demo.yml` — build `examples/sites/docsforge-demo` in GH Actions (TeX Live
  for TikZ) and deploy to Cloudflare Pages via wrangler-action v4.
  Secrets: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`. Cloudflare-side
  auto-build must be disabled.
- `release.yml` — `workflow_dispatch` with `version` + optional `prerelease`
  inputs. Jobs: test → release (validate/derive versions, bump pyproject +
  studio package.json, frontend rebuild, changelog extraction → release body,
  commit + tag) → publish-pypi → build-vsix → build-docker.
- `dependabot.yml` — weekly updates: github-actions (root), npm (root pnpm),
  npm (`/studio`), pip (root).

---

## 14. Examples & demo

- `examples/sites/docsforge-demo/` — the official demo: Shannon paper (TikZ
  figures), diagram-demo, features, tags, blog, theme-playground, custom_dir
  override. Own `docsforge.yml` with explicit nav schema and
  `edit_uri: edit/main/examples/sites/docsforge-demo/docs/`.
- `examples/hooks/` — `hook_draft_banner.py` (on_env hook example).
- `examples/plugins/` — `custom-filter`, `last-modified`, `reading-time`
  (third-party plugin examples).
- `examples/README.md` — catalog of projects/plugins/hooks using DocsForge.
- The demo's TikZ figures are compiled at build time (texlive + dvisvgm);
  outputs are gitignored (`docs/assets/tikz/*.svg`).

---

## 15. Licensing

- Apache-2.0 (root `LICENSE`); upstream attribution in `NOTICE`
  (ProperDocs/MkDocs BSD-2, Material MIT, Python-Markdown BSD-3, Pygments,
  Lunr, Mermaid, MDI Apache-2.0, Lucide ISC, Octicons MIT, Simple Icons CC0,
  FontAwesome CC-BY-4.0, Twemoji CC-BY-4.0).
- Docs content: CC BY 4.0. See `docs/docs/license.md` (en) + `.zh.md`.
