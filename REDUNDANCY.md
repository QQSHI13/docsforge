# DocsForge Redundancy Analysis

## Executive Summary

DocsForge inherited a lot of baggage from the MkDocs → ProperDocs → DocsForge migration path. Since we're dropping backwards compatibility for v11, **~15% of the codebase** can be removed or consolidated.

---

## 🔴 Remove Completely (No Longer Needed)

### 1. `_vendor_shims/__init__.py`
**Location:** `docsforge/_vendor_shims/__init__.py`
**What it does:** `sys.modules['mkdocs'] = sys.modules['docsforge']` and `sys.modules['properdocs'] = sys.modules['docsforge']`
**Why remove:** This was a transition shim so that `import mkdocs` still worked after you removed the `_vendor/` directory. With no backwards compatibility, this is dead code.
**Impact:** Any code doing `import mkdocs` or `import properdocs` will break. But since we're not supporting that, fine.
**Also remove:** The entire `_vendor_shims/` directory.

### 2. MkDocs 2.0 Warning Banner
**Location:** `docsforge/themes/material/templates/__init__.py`
**What it does:** Prints a scary red warning to stderr about MkDocs 2.0 when `is_mkdocs()` detects the binary name is `mkdocs`.
**Why remove:** We are not MkDocs. The warning is about a future MkDocs 2.0 that breaks plugins. DocsForge is already the solution. The warning confuses users.
**Impact:** Removes stderr spam. The `colorama` dependency might become unused if nothing else uses it.

### 3. `overrides/hooks/shortcodes.py`
**Location:** `docsforge/overrides/hooks/shortcodes.py`
**What it does:** Custom Material shortcodes (`<!-- md:version -->`, `<!-- md:sponsors -->`, `<!-- md:flag -->`, etc.) that generate badges and links.
**Why remove:** These shortcodes are specific to Material's **own documentation site** (mkdocs-material's docs, not users' docs). They reference paths like `insiders/index.md`, `conventions.md`, `changelog/index.md` that only exist in Material's docs. No general user will ever use them.
**Impact:** Users who copied Material's docs verbatim might lose badge rendering. But they shouldn't be using internal shortcodes anyway.

### 4. `overrides/hooks/translations.py`
**Location:** `docsforge/overrides/hooks/translations.py`
**What it does:** Hook that scans `src/templates/partials/languages/*.html` and generates a translation status table for the "Changing the language" setup page.
**Why remove:** Also specific to Material's own documentation site. It expects a `src/templates/partials/languages/` directory that doesn't exist in user projects. The `icons` dict of 50+ language-to-flag mappings is only useful for Material's docs.
**Impact:** None for users.

### 5. Multiple Plugin Entry Points in `pyproject.toml`
**Location:** `pyproject.toml` lines 48–82
**What they do:** Register plugins under three namespaces:
- `[project.entry-points."mkdocs.plugins"]` — 7 entries
- `[project.entry-points."properdocs.plugins"]` — 7 entries  
- `[project.entry-points."docsforge.plugins"]` — 7 entries
**Why remove:** With no backwards compatibility, only `docsforge.plugins` matters. The `mkdocs.plugins` and `properdocs.plugins` namespaces are for interop with tools that expect those entry point groups.
**Impact:** Tools that query `mkdocs.plugins` won't find DocsForge plugins. But we're not pretending to be MkDocs anymore.
**What to keep:** Only `[project.entry-points."docsforge.plugins"]` and `[project.entry-points."docsforge.themes"]`.

### 6. `MkDocsConfig` Legacy Alias
**Location:** `docsforge/config/defaults.py:265`
**What it does:** `MkDocsConfig = DocsForgeConfig`
**Why remove:** Used in 20+ places (mostly blog plugin). It's a backwards-compat alias for code that expects `MkDocsConfig`.
**Impact:** Need to update all imports. But since we're doing a clean break, rename everything to `DocsForgeConfig`.
**Files affected:**
- `docsforge/config/defaults.py` (the alias itself)
- `docsforge/plugins/blog/plugin.py` (10+ uses)
- `docsforge/plugins/blog/structure/__init__.py` (8+ uses)
- `docsforge/overrides/hooks/shortcodes.py` (2 uses)
- `docsforge/overrides/hooks/translations.py` (1 use)

### 7. Plugin Namespace Collisions in `plugins/base.py`
**Location:** `docsforge/plugins/base.py`, function `get_plugins()`
**What it does:** Queries both `mkdocs.plugins` and `docsforge.plugins` entry point groups, then merges them.
**Why remove:** If we drop the `mkdocs.plugins` entry points, this dual-query logic is unnecessary.
**Code to clean:**
```python
pluginmaps: dict[str, dict[str, EntryPoint]] = {'docsforge': {}, 'mkdocs': {}}
for prefix in pluginmaps:
    ...
return pluginmaps['mkdocs'] | pluginmaps['docsforge']
```
**Simplify to:** Just query `docsforge.plugins`.

---

## 🟡 Consolidate / Merge

### 8. `utilities/` → `utils/`
**Location:** `docsforge/utilities/filter/` (3 files)
**What it does:** Filter classes (`Filter`, `FileFilter`, `FilterConfig`) used by tags plugin and extensions.
**Why merge:** Having both `utilities/` and `utils/` is confusing. The `utils/` directory has 9 files. `utilities/` has only filter-related code.
**Action:** Move `docsforge/utilities/filter/` → `docsforge/utils/filter/`. Update imports in:
- `docsforge/extensions/preview.py`
- `docsforge/plugins/tags/config.py`
- `docsforge/plugins/tags/plugin.py`
**Then remove:** `docsforge/utilities/` entirely.

### 9. `contrib/search/` vs `plugins/search/`
**Location:** `docsforge/contrib/search/` and `docsforge/plugins/search/`
**What they do:**
- `contrib/search/search_index.py` — Core search index logic (SearchIndex, ContentParser, ContentSection)
- `plugins/search/plugin.py` — Plugin wrapper + Jieba segmentation
- `plugins/search/config.py` — Plugin config schema
**Why merge:** `contrib/` is a legacy MkDocs concept ("contributed" plugins). Since everything is vendored, the distinction is meaningless.
**Action:** Move `contrib/search/search_index.py` → `plugins/search/index.py`. Update imports in:
- `docsforge/plugins/search/plugin.py`
- `docsforge/plugins/search/config.py`
**Then remove:** `docsforge/contrib/` entirely.

### 10. Empty `__init__.py` Files
**Files:**
- `docsforge/commands/__init__.py` — completely empty
- `docsforge/contrib/__init__.py` — completely empty
- `docsforge/plugins/minify/__init__.py` — completely empty
**Note:** In Python 3.3+, these aren't strictly necessary for package discovery. However, keeping them is harmless and avoids edge cases. **Low priority.**

---

## 🟢 Consider Removing (User-Visible)

### 11. `get_deps` Command
**Location:** `docsforge/commands/get_deps.py`
**What it does:** `docsforge get-deps` — reads `docsforge.yml` and prints PyPI packages inferred from plugins.
**Why consider removing:** With everything vendored, there are no external plugin dependencies to infer. The command is a leftover from when MkDocs had external plugins.
**Counter-argument:** Could be useful for third-party plugins. Keep if you want to support external plugins.
**Verdict:** Keep but deprioritize. Not hurting anything.

### 12. `gh_deploy` Command Complexity
**Location:** `docsforge/commands/gh_deploy.py`
**What it does:** `docsforge gh-deploy` — pushes `site/` to `gh-pages` branch with git history manipulation.
**Why consider simplifying:** The command has complex logic for remote branch detection, SHA verification, force push, no-history mode. Most users just want `docsforge build` + GitHub Actions.
**Counter-argument:** Some users still use this workflow.
**Verdict:** Don't remove, but consider a simpler `docsforge deploy` wrapper later.

---

## 📊 Impact Summary

| Change | Files Removed | Files Modified | Lines Saved (est.) |
|--------|--------------|----------------|-------------------|
| Remove `_vendor_shims/` | 1 dir | 0 | ~5 |
| Remove MkDocs 2.0 warning | 1 file | 0 | ~50 |
| Remove `overrides/hooks/` | 2 files | 0 | ~350 |
| Remove `mkdocs.plugins` + `properdocs.plugins` entry points | 0 | 1 (`pyproject.toml`) | ~28 lines |
| Remove `MkDocsConfig` alias + update imports | 0 | 5 files | ~20 lines (alias) + ~20 import changes |
| Simplify `get_plugins()` | 0 | 1 file | ~5 lines |
| Merge `utilities/` → `utils/` | 1 dir | 3 files | 0 (reorg) |
| Merge `contrib/search/` → `plugins/search/` | 1 dir | 2 files | 0 (reorg) |
| **Total** | **~4 dirs, 3 files** | **~12 files** | **~400–500 lines** |

---

## 🗺️ Suggested File Tree After Cleanup

```
docsforge/
├── __init__.py
├── __main__.py
├── commands/
│   ├── build.py
│   ├── get_deps.py
│   ├── gh_deploy.py
│   ├── new.py
│   ├── serve.py
│   └── migrate.py          # NEW in v11
├── config/
│   ├── __init__.py
│   ├── base.py
│   ├── config_options.py
│   └── defaults.py         # No MkDocsConfig alias
├── editor/                 # NEW in v11
│   ├── server.py
│   └── static/
│       ├── index.html
│       ├── app.js
│       ├── style.css
│       └── monaco/
├── exceptions.py
├── extensions/
│   ├── __init__.py
│   ├── emoji.py
│   └── preview.py
├── livereload/
│   └── __init__.py
├── localization.py
├── plugins/
│   ├── __init__.py
│   ├── base.py             # Simplified get_plugins()
│   ├── blog/
│   ├── info/
│   ├── meta/
│   ├── minify/
│   ├── privacy/
│   ├── search/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── plugin.py
│   │   └── index.py        # Was contrib/search/search_index.py
│   └── tags/
├── structure/
│   ├── __init__.py
│   ├── files.py
│   ├── nav.py
│   ├── pages.py
│   └── toc.py
├── theme.py
├── themes/
│   └── material/
│       └── templates/
│           └── ...
└── utils/
    ├── __init__.py
    ├── babel_stub.py
    ├── cache.py
    ├── filters.py           # Was utilities/filter/
    ├── meta.py
    ├── rendering.py
    ├── templates.py
    ├── tikz.py
    └── yaml.py
```

---

## ⚠️ What NOT to Remove

| Feature | Why Keep |
|---------|----------|
| `localization.py` | Used by `theme.py` for Jinja2 i18n. Babel integration is real. |
| `extensions/emoji.py` | Custom twemoji integration, used by config defaults. |
| `extensions/preview.py` | Used for social card / link preview generation. |
| `utils/babel_stub.py` | Fallback when babel is not installed. Needed. |
| `tikz.py` | Unique feature — auto-compiles TikZ to SVG. Selling point. |
| `livereload/` | Dev server WebSocket reload logic. Essential. |

---

## Recommended Order of Removal

1. **First (safe):** Remove `_vendor_shims/`, `overrides/hooks/`, MkDocs 2.0 warning
2. **Second (config):** Clean up `pyproject.toml` entry points
3. **Third (reorg):** Merge `utilities/` → `utils/`, `contrib/` → `plugins/`
4. **Fourth (alias):** Remove `MkDocsConfig`, update all imports
5. **Fifth (plugin base):** Simplify `get_plugins()`

---

*Analysis by Nova ☄️ — 2026-05-27*
