# Changelog

All notable changes to DocsForge are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
