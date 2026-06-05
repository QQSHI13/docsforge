# DocsForge v10.8.2

## What's Changed

### Performance Improvements
- **Lazy jieba loading**: Chinese text segmentation dictionary is now loaded only when Chinese content is detected. For non-Chinese sites, this saves ~1 second per build.
- **Parallel page building**: The `_build_page` loop (template rendering + file writing) now uses `ThreadPoolExecutor` for parallel execution. I/O-bound operations benefit from concurrent execution.

### Build Time Improvements
- **Before**: ~3.2 seconds for 34-page docs site
- **After**: ~2.1 seconds (35% faster)
- For non-Chinese sites: up to 50% faster (no jieba dictionary load)

### Code Quality
- Removed unused imports from `__main__.py`, `check.py`, `init.py`

## Full Changelog
- v10.8.0: Complete restructuring — all plugins flattened into `core/`, `plugins/` directory removed
- v10.8.1: Import cleanup across `core/` plugin files
- v10.8.2: Performance improvements — lazy jieba loading + parallel page building

## Build Verified
- 34 HTML files generated successfully
- All imports working, no circular dependencies
- Clean working tree
