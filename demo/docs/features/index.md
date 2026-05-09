# Features

DocsForge includes everything you need to build modern documentation sites.

## Core Engine

The underlying engine is vendored from MkDocs 1.6 + Material 9.7, with all imports rewritten to use the internal `_vendor/` packages.

## Plugin System

All Material plugins are available as `material/*`:

| Plugin | Purpose |
|--------|---------|
| `material/blog` | Blogging with authors, categories, RSS |
| `material/search` | Full-text search with Lunr |
| `material/tags` | Tag indexing and pages |
| `material/privacy` | Inline external assets for privacy |
| `material/social` | Auto-generate social card images |
| `material/optimize` | Optimize images (PNG/JPG) |
| `material/minify` | Minify HTML, CSS, JS |
| `material/info` | Info annotations |
| `material/meta` | Metadata management |
| `material/offline` | Offline builds |

## Markdown Extensions

All standard extensions work:

- Admonitions
- Code blocks with highlighting
- Content tabs
- Details/summary
- Tables
- And more...
