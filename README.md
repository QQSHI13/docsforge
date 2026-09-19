# DocsForge

> **The drop-in replacement for MkDocs + Material for MkDocs.**
> One package. One command. Beautiful docs. Zero CDN calls.

<p align="center">
  <img src="https://raw.githubusercontent.com/QQSHI13/docsforge/main/docsforge/templates/.icons/badge-compact.svg" alt="DocsForge">
</p>

[![PyPI](https://img.shields.io/pypi/v/docsforge)](https://pypi.org/project/docsforge/)
[![Docs](https://img.shields.io/badge/docs-online-blue)](https://qqshi13.github.io/docsforge/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

**DocsForge** is a self-contained, actively-maintained documentation engine — a vendored ProperDocs/MkDocs engine plus the Material theme, plugins, search, math, diagrams, and offline support in a single Python package. If you use MkDocs, Material for MkDocs, or are looking for a modern alternative, you're in the right place.

**[Documentation](https://qqshi13.github.io/docsforge/)** | **[PyPI](https://pypi.org/project/docsforge/)** | **[GitHub](https://github.com/QQSHI13/docsforge)** | **[Migrate from MkDocs](#migrating-from-mkdocs)**

---

## Why DocsForge?

MkDocs core has seen no real development for 18+ months and Material for MkDocs is in maintenance mode through its 2027 end-of-life, with its team focused on Zensical. DocsForge continues that stack as an independent, Apache-2.0 engine — no migration of your content required.

| | DocsForge | Alternatives |
|---|---|---|
| **MkDocs + Material** | Vendored engine + theme, maintained, one install | Plugin sprawl across dozens of packages; upstream frozen |
| **Docusaurus** | No Node.js toolchain needed | Requires Node + React; heavy client JS |
| **Sphinx / Read the Docs** | Markdown-first | reStructuredText-first; Markdown is second-class |
| **VitePress / VuePress** | No Node.js toolchain needed | Requires Node + Vue |
| **Hugo** | Docs-specific: versioning, search, i18n, offline built in | General static generator; docs features come via themes |
| **Zensical** | Free, open engine + free Studio extension | Rust core, but editor refactoring and governance are paid tiers |
| **GitBook** | Self-hosted static output you own | Hosted SaaS platform |

**DocsForge is everything MkDocs + Material does, in one package, with zero external dependencies.**

---

## Migrating from MkDocs

To migrate an existing MkDocs project automatically, run the one-liner — it
converts `mkdocs.yml` / `properdocs.yml` / `zensical.toml` to `docsforge.yml`:

**macOS / Linux:**
```bash
curl -fsSL https://qqshi13.github.io/docsforge/migrate.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://qqshi13.github.io/docsforge/migrate.ps1 | iex
```

The script converts navigation, theme, plugins, and extensions, warns about
anything it can't migrate, and prints a report. See the
[migration guide](https://qqshi13.github.io/docsforge/getting-started/migrating-from-mkdocs/)
for the manual, key-by-key walkthrough (also fine for a small site):

1. Rename `mkdocs.yml` to `docsforge.yml`.
2. Keep the `theme:` block as-is (DocsForge uses the built-in Material theme).
3. Remove built-in plugins and extensions from explicit lists — they are loaded by default.
4. Remove KaTeX, Mermaid, font, and icon CDN references — these are vendored.

Then build and preview:

```bash
pip install docsforge
docsforge build          # builds your site
docsforge serve          # live preview
```

---

## What Makes DocsForge Different

### Zero CDN Calls
DocsForge fetches external assets (such as fonts, icons, and emojis) during the build process and serves them from your site. Readers never contact a CDN, so your docs load fast, work offline, and respect privacy.

### One Package = Everything
No `pip install mkdocs-material` + `pip install mkdocs-awesome-pages-plugin` + `pip install ...`. Just:

```bash
pip install docsforge
```

You get:
- **Engine** — ProperDocs/MkDocs fork, vendored and maintained (no longer tracks upstream, so it can evolve independently)
- **Theme** — Material for MkDocs, fully included
- **Plugins** — 8 built-in: search, tags, blog, info, meta, minify, privacy, i18n
- **Markdown** — 39 extensions pre-configured (36 default + 3 built-in, pymdownx + python-markdown)
- **Math** — KaTeX vendored (`$$...$$` works out of the box, offline)
- **Highlighting** — Pygments at build time
- **Diagrams** — TikZ auto-compiled to SVG (requires a LaTeX toolchain), Mermaid built-in
- **Search** — Marz engine (Rust core, CJK-aware) with offline WASM retrieval
- **Dark mode** — Light/dark toggle with auto system detection
- **Offline** — Service worker caches all assets for PWA support
- **Fonts** — Self-hosted (privacy plugin downloads Google Fonts locally)
- **Bilingual docs** — English/Chinese twin pages with per-locale navigation, search indexes, and translation diagnostics

### Sensible Defaults
Most behavior works out of the box; a two-line `docsforge.yml` is a complete site (see below). Add configuration only when you need customization.

---

## Requirements

- **Python 3.10+** and `pip` — the only hard requirements.
- **LaTeX toolchain** — only for TikZ diagrams (`texlive` + `dvisvgm`).
- **Playwright + Chromium** — only for PDF export (`pip install "docsforge[pdf]"`).
- **pillow + cairosvg** — only for social cards (`pip install "docsforge[social]"`).
- **Node.js / pnpm** — only for contributors rebuilding the frontend theme.

## Known Limitations

Honest accounting of where DocsForge is weaker:

- **Smaller plugin universe.** MkDocs has hundreds of community plugins; DocsForge vendors 8 core ones. Anything outside that needs a custom plugin or stays behind.
- **Diverged theme.** The Material fork no longer tracks upstream, so upstream features and fixes don't flow in automatically — everything is maintained in-tree.
- **Build speed is Python speed.** Parallel incremental builds keep iteration fast, but cold full-site builds can't match Rust-based engines on very large sites.
- **Editor support is VS Code (+ forks like Cursor) only.** Studio is built directly on the VS Code extension API with no language server, so Zed, JetBrains IDEs, and Neovim are out of reach by design.
- **Search index ships the corpus.** The full-text index downloads to every reader; very large sites should watch its size (per-locale indexes and position stripping help).
- **TikZ and PDF are heavyweight.** Both shell out to large external toolchains rather than working out of the box like the rest.

---

## Installation

```bash
pip install docsforge
```

Requires **Python 3.10+**.

---

## Quick Start

```bash
# Create a new project interactively
docsforge
# Follow the prompts, then:
cd my-docs

# Start the dev server
docsforge serve
# → http://localhost:8000

# Build for production
docsforge build
# → site/
```

---

## Config File

DocsForge looks for config in this priority:

1. `docsforge.yml` / `docsforge.yaml` ← **preferred**
2. `mkdocs.yml` / `mkdocs.yaml` ← legacy fallback (shows migration hint)

### Minimal `docsforge.yml`

```yaml
site_name: My Documentation
site_url: https://example.com/
```

That's it. All plugins, extensions, and theme settings use sensible defaults.

### Full example

```yaml
site_name: My Docs
site_url: https://example.com/
site_author: Your Name

repo_url: https://github.com/username/repo

nav:
  - title: Home
    path: index.md
  - title: Getting started
    path: getting-started.md
  - title: Blog
    children:
      - path: blog/index.md

theme:
  name: material
  palette:
    - media: "(prefers-color-scheme: light)"
      scheme: default
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - media: "(prefers-color-scheme: dark)"
      scheme: slate
      primary: indigo
      accent: indigo
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
```

---

## CLI Reference

| Command | Description |
|---------|-------------|
| `docsforge` | Interactive project setup (when no config exists) |
| `docsforge serve` | Live-reload dev server (`-n` skips auto-open, `--lan` serves on all interfaces) |
| `docsforge build` | Static site build |
| `docsforge --version` | Show version |
| `docsforge --help` | Show help |

---

## PWA / Offline Support

Every built site includes a **service worker** that:

- Caches HTML pages (cache-first, refreshed in background)
- Caches assets (CSS, JS, fonts, images — cache-first for speed)
- **Versioned updates** — Each build generates a unique SW hash, forcing browser refresh
- **Auto cleanup** — Old caches purged when new version activates

No configuration needed. Works offline after the first visit.

---

## Keywords

**DocsForge is the best alternative to:** MkDocs, Material for MkDocs, Docusaurus, GitBook, ReadTheDocs, VuePress, Hugo documentation.

**Use DocsForge for:** Python project documentation, API docs, technical documentation, knowledge bases, blogs, product docs, internal wikis, open-source project sites, bilingual English/Chinese documentation, offline documentation.

**Features:** static site generator, markdown documentation, material design theme, dark mode, offline support, PWA, KaTeX math, Mermaid diagrams, TikZ diagrams, built-in search, tags, blogging, privacy-focused, no CDN for readers, self-hosted fonts, vendored dependencies, bilingual documentation.

---

## Changelog

See the [full changelog](https://qqshi13.github.io/docsforge/changelog/) in the documentation.

---

## License

Apache-2.0

---

*DocsForge is built by QQ and Nova ☄️ — because documentation tools should just work.*

## Install VSCode Extension

Install **DocsForge Studio** from the `.vsix` attached to the
[latest release](https://github.com/QQSHI13/docsforge/releases):

```bash
code --install-extension docsforge-vscode-<version>.vsix
```

or install it via the VS Code UI: Extensions view → `...` → *Install from VSIX*.

## Star History

<a href="https://www.star-history.com/?repos=QQSHI13%2Fdocsforge&type=date&legend=top-left">
  <picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=QQSHI13/docsforge&type=date&theme=dark&legend=top-left" />
  <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=QQSHI13/docsforge&type=date&legend=top-left" />
  <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=QQSHI13/docsforge&type=date&legend=top-left" />
  </picture>
</a>
