# DocsForge

> **One package. One command. Beautiful docs.**

[![PyPI](https://img.shields.io/pypi/v/docsforge)](https://pypi.org/project/docsforge/)
[![Docs](https://img.shields.io/badge/docs-online-blue)](https://qqshi13.github.io/docsforge-docs/)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)

Write your documentation in Markdown. Build a professional static site in seconds. Deploy anywhere.

📖 **[Documentation](https://qqshi13.github.io/docsforge-docs/)** | 📦 **[PyPI](https://pypi.org/project/docsforge/)** | 🐙 **[GitHub](https://github.com/QQSHI13/docsforge)**

---

## What is DocsForge?

DocsForge is a **self-contained documentation engine**. Everything you need is bundled into one package:

- ⚡ **Engine** — ProperDocs (MkDocs fork), vendored
- 🎨 **Theme** — Material for MkDocs, vendored  
- 🔌 **Plugins** — 7 plugins built-in (search, tags, blog, info, meta, minify, privacy)
- 📝 **Markdown** — 31 extensions pre-configured (all pymdownx + python-markdown)
- ➗ **Math** — KaTeX vendored (`$$...$$` works out of the box)
- 🖍️ **Highlighting** — Pygments for code blocks at build time
- 📐 **Diagrams** — TikZ support (auto-compiled to SVG)
- 🔍 **Search** — Lunr.js client-side full-text search
- 🌙 **Dark mode** — Light/dark toggle with auto system detection
- 📱 **Offline** — Service worker caches all assets for PWA support
- 🔤 **Fonts** — Self-hosted (privacy plugin downloads Google Fonts locally)

`pip install docsforge` and you're done. No CDN, no extra config, no external dependencies.

---

## Installation

```bash
pip install docsforge
```

Requires **Python 3.10+**.

---

## Quick Start

```bash
# Create a new project
docsforge new my-docs
cd my-docs

# Start the dev server
docsforge serve
# → http://localhost:8000

# Build for production
docsforge build
# → site/
```

---

## What's Built In

### 📝 Documentation
| Feature | Status |
|---------|--------|
| Admonitions (`!!! note`) | ✅ Zero config |
| Math (`$$...$$`) | ✅ Zero config |
| Code highlighting | ✅ Zero config |
| Tables, task lists, footnotes | ✅ Zero config |
| Definition lists, abbreviations | ✅ Zero config |
| Content tabs, diagrams (Mermaid, TikZ) | ✅ Zero config |

### 🔍 Discovery
| Feature | Status |
|---------|--------|
| Full-text search (Lunr.js) | ✅ Zero config |
| Tags and tag pages | ✅ Zero config |
| Navigation with sections/tabs | ✅ Zero config |
| Table of contents | ✅ Zero config |

### 🎨 Theming
| Feature | Status |
|---------|--------|
| Material theme (light/dark) | ✅ Zero config |
| Customizable colors/fonts | ✅ Zero config |
| 14,000+ icons | ✅ Zero config |

### 📝 Blogging
| Feature | Status |
|---------|--------|
| Author profiles | ✅ Zero config |
| Categories, tags, archives | ✅ Zero config |
| Pagination | ✅ Zero config |
| RSS feeds | ✅ Zero config |

### 🌐 Publishing
| Feature | Status |
|---------|--------|
| Static HTML output | ✅ Zero config |
| GitHub Pages workflow | ✅ Zero config |
| PWA with offline support | ✅ Zero config |
| Minified HTML/CSS/JS | ✅ Zero config |

---

## Config File

DocsForge looks for config in this priority:

1. `docsforge.yml` / `docsforge.yaml` ← **preferred**
2. `properdocs.yml` / `properdocs.yaml`
3. `mkdocs.yml` / `mkdocs.yaml` ← legacy fallback

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
| `docsforge new <name>` | Scaffold a new project |
| `docsforge serve` | Live-reload dev server |
| `docsforge build` | Static site build |
| `docsforge gh-deploy` | Deploy to GitHub Pages |

---

## PWA / Offline Support

Every built site includes a **service worker** that:

- Caches HTML pages (network-first, updates in background)
- Caches assets (CSS, JS, fonts, images — cache-first for speed)
- **Versioned updates** — Each build generates a unique SW hash, forcing browser refresh
- **Auto cleanup** — Old caches purged when new version activates

No configuration needed. Works offline after the first visit.

---

## Changelog

See [full changelog](https://qqshi13.github.io/docsforge-docs/changelog/) in the documentation.

Recent highlights:

- **v10.3.3** — Versioned service worker with auto cache cleanup
- **v10.3.0** — TikZ diagrams, blog plugin, theme playground
- **v10.1.0** — Zero-config Markdown, KaTeX math, dark mode toggle

---

## License

GPL-3.0-or-later

---

*DocsForge is built by QQ (Cyrus) and Nova ☄️*

## Star History

<a href="https://www.star-history.com/?repos=QQSHI13%2Fdocsforge&type=date&legend=top-left">
 <picture>
 <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=QQSHI13/docsforge&type=date&theme=dark&legend=top-left" />
 <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=QQSHI13/docsforge&type=date&legend=top-left" />
 <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=QQSHI13/docsforge&type=date&legend=top-left" />
 </picture>
</a>
