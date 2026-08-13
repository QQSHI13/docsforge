---
icon: material/feature-search-outline
---

# Features

DocsForge includes everything you need to write and publish documentation. No extra installs, no extra config.

## Core Features

<div class="grid cards" markdown>

-   :material-package-variant-closed:{ .lg .middle } &nbsp; **Zero Dependencies**

    ---

    `pip install docsforge` gets you the engine, Material theme, all plugins, all Markdown extensions, KaTeX math, Pygments highlighting, fonts, icons, and a service worker. Nothing else to install.

-   :material-rocket-launch:{ .lg .middle } &nbsp; **Zero Configuration**

    ---

    Start with a working site in seconds. 8 core plugins and 36 Markdown extensions load automatically; social cards are opt-in. Customize only what you need.

-   :material-theme-light-dark:{ .lg .middle } &nbsp; **Light & Dark Mode**

    ---

    Automatic system preference detection with a manual toggle. Both modes are fully customizable with your brand colors.

-   :material-magnify:{ .lg .middle } &nbsp; **Full-Text Search**

    ---

    Client-side search powered by Lunr.js. No external services, no backend required. Works offline.

-   :material-function-variant:{ .lg .middle } &nbsp; **Math Rendering**

    ---

    Write `$$...$$` and it renders with KaTeX. No CDN calls for readers, no `extra_javascript`, no configuration.

-   :material-code-tags:{ .lg .middle } &nbsp; **Syntax Highlighting**

    ---

    Code blocks render with Pygments colors at build time. Supports all major languages.

-   :material-chart-bar:{ .lg .middle } &nbsp; **TikZ Diagrams**

    ---

    Write TikZ diagrams as `.tex` files. Automatically compiled to SVG at build time (requires a LaTeX toolchain; skipped gracefully when unavailable).

-   :material-rss-box:{ .lg .middle } &nbsp; **Blogging**

    ---

    Built-in blog plugin with authors, categories, tags, archives, pagination, and RSS feeds.

-   :material-wifi-off:{ .lg .middle } &nbsp; **Offline Support**

    ---

    Service worker caches all assets. Your documentation works without an internet connection.

</div>

## Markdown Extensions

All enabled by default. No configuration needed.

| Category | Extensions |
|----------|-----------|
| **Structure** | `toc`, `tables`, `fenced_code`, `def_list`, `footnotes`, `md_in_html`, `meta` |
| **Text** | `admonition`, `abbr`, `attr_list`, `nl2br`, `sane_lists`, `wikilinks` |
| **pymdownx** | `arithmatex`, `b64`, `betterem`, `caret`, `critic`, `details`, `emoji`, `escapeall`, `extra`, `fancylists`, `highlight`, `inlinehilite`, `keys`, `magiclink`, `mark`, `pathconverter`, `progressbar`, `quotes`, `saneheaders`, `smartsymbols`, `snippets`, `striphtml`, `superfences`, `tabbed`, `tasklist`, `tilde` |

## Plugins

8 core plugins auto-load — no `plugins:` config needed. Social cards are opt-in (`plugins: [social]`).

| Plugin | What it does |
|--------|-----------|
| `blog` | Blogging with authors, categories, archives, pagination, RSS |
| `i18n` | Multi-language sites (suffix-mode locale variants) |
| `info` | Admonition callouts (note, tip, warning, danger) |
| `meta` | OpenGraph metadata |
| `minify` | Compress HTML/CSS/JS output |
| `privacy` | Self-host external assets (Google Fonts, CDN scripts) |
| `search` | Full-text search with Lunr.js |
| `tags` | Tag system with tag pages |

## PWA / Offline

Every built site includes a service worker that:

- **Caches HTML pages** — network-first, updates cache in background
- **Caches assets** — CSS, JS, fonts, images served from cache for speed
- **Versioned updates** — Each build generates a unique SW hash, forcing browser refresh
- **Auto cleanup** — Old caches purged when new version activates

## Publishing

DocsForge builds static HTML. Deploy `site/` anywhere:

- **GitHub Pages** — [Ready-to-use workflow](publishing-your-site.md)
- **Netlify, Vercel** — Drag and drop
- **Your own server** — `rsync site/ server:/var/www/docs`
