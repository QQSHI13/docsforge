# Migrating from MkDocs / Material for MkDocs

DocsForge is a drop-in replacement for MkDocs + Material for MkDocs. If you have an existing project, migration takes about 5 minutes.

---

## Quick Migration

```bash title="Terminal"
pip install docsforge
cd your-mkdocs-project/
docsforge migrate
docsforge build
docsforge serve
```

That's it. `docsforge migrate` reads your `mkdocs.yml`, converts it to `docsforge.yml`, and reports what changed.

---

## What the Migrate Command Does

### 1. Reads your existing `mkdocs.yml`

No manual copying. The command finds `mkdocs.yml` or `mkdocs.yaml` in the current directory automatically.

### 2. Converts configuration keys

Most MkDocs config keys work identically in DocsForge:

| MkDocs key | DocsForge support |
|---|---|
| `site_name` | ✅ Identical |
| `site_url` | ✅ Identical |
| `nav` | ✅ Identical |
| `theme` | ✅ Identical (Material theme built-in) |
| `plugins` | ✅ Most plugins supported natively |
| `markdown_extensions` | ✅ Identical |
| `extra_css` / `extra_javascript` | ✅ Identical |
| `strict` | ✅ Identical |
| `docs_dir` | ✅ Supported |

### 3. Analyzes your plugins

The migration command checks each plugin and tells you:

- **Supported** — Works out of the box (search, tags, blog, info, meta, privacy, social, minify, offline, optimize, typeset)
- **Unsupported** — Needs attention (custom third-party plugins, i18n, mkdocstrings)

Example output:

```
Supported plugins (2):
  ✓ search
  ✓ tags

Attention needed (1):
  ⚠ mkdocstrings: API docs not included. Consider using external tools.
```

### 4. Creates `docsforge.yml`

Your new config file. The old `mkdocs.yml` is backed up to `mkdocs.yml.backup`.

### 5. Shows next steps

```
Next steps:
  1. Review docsforge.yml for any needed adjustments
  2. Run 'docsforge build' to test the migration
  3. Run 'docsforge serve' for live preview
  4. When satisfied, you can remove mkdocs.yml
```

---

## Preview Before Committing

Run with `--dry-run` to see what would change without writing anything:

```bash
docsforge migrate --dry-run
```

This is useful for:

- CI/CD pipelines that validate migrations
- Reviewing changes before committing
- Understanding what DocsForge does differently

---

## Handling Plugin Differences

### Plugins that work identically

These MkDocs/Material plugins are built into DocsForge — **no separate install needed**:

| Plugin | Notes |
|---|---|
| `search` | Built-in, Lunr.js client-side search |
| `tags` | Built-in, tag pages and indexes |
| `blog` | Built-in, full blogging engine |
| `info` | Built-in, site information |
| `meta` | Built-in, meta tags |
| `privacy` | Built-in, self-hosts external assets |
| `social` | Built-in, social cards |
| `minify` | Built-in, HTML/CSS/JS minification |
| `offline` | Built-in, PWA service worker |
| `optimize` | Built-in, image optimization |
| `typeset` | Built-in, typographic enhancements |

### Plugins that need attention

| Plugin | Status | Alternative |
|---|---|---|
| `i18n` | Not yet supported | Use single-language docs for now |
| `mkdocstrings` | Not included | Use external API doc generators |
| `gen-files` | Not supported | Pre-build scripts |
| `literate-nav` | Not supported | Standard `nav:` configuration |
| `exclude` | Not needed | Use `exclude_docs` in config |

### Custom third-party plugins

Most MkDocs plugins that don't depend on MkDocs internals work with DocsForge. If a plugin fails, the error message will tell you why.

---

## Key Differences from MkDocs

### Zero CDN calls

MkDocs + Material fetches Google Fonts, KaTeX, and Mermaid from CDNs during build. DocsForge **vendors everything**:

- **KaTeX** — included for math rendering
- **Mermaid** — included for diagrams
- **Fonts** — downloaded once by the privacy plugin, then self-hosted
- **Icons** — all 14,000+ included in the package

This means:

- ✅ Builds work offline / in air-gapped environments
- ✅ No external network dependency in CI/CD
- ✅ Faster builds (no HTTP requests)
- ✅ Better privacy (no font requests from user browsers)

### PWA / Offline support

Every DocsForge site includes a **service worker** that caches all assets. After the first visit, your documentation works offline. This is built-in — no configuration needed.

MkDocs + Material has no equivalent feature.

### Built-in blog

The blogging plugin is included and pre-configured. Add a `blog/` directory and start writing:

```yaml
nav:
  - Blog:
    - blog/index.md
```

No separate plugin install, no extra configuration.

---

## Migration Checklist

- [ ] Run `docsforge migrate` in your project directory
- [ ] Review the migration report for unsupported plugins
- [ ] Check `docsforge.yml` looks correct
- [ ] Run `docsforge build` — verify no errors
- [ ] Run `docsforge serve` — click around, check formatting
- [ ] Test search, dark mode, mobile layout
- [ ] If using math: verify `$$...$$` renders correctly
- [ ] If using diagrams: verify Mermaid/TikZ renders correctly
- [ ] Commit `docsforge.yml` to version control
- [ ] Remove `mkdocs.yml` (or keep as backup)
- [ ] Update CI/CD to use `docsforge build` instead of `mkdocs build`

---

## Rollback

If something goes wrong, your original `mkdocs.yml` is backed up:

```bash
mv docsforge.yml docsforge.yml.new
mv mkdocs.yml.backup mkdocs.yml
```

Then reinstall MkDocs if needed:

```bash
pip install mkdocs-material
```

---

## Getting Help

- 📖 [Full documentation](https://qqshi13.github.io/docsforge-docs/)
- 🐙 [GitHub Issues](https://github.com/QQSHI13/docsforge/issues)
- The migration command shows specific warnings for your project — read them carefully

---

## Why Migrate?

MkDocs is no longer actively maintained. Material for MkDocs is in maintenance mode. DocsForge picks up where they left off — with active development, new features, and a commitment to keeping documentation tooling modern and reliable.

**Migration takes 5 minutes. The benefits last for years.**
