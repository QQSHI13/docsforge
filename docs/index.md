# DocsForge

Write your documentation in Markdown. Build a professional static site in seconds. Deploy anywhere.

```bash
pip install docsforge
docsforge serve
```

## What makes DocsForge different

<div class="grid cards" markdown>

-   :material-package-variant-closed:{ .lg .middle } &nbsp; **Zero Dependencies**

    ---

    Everything is bundled. `pip install docsforge` gets you the engine, Material theme, all plugins, all extensions, fonts, icons, math rendering, and a service worker.

-   :material-rocket-launch:{ .lg .middle } &nbsp; **Zero Config**

    ---

    Start with just `site_name:`. All 7 plugins and 31 Markdown extensions load automatically. Customize only when you need to.

-   :material-function-variant:{ .lg .middle } &nbsp; **Math Works**

    ---

    Write `$$...$$` and it renders. KaTeX is vendored — no CDN, no `extra_javascript`, no setup.

-   :material-code-tags:{ .lg .middle } &nbsp; **Syntax Highlighted**

    ---

    Code blocks render with Pygments colors at build time. No client-side JavaScript needed.

-   :material-magnify:{ .lg .middle } &nbsp; **Instant Search**

    ---

    Full-text search built in, powered by a client-side Lunr.js index.

-   :material-palette:{ .lg .middle } &nbsp; **Dark Mode**

    ---

    Light/dark toggle in the header. Auto-detects system preference.

-   :material-chart-bar:{ .lg .middle } &nbsp; **TikZ Diagrams**

    ---

    Write TikZ directly in Markdown. Auto-compiled to SVG at build time.

-   :material-rss-box:{ .lg .middle } &nbsp; **Blogging**

    ---

    Built-in blog with authors, tags, archives, pagination, and RSS feeds.

-   :material-wifi-off:{ .lg .middle } &nbsp; **Offline Support**

    ---

    Service worker caches all assets. Works without an internet connection.

</div>

## Quick start

```bash
pip install docsforge
docsforge new my-docs
cd my-docs
docsforge serve
```

That's it. Your documentation site is now running at [localhost:8000](http://localhost:8000).

## What you get

| Feature | Status |
|---------|--------|
| Admonitions (`!!! note`) | ✅ Zero config |
| Math (`$$...$$`) | ✅ Zero config |
| Code highlighting | ✅ Zero config |
| Tables | ✅ Zero config |
| Task lists (`- [x]`) | ✅ Zero config |
| Footnotes (`[^1]`) | ✅ Zero config |
| Definition lists | ✅ Zero config |
| Abbreviations | ✅ Zero config |
| Content tabs | ✅ Zero config |
| Diagrams (Mermaid, TikZ) | ✅ Zero config |
| Emojis | ✅ Zero config |
| Blog | ✅ Zero config |
| Tags | ✅ Zero config |
| Search | ✅ Zero config |
| Privacy (self-host assets) | ✅ Zero config |
| Minify (HTML/CSS/JS) | ✅ Zero config |
| Offline/PWA | ✅ Zero config |

## Next steps

<div class="grid cards" markdown>

-   :material-cog-play:{ .lg .middle } &nbsp; **[Getting Started](getting-started.md)**

    ---

    Installation, first steps, and basic configuration

-   :material-book-open-page-variant:{ .lg .middle } &nbsp; **[Setup Guides](setup/index.md)**

    ---

    Customize colors, fonts, navigation, search, and more

-   :material-code-braces:{ .lg .middle } &nbsp; **[Reference](reference/index.md)**

    ---

    Markdown syntax, components, and formatting options

-   :material-rss-box:{ .lg .middle } &nbsp; **[Blogging](blogging.md)**

    ---

    Set up a blog with authors, tags, and RSS feeds

</div>
