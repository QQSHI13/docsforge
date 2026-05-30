# DocsForge Optimization Plan — 2026-05-30

## Goal: Optimize code before implementing user capture features

## Current Performance Baseline
- Build time: ~1.5-2.2 seconds (docsforge-docs site, 31 pages)
- Profile shows: Markdown rendering (1.4s), Jinja2 templates (0.8s), page population (1.5s)

## Optimization Targets

### 1. Per-Page Markdown Extension Setup (High Impact)
**Issue:** `markdown.Markdown()` is instantiated 31 times per build, reinitializing all extensions each time.
**Location:** `structure/pages.py:288`
**Approach:** Cache markdown instance or pre-process config once
**Risk:** Medium — extensions may maintain page-specific state
**Decision:** Document as future optimization, not safe to change now

### 2. Mermaid Config Check Per-Page (Low-Medium Impact)
**Issue:** Mermaid fence check runs for every page (31 times)
**Location:** `structure/pages.py:275-285`
**Fix:** Move to config initialization in `build.py` or `config/defaults.py`
**Risk:** Low — pure config mutation, no state dependency

### 3. Import Overhead (Low Impact)
**Issue:** Some imports may be unused or could be lazy-loaded
**Check:** All top-level imports in hot paths
**Files:** `pages.py`, `files.py`, `nav.py`

### 4. Jinja2 Template Compilation (Medium Impact)
**Issue:** Templates may be recompiled frequently
**Check:** Jinja2 environment caching in `theme.py`
**Fix:** Ensure `auto_reload=False` in production builds

### 5. File I/O Optimization (Medium Impact)
**Issue:** Multiple file reads/writes may not be buffered efficiently
**Check:** `utils.write_file`, `utils.copy_file` patterns

## Quick Wins (30 min total)

1. Move mermaid config to build init (5 min)
2. Add `auto_reload=False` to Jinja2 env for builds (5 min)
3. Check for unused imports (10 min)
4. Verify search index caching works (10 min)

## Larger Optimizations (Future)

1. Parallel page rendering (thread pool for `_populate_page`)
2. Incremental builds (only render changed pages)
3. Markdown extension instance caching (if safe)
4. Search index incremental updates (already partially done with `search_index_prev`)

## What NOT to Optimize

- Don't break correctness for speed
- Don't optimize before adding tests (risky)
- Don't parallelize if extensions aren't thread-safe

## Next Steps

1. Implement quick wins (30 min)
2. Verify build still works
3. Commit + push
4. Move to migration command implementation

---
