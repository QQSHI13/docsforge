# DocsForge v10.8.1

## What's Changed

### Code Quality
- **Removed unused imports** across `core/` plugin files:
  - `tags.py`: removed `Dict` (typing), `ListOfItems`, `SubConfig`, `Union`, `Dumper` (yaml)
  - `minify.py`: removed `List`, `Union` (typing)
  - Merged duplicate `collections.abc` import lines in `tags.py`
  - Merged duplicate `docsforge.config_options` imports in `tags.py`
  - Removed orphaned comment blocks from merged files

### Full Changelog (v10.8.0 → v10.8.1)
- v10.8.0: Complete restructuring — all plugins flattened into `core/`, `plugins/` directory removed, Material theme unified into `templates/`
- v10.8.1: Import cleanup and dead code removal

## Current Structure
```
docsforge/
  __init__.py
  build.py, pages.py, nav.py, files.py, theme.py, ...   # engine (33 files)
  core/
    __init__.py
    blog.py
    info.py
    meta.py
    minify.py
    plugin_base.py
    privacy.py
    search.py
    tags.py
  templates/
    ...
```

## Build Verified
- 34 HTML files generated successfully
- All imports working, no circular dependencies
- Clean working tree
