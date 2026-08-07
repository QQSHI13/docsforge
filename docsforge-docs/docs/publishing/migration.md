# Migration Guide

Moving from MkDocs/Material to DocsForge is straightforward for most sites. This guide covers what migrates easily and what requires effort.

## Easy to Migrate (Zero/Low Effort)

| Feature | Status | Notes |
|---------|--------|-------|
| **Markdown content** | :material-check-bold: Direct | All `.md` files work as-is |
| **Navigation (`nav`)** | :material-check-bold: Direct | `nav:` section copies over directly |
| **Theme settings** | :material-check-bold: Direct | Colors, fonts, logos, favicons |
| **Extra CSS/JS** | :material-check-bold: Direct | `extra_css`, `extra_javascript` |
| **Markdown extensions** | :material-check-bold: Direct | admonition, pymdownx, etc. |
| **Search** | :material-check-bold: Direct | Built-in, no config needed |
| **Tags** | :material-check-bold: Direct | `tags:` plugin built-in |
| **Git revision info** | :material-check-bold: Direct | Git dates displayed automatically |
| **PWA / Service Worker** | :material-check-bold: Direct | Built-in, auto-generated |
| **Sitemap** | :material-check-bold: Direct | Auto-generated |

## Requires Some Effort

| Feature | Status | Migration Path |
|---------|--------|---------------|
| **Custom hooks** | :material-alert: Adapt | Rewrite as DocsForge plugins or use `hooks:` if compatible |
| **Custom plugins** | :material-alert: Adapt | Check if DocsForge has equivalent; otherwise rewrite |
| **Custom templates** | :material-alert: Adapt | Template paths differ; check `docsforge/templates/` |
| **Insiders features** | :material-alert: Adapt | Many are included in DocsForge; check [feature parity](#feature-parity-material-vs-docsforge) |
| **Privacy plugin** | :material-alert: Built-in | DocsForge includes privacy features by default |
| **Optimize plugin** | :material-alert: Built-in | Asset optimization runs automatically post-build |
| **Tags layout** | :material-alert: Changed | Custom tag templates moved from `fragments/tags/{layout}/` to `fragments/tags/{layout}-tag.html` and `fragments/tags/{layout}-listing.html` (flattened directory structure) |

## Requires Significant Effort

| Feature | Status | Notes |
|---------|--------|-------|
| **Post-build scripts** | :material-wrench: Custom | Node.js/Python scripts that modify built HTML need porting |
| **Deep MkDocs internals** | :material-wrench: Custom | Plugins that monkey-patch MkDocs classes |
| **Custom extensions** | :material-wrench: Custom | Python markdown extensions with MkDocs-specific logic |

## MkDocs Plugin Migration Guide

MkDocs plugins are not compatible with DocsForge. Below is a mapping of common MkDocs plugins to their DocsForge equivalents or workarounds.

### Built-in (Zero Effort)

These MkDocs plugins have direct built-in equivalents in DocsForge — remove from `plugins:` and they load automatically:

| MkDocs Plugin | DocsForge | Notes |
|---------------|-----------|-------|
| `search` | :material-check-bold: Built-in | Lunr.js search, same behavior. Remove from config. |
| `tags` | :material-check-bold: Built-in | Same `tags:` front matter, same tag pages. Remove from config. |
| `blog` | :material-check-bold: Built-in | Blog with authors, categories, archives, RSS. Remove from config. |
| `minify` | :material-check-bold: Built-in | HTML/CSS/JS minification runs automatically post-build. |
| `meta` | :material-check-bold: Built-in | OpenGraph metadata, social previews. Included by default. |
| `privacy` | :material-check-bold: Built-in | External asset downloading and inlining (Google Fonts, CDN resources). |

### Config-Compatible (Copy Plugin Config)

These MkDocs plugins are not supported, but their features can be replicated with DocsForge's built-in capabilities:

| MkDocs Plugin | DocsForge Equivalent |
|---------------|---------------------|
| `git-revision-date-localized` | Built-in — every page shows git revision dates automatically |
| `git-authors` | Built-in — author info extracted from git history |
| `macros` | Use Jinja2 templates or `extra:` config variables |
| `redirects` | Use web server redirects (Netlify `_redirects`, nginx config, etc.) |
| `awesome-pages` | Navigation is auto-discovered when `nav:` is omitted; use `nav:` for explicit ordering |
| `section-index` | Built-in — section index pages work automatically |
| `tooltipster-links` | Built-in — tooltips on reference links are included in the theme |
| `embed-external` | Use standard Markdown links or `pymdownx.snippets` |
| `include-markdown` | Built-in — `pymdownx.snippets` is enabled by default |
| `mkdocstrings` | Not built-in; use `pymdownx.snippets` or a custom post-build script |

### No Direct Equivalent (Requires Custom Work)

| MkDocs Plugin | Workaround |
|---------------|-----------|
| `mkdocs-material/plugins/social` | Not built-in. Requires Pillow + CairoSVG. Install with `pip install docsforge[imaging]` and configure `social:` plugin manually. |
| `mkdocs-redirects` | Use server-level redirects (Cloudflare `_redirects`, nginx, etc.) |
| `mkdocs-awesome-pages` | Manually specify `nav:` structure |
| `mkdocs-glightbox` | Image lightbox not built-in. Use theme's built-in image zoom if available. |
| `mkdocs-pdf-export` | Use `docsforge build --pdf` (see [PDF export setup](../setup/pdf-export.md)) |
| `mkdocs-static-i18n` | Use the built-in `material/i18n` plugin (see [Internationalization setup](../setup/i18n.md)) |
| `mkdocs-video` | Use standard HTML `<video>` tags in Markdown |
| `mkdocs-gallery` | Use standard Markdown image syntax |
| `mkdocs-jupyter` | Not supported. Export notebooks to Markdown first. |
| `mkdocs-swagger-ui-tag` | Not supported. Use a custom plugin or embed Swagger UI HTML directly. |

### Custom MkDocs Plugins

Plugins that extend MkDocs' `BasePlugin` class or hook into MkDocs events (`on_page_markdown`, `on_page_content`, etc.) need to be rewritten for DocsForge's plugin system:

1. DocsForge uses the same event names (`on_page_markdown`, `on_post_build`, etc.) — many MkDocs plugins can be adapted by changing the import from `mkdocs.plugins` to `docsforge.core.plugin_base`.
2. The config schema uses DocsForge's `Config` class instead of MkDocs' `BaseConfig`.
3. See the [plugin development guide](../advanced/customization.md#custom-plugins) for details.

### Markdown Extensions

All MkDocs-compatible Markdown extensions work directly. DocsForge uses the same `python-markdown` package with `pymdown-extensions`. Copy your `markdown_extensions:` block as-is:

```yaml
markdown_extensions:
  - admonition
  - pymdownx.superfences
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.tasklist:
      custom_checkbox: true
  # ... all your existing extensions work unchanged
```

The 31 most common extensions are already pre-enabled — you only need to list them if you want custom configuration.

### Config Key Migration

| MkDocs / Material Key | DocsForge | Notes |
|-----------------------|-----------|-------|
| `mkdocs.yml` | `docsforge.yml` | Rename the file |
| `theme.name: material` | `theme.name: material` | Same — DocsForge bundles Material |
| `theme.features` | `theme.features` | Same — all Material features supported |
| `theme.palette` | `theme.palette` | Same — color scheme configuration |
| `theme.font` | `theme.font` | Same — font configuration |
| `theme.favicon` | `theme.favicon` | Same — relative to `docs_dir` |
| `theme.logo` | `theme.logo` | Same — relative to `docs_dir` |
| `theme.icon.logo` | `theme.icon.logo` | Same — Material icon reference |
| `markdown_extensions` | `markdown_extensions` | **Same** — fully compatible |
| `plugins` | `plugins` | **Partial** — built-in plugins work; third-party need porting |
| `extra_css` | `extra_css` | Same |
| `extra_javascript` | `extra_javascript` | Same |
| `extra` | `extra` | Same — custom template variables |
| `site_dir` | `site_dir` | Same |
| `docs_dir` | `docs_dir` | Same |
| `hooks` | `hooks` | Same — but MkDocs hook format may differ |
| `INHERIT` | ❌ Not supported | Use YAML anchors instead |
| `validation` | `validation` | Same |
| `watch` | `watch` | Same — extra paths to watch during serve |

### Deprecated / Removed Keys

| Key | Status | Replacement |
|-----|--------|-------------|
| `strict` | :material-check-bold: Supported | Use `strict: true` in config or `docsforge build --strict` on the CLI |
| `config_file_path` | Internal | Not needed in user config |
| `site_description` | :material-check-bold: Supported | Same key |
| `site_author` | :material-check-bold: Supported | Same key |
| `copyright` | :material-check-bold: Supported | Same key |
| `repo_url` | :material-check-bold: Supported | Same key |
| `repo_name` | :material-check-bold: Supported | Same key |
| `edit_uri` | :material-check-bold: Supported | Same key |
| `remote_branch` | ❌ Removed | Use GitHub Actions for deployment |
| `remote_name` | ❌ Removed | Use GitHub Actions for deployment |
| `use_directory_urls` | :material-check-bold: Supported | Same key (default: true) |
| `dev_addr` | :material-check-bold: Supported | Same key (default: `127.0.0.1:8000`) |
| `site_url` | :material-check-bold: Required | Must be set for social cards, sitemap, RSS |

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
| Material theme | :material-check-bold: | :material-check-bold: (included) |
| Search | :material-check-bold: | :material-check-bold: (built-in) |
| Tags | :material-check-bold: | :material-check-bold: (built-in) |
| Social cards | :material-check-bold: (Insiders) | ❌ Not built-in |
| Blog | :material-check-bold: (Insiders) | :material-check-bold: (built-in) |
| Privacy plugin | :material-check-bold: (Insiders) | :material-check-bold: (built-in) |
| Optimize plugin | :material-check-bold: (Insiders) | :material-check-bold: (auto post-build) |
| PWA / Offline | :material-check-bold: (Insiders) | :material-check-bold: (built-in) |
| Git revision dates | :material-check-bold: (plugin) | :material-check-bold: (built-in) |
| Minification | :material-check-bold: (Insiders) | :material-check-bold: (auto) |
| Built-in icons | :material-check-bold: | :material-check-bold: (58MB bundled) |
| Instant navigation | :material-check-bold: | :material-check-bold: |
| Custom admonitions | :material-check-bold: | :material-check-bold: |
| Mermaid diagrams | :material-check-bold: (plugin) | :material-check-bold: (built-in) |
| Code annotations | :material-check-bold: (Insiders) | :material-check-bold: (built-in) |
| Content tabs | :material-check-bold: | :material-check-bold: |
| Data tables | :material-check-bold: | :material-check-bold: |
| Tooltips | :material-check-bold: | :material-check-bold: |

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
