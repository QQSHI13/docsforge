# Migration Guide

Moving from MkDocs/Material to DocsForge is straightforward for most sites. This guide covers what migrates easily and what requires effort.

## Easy to Migrate (Zero/Low Effort)

| Feature | Status | Notes |
|---------|--------|-------|
| **Markdown content** | ✅ Direct | All `.md` files work as-is |
| **Navigation (`nav`)** | ✅ Direct | `nav:` section copies over directly |
| **Theme settings** | ✅ Direct | Colors, fonts, logos, favicons |
| **Extra CSS/JS** | ✅ Direct | `extra_css`, `extra_javascript` |
| **Markdown extensions** | ✅ Direct | admonition, pymdownx, etc. |
| **Search** | ✅ Direct | Built-in, no config needed |
| **Tags** | ✅ Direct | `tags:` plugin built-in |
| **Git revision info** | ✅ Direct | Git dates displayed automatically |
| **PWA / Service Worker** | ✅ Direct | Built-in, auto-generated |
| **Sitemap** | ✅ Direct | Auto-generated |

## Requires Some Effort

| Feature | Status | Migration Path |
|---------|--------|---------------|
| **Custom hooks** | ⚠️ Adapt | Rewrite as DocsForge plugins or use `hooks:` if compatible |
| **Custom plugins** | ⚠️ Adapt | Check if DocsForge has equivalent; otherwise rewrite |
| **Custom templates** | ⚠️ Adapt | Template paths differ; check `docsforge/templates/` |
| **Insiders features** | ⚠️ Adapt | Many are included in DocsForge; check [feature parity](#feature-parity-material-vs-docsforge) |
| **Privacy plugin** | ⚠️ Built-in | DocsForge includes privacy features by default |
| **Optimize plugin** | ⚠️ Built-in | Asset optimization runs automatically post-build |
| **Tags layout** | ⚠️ Changed | Custom tag templates moved from `fragments/tags/{layout}/` to `fragments/tags/{layout}-tag.html` and `fragments/tags/{layout}-listing.html` (flattened directory structure) |

## Requires Significant Effort

| Feature | Status | Notes |
|---------|--------|-------|
| **Post-build scripts** | 🔧 Custom | Node.js/Python scripts that modify built HTML need porting |
| **Deep MkDocs internals** | 🔧 Custom | Plugins that monkey-patch MkDocs classes |
| **Custom extensions** | 🔧 Custom | Python markdown extensions with MkDocs-specific logic |

## OI Wiki Specific Migration Notes

OI Wiki uses several advanced features. Here's how each maps:

| OI Wiki Feature | DocsForge Equivalent | Effort |
|-----------------|---------------------|--------|
| `hooks/on_env.py` (nav_math filter) | Custom plugin or hook | Medium |
| `toggle-sidebar` plugin | Theme customization | Low |
| `document-offsets-injection` extension | Built-in or custom plugin | Medium |
| `extra: disqus` | Disqus integration (manual) | Low |
| `extra: pagetime` | Built-in git date display | None |
| `_static/css/extra.css` | `extra_css` — direct copy | None |
| `_static/js/math-csr.js` | `extra_javascript` — direct copy | None |
| MathJax external CDN | Built-in KaTeX or MathJax | Low |
| Post-build Node scripts | Custom build pipeline | High |

### Estimated Migration Effort

- **Basic content + styling**: < 1 hour
- **Custom hooks + extensions**: 2–4 hours
- **Post-build pipeline**: 4–8 hours
- **Full OI Wiki migration**: ~1–2 days for a developer familiar with both systems

## Feature Parity: Material vs DocsForge

| Feature | Material | DocsForge |
|---------|----------|-----------|
| Material theme | ✅ | ✅ (included) |
| Search | ✅ | ✅ (built-in) |
| Tags | ✅ | ✅ (built-in) |
| Social cards | ✅ (Insiders) | ❌ Not built-in |
| Blog | ✅ (Insiders) | ✅ (built-in) |
| Privacy plugin | ✅ (Insiders) | ✅ (built-in) |
| Optimize plugin | ✅ (Insiders) | ✅ (auto post-build) |
| PWA / Offline | ✅ (Insiders) | ✅ (built-in) |
| Git revision dates | ✅ (plugin) | ✅ (built-in) |
| Minification | ✅ (Insiders) | ✅ (auto) |
| Built-in icons | ✅ | ✅ (58MB bundled) |
| Instant navigation | ✅ | ✅ |
| Custom admonitions | ✅ | ✅ |
| Mermaid diagrams | ✅ (plugin) | ✅ (built-in) |
| Code annotations | ✅ (Insiders) | ✅ (built-in) |
| Content tabs | ✅ | ✅ |
| Data tables | ✅ | ✅ |
| Tooltips | ✅ | ✅ |

## Step-by-Step Migration

### 1. Backup Your Site
```bash
cp mkdocs.yml mkdocs.yml.bak
git add -A && git commit -m "backup before docsforge migration"
```

### 2. Create `docsforge.yml`

Copy your `mkdocs.yml` to `docsforge.yml`. Most settings work directly:

```yaml
site_name: Your Site
site_url: https://yourdomain.com
copyright: Copyright © 2025

nav:
  - Home: index.md
  # ... copy your nav structure

# Theme settings work as-is
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

# Extra CSS/JS copy directly
extra_css:
  - stylesheets/extra.css
extra_javascript:
  - javascripts/extra.js

# Markdown extensions copy directly
markdown_extensions:
  - admonition
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  # ... etc

plugins:
  - tags
  - search
  # - blog        # built-in, customize only if needed
```

### 3. Convert Config Keys

DocsForge uses `docsforge.yml` with the same schema as `mkdocs.yml`. Replace these keys:

| MkDocs | DocsForge |
|--------|-----------|
| `mkdocs.yml` | `docsforge.yml` |
| `site_dir` | `site_dir` (same) |
| `docs_dir` | `docs_dir` (same) |
| `plugins` | `plugins` (same) |

### 4. Install DocsForge
```bash
pip install docsforge
```

### 5. Build and Test
```bash
cd your-project
docsforge build
# Check site/ directory
docsforge serve
```

### 6. Deploy

DocsForge outputs static HTML to `site/` — deploy to any static host. See [Deployment Guide](deployment-guide.md) for platform-specific instructions.

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `plugin not found` | Plugin not in DocsForge | Check [feature parity](#feature-parity-material-vs-docsforge) or install separately |
| `theme not found` | Material theme path | DocsForge bundles Material; use `name: material` |
| Custom hook fails | MkDocs API differences | Update hook to use DocsForge APIs |
| CSS/JS not loading | Path resolution | Check paths relative to `docs_dir` |
| Search not working | Missing index | Ensure `search` plugin is in `plugins:` |

## Getting Help

- GitHub Issues: [github.com/QQSHI13/docsforge/issues](https://github.com/QQSHI13/docsforge/issues)
- Docs: [qqshi13.github.io/docsforge-docs](https://qqshi13.github.io/docsforge-docs/)
