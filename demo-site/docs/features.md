# Features

## Auto-Registered Plugins

DocsForge automatically enables Material plugins **without** requiring a `plugins:` section:

| Plugin | Purpose |
|--------|---------|
| `search` | Full-text search with lunr |
| `tags` | Tag-based navigation |
| `blog` | Blogging support |
| `social` | Social card generation |
| `privacy` | External resource optimization |
| `offline` | Offline-capable builds |
| `optimize` | Asset optimization |

## Theme Features

- **Dark mode** — Toggle between light and dark themes
- **Responsive** — Works on desktop, tablet, mobile
- **Search** — Built-in search with highlighting
- **Navigation** — Automatic nav from directory structure
- **Code blocks** — Syntax highlighting with copy button

## Backward Compatible

Existing `mkdocs.yml` files work unchanged:

```yaml
site_name: My Existing Site
theme:
  name: material
plugins:
  - search
```

Just rename to `docsforge.yml` for the full experience.

---

*Next: [About](about.md)*
