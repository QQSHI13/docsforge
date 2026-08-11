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

## 2. The Python package (`docsforge/`)

### Entry points

| File | Purpose |
|------|---------|
| `__init__.py` | Version, re-exports of utils |
| `__main__.py` | Click CLI (`docsforge build/serve/check/init/...`) |
| `cli_core.py` | CLI backend logic (config discovery, `Validator`, `BuildEngine`, `DevServer`, `AutoRouter`) |
| `check.py` | `docsforge check` — YAML validation, plugin/theme checks, `fix_config` |

### Config

- `config_base.py` — `Config` base class + `load_config()` (YAML → config
  object), schema generation.
- `config_defaults.py` — `DocsForgeConfig`: every config key. Notable ones:
  `site_name`, `site_url`, `nav`, `theme`, `docs_dir` (default `docs`),
  `site_dir` (default `site`), `use_directory_urls` (default True),
  `markdown_extensions` (31 preconfigured), `tikz` (bool, optional),
  `plugins` (default `[]` — core plugins still auto-load), `privacy`
  (default True — external assets fetched + inlined), `hooks` (Python module
  plugins), `watch`, and `validation` (link/anchor warning levels, see §5).
- `config_options.py` — the option type system (`Type`, `Choice`, `Optional`,
  `URL`, `Dir`, `Plugins`, `Nav`, `MarkdownExtensions`, `SubConfig`, etc.).
- `filter_config.py` — `get_schema()` for JSON schema export.

### Build pipeline (`build.py`)

The `build()` function, in order:

1. `_collect_files_and_nav()` — compiles TikZ (if enabled), collects files
   from `docs_dir` + theme, runs `on_files` plugins, sets exclusions, builds
   navigation.
2. Renders pages (thread pool, one thread per page): `Page.render()` applies
   the Markdown pipeline, extracts anchors/links/titles; per-page
   `link_warnings` collected.
3. `_write_outputs()` — writes rendered pages, updates the cache
   (`planner.update_cache`), serializes per-page validation.
4. `_finalize_build()` — restores validation for un-rendered pages, runs the
   anchor/link validation pass **on every build**, re-serializes validation,
   runs `on_post_build`, optimizes assets, generates the PWA manifest +
   service worker, saves the cache.

### Incremental cache (`cache.py`)

- `CACHE_DIR = .docsforge/cache`, `CACHE_VERSION = 1`.
- `FileHasher` — SHA-256 content hashing.
- `DependencyTracker` — tracks snippet includes (`--8<-- "path"` lines) so a
  change to an included file dirties its consumers.
- `BuildPlanner` — dirty-page detection from hashes/deps/config/theme/nav
  signatures; orphan-output cleanup; `validation.json` persistence
  (`get_validation`/`set_validation`), keyed by source uri →
  `{warnings, links, anchors}`.

### Files / pages / nav

- `files.py` — `Files` collection, `File` (src_uri, dest_uri, url, page),
  `InclusionLevel`, `get_files()`, `set_exclusions()`.
- `pages.py` — `Page` (render, TOC, anchors, `link_warnings`,
  `validate_anchor_links`), markdown treeprocessors (anchor extraction,
  relative-path rewriting, title extraction), raw-HTML handling.
- `nav.py` — `Navigation`, `Section`, `Link`, `get_navigation()`; explicit
  nav schema (`title/path/children/i18n`) + legacy shorthand.

### Serving (`serve.py`, `livereload.py`)

- `serve.py` — dev server wrapper: port retry, config-mtime cache, pidfile
  (`.docsforge/server.json`) for the VS Code extension, stdin config.
- `livereload.py` — `LiveReloadServer`: file watching (watchdog), epoch-cond
  rebuild safety (a rebuild triggered by a change won't re-trigger on its own
  output), read-only event filtering, hermetic mime map. Note: the browser
  auto-reload-injection of mkdocs' livereload was dropped.

### Content features

- `tikz.py` — compiles `.tex` files (TikZ diagrams) to SVG via LaTeX +
  dvisvgm, parallel + incremental. Config: `tikz: true`.
- `pdf.py` — `docsforge build --pdf`: renders built HTML to A4 PDF via
  headless Chromium (Playwright), parallel tabs, offline asset routing.
  Extra: `docsforge[pdf]`.
- `emoji.py` — Material Icons emoji extension (twemoji index → SVG).
- `meta.py` (root) — front-matter parser (`get_data`).
- `rendering.py`, `toc.py` — heading text extraction, TOC model.
- `git_info.py` — last-modified dates via git.
- `localization.py` — Babel-less i18n helper.
- `asset_optimizer.py` — `optimize_assets()`: removes unused assets, strips
  source maps, drops old font formats; incremental via cache.
- `utils.py` — helpers (slugify, url helpers, write_file, CountHandler,
  DuplicateFilter, ...).
- `init.py` — interactive `docsforge init` wizard.
- `theme.py` — theme loading (name, custom_dir, locale).

---

## 3. Core plugins (`docsforge/core/`)

### Plugin system (`plugin_base.py`)

- `BasePlugin` with the mkdocs-compatible event API:
  `on_startup`, `on_shutdown`, `on_serve`, `on_config`, `on_pre_build`,
  `on_files`, `on_nav`, `on_env`, `on_post_build`, `on_build_error`,
  `on_pre_template`, `on_template_context`, `on_post_template`,
  `on_pre_page`, `on_page_read_source`, `on_page_markdown`,
  `on_page_content`, `on_page_context`, `on_post_page`.
- `event_priority(priority)` decorator for ordering.
- Entry points: `docsforge.plugins` group; theme-namespaced (`material/*`).
  Core plugins are registered with the `material/` namespace and load
  automatically via `config_options.Plugins.run_validation` — except
  **social** (opt-in, needs pillow + cairosvg) and **privacy** (loaded only
  when `privacy: true` config).

### The plugins

| Plugin | What it does | Load |
|--------|-------------|------|
| `search` | Lunr.js full-text search index (client-side, offline); per-locale indexes; Chinese via jieba when installed | auto |
| `meta` | OpenGraph / social metadata injection | auto |
| `tags` | Tag system with tag pages | auto |
| `blog` | Blog: posts, authors, categories, archive, RSS | auto |
| `info` | Admonition callouts (material's info plugin) | auto |
| `minify` | HTML/CSS/JS minification (minify-html Rust crate + csscompressor + jsmin); source-map stripping | auto |
| `i18n` | Suffix-mode i18n (see §4) | auto |
| `privacy` | Fetches + inlines external assets (Google Fonts, CDN scripts) at build; cache under `.docsforge/cache/privacy` | when `privacy: true` |
| `social` | Social cards (OpenGraph PNG generation), two-stage parallel rendering, font download, cache under `.docsforge/cache/social` | opt-in via `plugins: [social]` |

`docsforge/check.py`'s `BUILTIN_PLUGINS` includes all 9; `AUTOLOAD_PLUGINS`
excludes social (declaring it doesn't warn).

---

## 4. i18n (suffix mode)

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
- `on_files` creates per-locale File objects; `on_nav` clones nav with
  per-locale titles (`i18n: {zh: 首页}`); `on_page_context` fixes locale
  titles; `on_page_content` injects alternate-language `<link>` tags;
  `on_post_build` writes the locale switcher data.
- The theme's i18n widget is **stateless** (fixed the instant-nav state bug),
  persists language in IDB, works on 404 pages too.

---

## 5. Validation (`validation.*` config)

`DocsForgeConfig.validation` controls warning levels (Python logging levels:
`debug/info/warn/error`):

- `validation.nav.omitted_files` (info), `.not_found` (warn),
  `.absolute_links` (info)
- `validation.links.not_found` (warn), `.absolute_links` (info),
  `.unrecognized_links` (info), `.anchors` (info)

Link/anchor problems are collected per page (`page.link_warnings`) during
render, persisted to `.docsforge/cache/validation.json` (keyed by src_uri:
`{warnings: [[level, msg]], links: {target: {anchor: original}}, anchors: []}`),
restored for un-rendered pages, and re-emitted **every build**. The VS Code
extension reads this file for diagnostics.

---

## 6. Frontend build (`build_frontend.py`) + `src/`

- `ROOT` = repo root, `SRC = src/`, `OUT = docsforge/templates/`,
  `NODE_MODULES = node_modules/`.
- Steps (see §CONTRIBUTING): `copy_icons` (svgo-optimize mdi/lucide/octicons/
  fontawesome/simple-icons from node_modules into `src/templates/.icons/`),
  `copy_icons_to_out`, `copy_templates` (minify HTML), `build_typescript`
  (esbuild → `bundle.min.js`, `workers/search.min.js`), `build_styles`
  (sass + autoprefixer + postcss → `main.min.css`, `palette.min.css`),
  `generate_pygments_css` (Pygments default style, `.highlight` scope),
  `copy_lunr` (lunr-languages stemmers), `copy_katex` (katex dist + fonts),
  `copy_mermaid` (mermaid.min.js), `copy_sw` (esbuild-minified worker keeping
  `__DOCSFORGE_BASE_URL__` / `__DOCSFORGE_BUILD_HASH__` placeholders).
- `src/assets/javascripts/sw.js` — the service worker source; build.py
  injects the real base URL + a deterministic build hash at site-build time.
  Mermaid is loaded from the local asset via `window.docsforge.mermaidUrl`
  (set in base.html), with an unpkg CDN fallback.
- The frontend CI job asserts `git diff --exit-code -- docsforge/templates`
  after a rebuild — committed templates must match the build.

---

## 7. DocsForge Studio (`studio/`) — the VS Code extension

No language server: everything is computed from the docs tree and the build's
`validation.json`.

| File | Purpose |
|------|---------|
| `extension.ts` | Activation, command registration, provider/rename wiring |
| `serverManager.ts` | Spawns `docsforge serve`/`build`, pidfile adoption, status bar |
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

- **Diagnostics**: from validation.json; a broken link appearing N times gets a
  squiggle at every occurrence (line-of-link scan). Refreshed on file change +
  after builds; a running `docsforge serve` keeps it live.
- **Rename**: `computeDocumentRename` renames the base doc + all locale
  variants (`foo.md`, `foo.zh.md`, `foo.fr.md`, ...) and rewrites every link
  resolving to any of them, anchor-aware. Explorer renames are intercepted by
  `onDidRenameFiles` and auto-apply (companion files renamed too, warnings on
  collisions).
- **Commands**: `init, serve, stop, build, stopBuild, openServer, openDocs,
  openLog, setupEnvironment, renameDocument, renameAnchor, refreshDiagnostics,
  openLinkTarget, openPage`.
- **Settings**: `docsforge.pythonPath`, `lan`, `openBrowser`,
  `rememberedPython`, `formatOnSave` (opt-in; format markdown on save).
- Packaging: `docsforge-studio`, displayName "DocsForge Studio", Apache-2.0,
  zero runtime deps (no vscode-languageclient).

---

## 8. Tests

- `tests/unit/` — per-module unit tests (build, cache, check, cli, config,
  files, nav, pages, pdf, rendering, serve, social, templates, theme, ...).
- `tests/regression/test_regressions.py` — historical bug regressions.
- `tests/integration/` — build e2e, i18n build, example-site build,
  link-validation-incremental.
- `tests/e2e/` — Playwright browser tests (`-m e2e`).
- `pytest.ini`: markers `slow` (deselect `-m "not slow"`) and `e2e`;
  DeprecationWarnings from docsforge are errors.
- Studio: `studio/test/*.test.ts` (mocha + ts-node), pure helpers only.

---

## 9. CI / release (` .github/workflows/`)

- `ci.yml` — on push/PR to main: `test` (Python suite), `e2e` (Playwright),
  `frontend` (pnpm install → build → parity check → pygments via
  `pip install -e .`), `studio` (npm ci → compile → lint → test).
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

## 10. Examples & demo

- `examples/sites/docsforge-demo/` — the official demo: Shannon paper (TikZ
  figures), diagram-demo, features, tags, blog, theme-playground, custom_dir
  override. Own `docsforge.yml` with explicit nav schema and
  `edit_uri: edit/main/examples/sites/docsforge-demo/docs/`.
- `examples/hooks/` — `hook_draft_banner.py` (on_env hook example).
- `examples/plugins/` — `custom-filter`, `last-modified`, `reading-time`
  (third-party plugin examples).
- `examples/README.md` — catalog of projects/plugins/hooks using DocsForge.

---

## 11. Licensing

- Apache-2.0 (root `LICENSE`); upstream attribution in `NOTICE`
  (ProperDocs/MkDocs BSD-2, Material MIT, Python-Markdown BSD-3, Pygments,
  Lunr, Mermaid, MDI Apache-2.0, Lucide ISC, Octicons MIT, Simple Icons CC0,
  FontAwesome CC-BY-4.0, Twemoji CC-BY-4.0).
- Docs content: CC BY 4.0. See `docs/docs/license.md` (en) + `.zh.md`.
