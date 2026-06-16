# Getting started

DocsForge is a self-contained documentation engine. `pip install`, write Markdown, build.

## Installation

```bash
pip install docsforge
```

Requires **Python 3.10+**.

## Quick start

```bash
# Create a new project interactively
docsforge
cd my-docs

# Start the dev server
docsforge serve

# Build for production
docsforge build
```

## What's inside

After running `docsforge` to create a project, your directory looks like this:

``` { .sh .no-copy }
my-docs/
├── docsforge.yml    # Site configuration
├── docs/
│   └── index.md     # Homepage
└── site/            # Build output
```

## Configuration

The smallest valid `docsforge.yml`:

```yaml
site_name: My Project
```

That's it. All plugins, extensions, and theme settings use sensible defaults. Add configuration only when you need to customize.

## Key defaults

| Feature | Default |
|---------|---------|
| Theme | Material (built-in) |
| Plugins | search, tags, blog, info, meta, minify, privacy |
| Markdown extensions | 31 total — all pymdownx + python-markdown |
| Math | KaTeX (vendored, `$$...$$` works) |
| Code highlighting | Pygments (colored syntax) |
| Dark mode | Light/dark toggle in header |
| Fonts | Self-hosted (privacy plugin downloads Google Fonts) |
| Diagrams | TikZ support (auto-compiled to SVG) |
| Offline | Service worker caches all assets |

## What's built in

### 📝 Documentation
- Write Markdown with 31 extensions
- Admonitions, tabs, task lists, footnotes
- Mermaid and TikZ diagrams
- KaTeX math rendering
- Pygments code highlighting

### 🔍 Discovery
- Full-text search (Lunr.js)
- Tags and tag pages
- Navigation with sections and tabs
- Table of contents

### 🎨 Theming
- Material theme with light/dark mode
- Customizable colors and fonts
- 14,000+ icons (Material, FontAwesome, Octicons)

### 📝 Blogging
- Author profiles
- Categories and tags
- Archive pages
- Pagination
- RSS feeds

### 🌐 Publishing
- Static HTML output
- GitHub Pages ready
- PWA with offline support
- Minified HTML/CSS/JS

## Next steps

- [Creating your site](creating-your-site.md)
- [Setting up a blog](blogging.md)
- [Reference](reference/index.md)
