# DocsForge

> **One package. One command. Beautiful docs.**

[![PyPI](https://img.shields.io/pypi/v/docsforge)](https://pypi.org/project/docsforge/)
[![Docs](https://img.shields.io/badge/docs-online-blue)](https://qqshi13.github.io/docsforge-docs/)
[![License](https://img.shields.io/badge/license-LGPL%20v3-blue.svg)](LICENSE)

DocsForge unifies the [ProperDocs](https://github.com/properdocs/properdocs) documentation engine and the [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) theme into a single, installable package. You write content. DocsForge handles the engine, the theme, and the plugins.

📖 **[Documentation](https://qqshi13.github.io/docsforge-docs/)** | 📦 **[PyPI](https://pypi.org/project/docsforge/)** | 🐙 **[GitHub](https://github.com/QQSHI13/docsforge)**

---

## Vision

MkDocs is effectively unmaintained. Material for MkDocs is in maintenance mode. [ProperDocs](https://github.com/properdocs/properdocs) is the actively maintained fork of MkDocs that keeps the ecosystem alive.

DocsForge makes the successor ecosystem effortless:

- **One `pip install`** gets you the engine + theme + recommended plugins.
- **One config file** (`docsforge.yml`) with no boilerplate `plugins:` list.
- **Backward compatible** — existing `mkdocs.yml` files work unchanged.
- **Plugin system stays alive** — we just auto-register Material plugins so you never write a `plugins:` section.

---

## Installation

```bash
pip install docsforge
```

That's it. ProperDocs, Material for MkDocs, and common plugins are installed together.

---

## Quick Start

### 1. Create a new site

```bash
docsforge new my-docs
cd my-docs
```

This scaffolds:

```
my-docs/
├── docsforge.yml          # Config with Material theme pre-selected
└── docs/
    └── index.md           # Starter page
```

### 2. Preview locally

```bash
docsforge serve
```

Material plugins (search, tags, etc.) are **auto-registered** — no `plugins:` list needed.

### 3. Build for production

```bash
docsforge build
```

### 4. Deploy to GitHub Pages

```bash
docsforge gh-deploy
```

---

## Config File

DocsForge looks for config in this priority:

1. `docsforge.yml` / `docsforge.yaml` ← **preferred**
2. `properdocs.yml` / `properdocs.yaml`
3. `mkdocs.yml` / `mkdocs.yaml` ← legacy fallback

### Minimal `docsforge.yml`

```yaml
site_name: My Documentation
site_url: https://example.com/
repo_url: https://github.com/username/repo

# Theme defaults to "material" — you can omit this entirely.
theme:
  name: material

# No plugins: section needed — search, tags, blog, privacy, social
# are auto-registered based on what you have installed.
```

### Advanced — override auto-plugins

If you define `plugins:` yourself, DocsForge **merges** rather than overwrites:

```yaml
site_name: My Docs

plugins:
  search:
    lang: en
  tags:
    tags_file: tags.md
  # blog, privacy, social are still auto-registered if available
```

---

## CLI Reference

| Command | Description |
|---------|-------------|
| `docsforge new <name>` | Scaffold a new project |
| `docsforge serve` | Live-reload dev server |
| `docsforge build` | Static site build |
| `docsforge gh-deploy` | Deploy to GitHub Pages |

All commands accept `-f / --config-file` to override config discovery.

---

## Architecture

```
docsforge/                    # Unified package
├── __init__.py
├── cli.py                    # `docsforge` command (wraps properdocs)
├── config.py                 # Unified config loader
├── plugins/
│   └── auto_register.py      # Pre-loads Material plugins
├── engine/                   # ProperDocs core (git subtree)
│   └── (properdocs source)
└── themes/                   # Material for MkDocs (git subtree)
    └── (mkdocs-material source)
```

**Key decisions:**

1. **Keep the plugin system alive.** Material's plugins (blog, tags, privacy, social, search) are powerful. We auto-register them instead of rewriting them.
2. **ProperDocs dual entrypoints.** ProperDocs already supports both `mkdocs.*` and `properdocs.*` entrypoints, so Material works without code changes.
3. **Unified CLI, not a fork.** We wrap ProperDocs commands; we don't fork the engine.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design record.

---

## License

GPL-3.0-or-later — same as ProperDocs.

---

*DocsForge is a repackaging project, not a fork. It keeps the MkDocs/ProperDocs ecosystem moving forward while the upstreams navigate their maintenance transitions.*
