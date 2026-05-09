# Plugins

DocsForge includes all Material plugins, accessible via `material/*` namespace.

## Built-in Plugins

### Search

```yaml
plugins:
  - search:
      separator: '[\s\-]+'
```

Features:
- Full-text search with Lunr
- Search highlighting
- Search suggestions
- Search sharing

### Blog

```yaml
plugins:
  - blog:
      blog_dir: blog
```

Features:
- Author profiles
- Categories
- Archive pages
- RSS feeds
- Draft posts

### Tags

```yaml
plugins:
  - tags:
      tags_file: tags.md
```

Features:
- Tag pages
- Tag indexes
- Tag clouds
- Shadow tags

### Privacy

```yaml
plugins:
  - privacy
```

Downloads and inlines external assets (fonts, scripts, images) for GDPR compliance.

### Social

```yaml
plugins:
  - social
```

Auto-generates social card images for every page. Needs:
```bash
pip install docsforge[imaging]
```

### Optimize

```yaml
plugins:
  - optimize:
      optimize_png: true
      optimize_jpg: true
```

Optimizes images. Needs `pngquant`:
```bash
apt install pngquant
```

### Minify

```yaml
plugins:
  - minify:
      minify_html: true
      minify_js: true
      minify_css: true
```

Minifies HTML, JS, and CSS files.
