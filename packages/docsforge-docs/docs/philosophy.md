# Philosophy

DocsForge exists because we believe documentation should be **as easy as possible**.

## The problem

Modern docs tools require too much setup. What should be "write Markdown, get a website" often becomes:

- Configure 10+ Markdown extensions
- Install a theme separately
- Add plugins one by one
- Set up CDN scripts for math
- Configure client-side JS for syntax highlighting
- Debug why something broke after an update

## Our principles

### 1. Zero config for core features

**Everything you need works without configuration.**

Write `$$...$$` → math renders. Write `!!! note` → admonition appears. Write ` ```python ` → code highlights. All 31 Markdown extensions and 7 plugins are loaded by default.

You configure only what you want to customize, not what you need to exist.

### 2. Self-contained

**After `pip install docsforge`, you own everything.**

The theme, all plugins, all extensions, KaTeX, fonts, and Pygments are bundled inside the package. No CDN calls at runtime. No external fetches during build. Works offline.

### 3. Stable

**Your docs build the same way in 10 years.**

Because everything is vendored in the package, version-pinning the package pins the entire toolchain. No transitive dependency surprises.

### 4. Material quality

**DocsForge is Material for MkDocs, made simpler.**

We didn't reinvent the theme. We took the world's most popular documentation theme and made it work without configuration. You get the same professional look, the same responsive layout, the same dark mode — just without the setup.

## What we removed

| Feature | Why removed |
|---------|-------------|
| `typeset` | Users can write Unicode directly |
| `optimize` | Requires external `pngquant` binary |
| `social` | Requires Pillow + CairoSVG |
| `projects` | Niche multi-project feature |
| `offline` | Privacy plugin covers most use cases |
| `group` | Plugin orchestrator (niche) |

## What we changed

| Before (Material/MkDocs) | After (DocsForge) |
|---------------------------|-------------------|
| Config file `docsforge.yml` | `docsforge.yml` |
| Theme via `mkdocs.themes` | `docsforge.themes` |
| Manually list all extensions | 31 loaded by default |
| Manually list all plugins | 7 loaded by default |
| `extra_javascript` for KaTeX | KaTeX vendored, zero config |
| Client-side JS for highlighting | Pygments at build time |

## Our goal

> `pip install docsforge`, write Markdown, done.
