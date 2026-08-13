---
icon: material/home
---

# DocsForge

<p align="center">
  <img src="assets/badge.svg" alt="DocsForge">
</p>

Write your documentation in Markdown. Build a professional static site in seconds. Deploy anywhere.


!!! tip "Coming from MkDocs?"

    DocsForge is the actively maintained successor to MkDocs + Material for MkDocs.
    See the [migration guide](getting-started/migrating-from-mkdocs.md) to convert your project manually.

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

    Start with just `site_name:`. All 8 core plugins and 36 Markdown extensions load automatically; social cards are opt-in. Customize only when you need to.

-   :material-function-variant:{ .lg .middle } &nbsp; **Math Works**

    ---

    Write `$$...$$` and it renders. KaTeX is vendored — no CDN calls for readers, no `extra_javascript`, no setup.

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

    Write TikZ diagrams as `.tex` files. Auto-compiled to SVG at build time (requires a LaTeX toolchain).

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
docsforge          # create a new project interactively
cd my-docs
docsforge serve
```

That's it. Your documentation site is now running at [localhost:8000](http://localhost:8000).

## What you get

| Feature | Status |
|---------|--------|
| Admonitions (`!!! note`) | :material-check-bold: Zero config |
| Math (`$$...$$`) | :material-check-bold: Zero config |
| Code highlighting | :material-check-bold: Zero config |
| Tables | :material-check-bold: Zero config |
| Task lists (`- [x]`) | :material-check-bold: Zero config |
| Footnotes (`[^1]`) | :material-check-bold: Zero config |
| Definition lists | :material-check-bold: Zero config |
| Abbreviations | :material-check-bold: Zero config |
| Content tabs | :material-check-bold: Zero config |
| Diagrams (Mermaid, TikZ) | :material-check-bold: Zero config |
| Emojis | :material-check-bold: Zero config |
| Blog | :material-check-bold: Zero config |
| Tags | :material-check-bold: Zero config |
| Search | :material-check-bold: Zero config |
| Privacy (self-host assets) | :material-check-bold: Zero config |
| Minify (HTML/CSS/JS) | :material-check-bold: Zero config |
| Offline/PWA | :material-check-bold: Zero config |

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
