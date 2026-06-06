# DocsForge v10.8.4 Release Notes

## Bug Fixes

### Search index 404 (CRITICAL)
**Problem:** Search was broken on all non-root pages. The URL `search_index.json` was being resolved relative to the current page instead of the site root, causing 404 errors like:
```
GET /docsforge/getting-started/getting-started/search/search_index.json 404
```

**Root cause:** In `build.py`, `base_url` was computed backwards using `get_relative_url('.', page.url)` which returns the path *from root to page* instead of *from page to root*. The template injects this as `base` in the JS config, and the browser resolves `search/search_index.json` against it, producing a duplicated path.

**Fix:** Changed to `get_relative_url(page.url, '.')` which correctly returns `../../` for a page at `getting-started/getting-started/`.

Also fixed the same bug in `_build_template()` for non-error templates (like `search.html`).

### Sidebar overlapping footer
**Problem:** On desktop, the sidebar had `height: 0` with no `max-height` on its scroll container. This allowed the sidebar to grow indefinitely, causing:
- Sidebar content from all sections to remain visible
- Visual overlap with the footer when scrolling to the bottom of the page
- The "index of current part and index of next part" appearing to overlap

**Fix:** Added CSS `max-height: calc(100vh - 2.4rem)` to `.md-sidebar__scrollwrap` on desktop (`min-width: 60em`), with `calc(100vh - 4.8rem)` when the header is lifted (tabs sticky). This constrains the sidebar to the viewport and enables proper scrolling.

## Files changed
- `docsforge/build.py` — Fixed `base_url` computation in `get_context()` and `_build_template()`
- `docsforge/templates/base.html` — Added CSS fix for sidebar max-height
- `docsforge/__init__.py` — Version bump to 10.8.4
