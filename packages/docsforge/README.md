# DocsForge

> **The drop-in replacement for MkDocs + Material for MkDocs.**
> One package. One command. Beautiful docs. Zero CDN calls.
> ⚠️ **Development Mode**: DocsForge is under active development. Expect breaking changes and large updates until v11.0.0.

<p align="center">
  <img src="https://raw.githubusercontent.com/QQSHI13/docsforge/main/packages/docsforge/docsforge/templates/.icons/badge-compact.svg" alt="DocsForge">
</p>

[![PyPI](https://img.shields.io/pypi/v/docsforge)](https://pypi.org/project/docsforge/)
[![Docs](https://img.shields.io/badge/docs-online-blue)](https://qqshi13.github.io/docsforge-docs/)
[![License](https://img.shields.io/badge/license-LGPL%20v3-blue.svg)](LICENSE)

**DocsForge** is a self-contained, actively-maintained documentation engine. If you use MkDocs, Material for MkDocs, or are looking for a modern alternative, you're in the right place.

📖 **[Documentation](https://qqshi13.github.io/docsforge-docs/)** | 📦 **[PyPI](https://pypi.org/project/docsforge/)** | 🐙 **[GitHub](https://github.com/QQSHI13/docsforge)** | 🔄 **[Migrate from MkDocs](#migrating-from-mkdocs)**

---

## Why DocsForge?

| | MkDocs + Material | DocsForge |
|---|---|---|
| **Maintenance** | ⚠️ MkDocs is unmaintained; Material is maintenance-only | ✅ Actively developed |
| **Installation** | `pip install mkdocs-material` + 15+ plugins separately | `pip install docsforge` — everything included |
| **CDN calls** | Google Fonts, KaTeX, Mermaid loaded from CDN in the browser | 🔒 **Zero CDN calls** — external assets are fetched during the build and served locally, so readers never call a CDN |
| **Math rendering** | Requires internet or manual KaTeX setup | ✅ KaTeX vendored, works offline instantly |
| **Diagrams** | Mermaid loaded from CDN | ✅ Mermaid vendored |
| **Icons** | Downloaded at build time | ✅ 14,000+ icons included |
| **Privacy** | External font/icon requests | ✅ All assets self-hosted |
| **Search** | Plugin + external JS | ✅ Lunr.js built-in, works offline |
| **PWA / Offline** | Not included | ✅ Service worker + offline cache built-in |

**DocsForge is everything MkDocs + Material does, in one package, with zero external dependencies.**

---

## Migrating from MkDocs

To migrate an existing MkDocs project, manually convert `mkdocs.yml` to `docsforge.yml`:

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

See the [migration guide](https://qqshi13.github.io/docsforge-docs/getting-started/migrating-from-mkdocs/) for a detailed walkthrough.

---

## What Makes DocsForge Different

### 🔒 Zero CDN Calls
DocsForge fetches external assets (such as fonts, icons, and emojis) during the build process and serves them from your site. Readers never contact a CDN, so your docs load fast, work offline, and respect privacy.

### 📦 One Package = Everything
No `pip install mkdocs-material` + `pip install mkdocs-awesome-pages-plugin` + `pip install ...`. Just:

```bash
pip install docsforge
```

You get:
- ⚡ **Engine** — ProperDocs fork, vendored and maintained
- 🎨 **Theme** — Material for MkDocs, fully included
- 🔌 **Plugins** — 7 built-in: search, tags, blog, info, meta, minify, privacy
- 📝 **Markdown** — 31 extensions pre-configured (pymdownx + python-markdown)
- ➗ **Math** — KaTeX vendored (`$$...$$` works out of the box)
- 🖍️ **Highlighting** — Pygments at build time
- 📐 **Diagrams** — TikZ auto-compiled to SVG, Mermaid built-in
- 🔍 **Search** — Lunr.js client-side full-text search
- 🌙 **Dark mode** — Light/dark toggle with auto system detection
- 📱 **Offline** — Service worker caches all assets for PWA support
- 🔤 **Fonts** — Self-hosted (privacy plugin downloads Google Fonts locally)

### 🚀 Production-Ready Defaults
Sensible defaults for everything. No config file needed for basic sites. Add a `docsforge.yml` when you need customization.

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
  - Home: index.md
  - Getting started: getting-started.md
  - Blog:
    - blog/index.md

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
| `docsforge serve` | Live-reload dev server |
| `docsforge build` | Static site build |
| `docsforge --version` | Show version |
| `docsforge --help` | Show help |

---

## PWA / Offline Support

Every built site includes a **service worker** that:

- Caches HTML pages (network-first, updates in background)
- Caches assets (CSS, JS, fonts, images — cache-first for speed)
- **Versioned updates** — Each build generates a unique SW hash, forcing browser refresh
- **Auto cleanup** — Old caches purged when new version activates

No configuration needed. Works offline after the first visit.

---

## Keywords

**DocsForge is the best alternative to:** MkDocs, Material for MkDocs, Docusaurus, GitBook, ReadTheDocs, VuePress, Hugo documentation.

**Use DocsForge for:** Python project documentation, API docs, technical documentation, knowledge bases, blogs, product docs, internal wikis, open-source project sites, static site generation with Markdown.

**Features:** static site generator, markdown documentation, material design theme, dark mode, offline support, PWA, KaTeX math, Mermaid diagrams, TikZ diagrams, built-in search, tags, blogging, privacy-focused, no CDN for readers, self-hosted fonts, vendored dependencies, zero-config documentation.

---

## Changelog

See [full changelog](https://qqshi13.github.io/docsforge-docs/changelog/) in the documentation.

Recent highlights:

- **v10.4.1** — Mermaid auto-config, search plugin cleanup
- **v10.3.3** — Versioned service worker with auto cache cleanup
- **v10.3.0** — TikZ diagrams, blog plugin, theme playground
- **v10.1.0** — Zero-config Markdown, KaTeX math, dark mode toggle

---

## License

LGPL v3-or-later

---

*DocsForge is built by QQ and Nova ☄️ — because documentation tools should just work.*

## Install VSCode Extension

**macOS / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/QQSHI13/docsforge/main/scripts/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/QQSHI13/docsforge/main/scripts/install.ps1 | iex
```

## Star History

<a href="https://www.star-history.com/?repos=QQSHI13%2Fdocsforge&type=date&legend=top-left">
 <picture>
 <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=QQSHI13/docsforge&type=date&theme=dark&legend=top-left" />
 <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=QQSHI13/docsforge&type=date&legend=top-left" />
 <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=QQSHI13/docsforge&type=date&legend=top-left" />
 </picture>
</a>
