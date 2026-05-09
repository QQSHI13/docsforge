---
title: DocsForge
---

# Welcome to DocsForge

**DocsForge** is a self-contained documentation engine, forked from MkDocs + Material, with all dependencies vendored into a single package.

## What makes it different?

| | MkDocs + Material | DocsForge |
|---|---|---|
| External deps | 10+ packages | **Zero** (core) |
| Install size | ~50MB+ deps | **~15MB** single package |
| Offline builds | Sometimes breaks | **Always works** |
| Lockfile needed | Yes | **No** |

## Quick Start

```bash
pip install docsforge
docsforge new my-docs
cd my-docs
docsforge serve
```

## Features Included

<div class="grid cards" markdown>

- :material-package-variant-closed-check: **Self-Contained**

  All dependencies vendored. No lockfiles, no version conflicts.

- :material-plug: **Plugin Ecosystem**

  Blog, search, tags, privacy, social, optimize, minify — all built-in.

- :material-palette: **Material Theme**

  Full Material Design theme with light/dark mode, custom colors.

- :material-search-web: **Full-Text Search**

  Built-in Lunr search with highlighting, suggestions, sharing.

- :material-tag: **Tags**

  Tag pages, tag indexes, tag clouds.

- :material-rss: **Blog**

  Full blogging support with authors, categories, RSS.

</div>

## Next Steps

- [Explore Features](features/index.md)
- [Read the Blog](blog/index.md)
- [View Changelog](changelog.md)
