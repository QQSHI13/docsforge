"""Browser E2E: service worker install, offline, search, prefetch."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e


def _sw_ready(page, timeout=8000):
    """Wait until the service worker is activated and controlling the page."""
    page.wait_for_function(
        "navigator.serviceWorker.controller !== null", timeout=timeout
    )


def test_page_loads(context_page):
    base_url, page, _ = context_page
    page.goto(base_url, wait_until="networkidle")
    assert "E2E" in page.title() or "Home" in page.inner_text("body")


def test_service_worker_installs_and_caches_home(context_page):
    base_url, page, _ = context_page
    page.goto(base_url, wait_until="networkidle")
    _sw_ready(page)
    # The home page must be in the SW cache after loading.
    cached = page.evaluate(
        """async () => {
            const cache = await caches.open((await caches.keys())[0]);
            const r = await cache.match(location.href);
            return r ? await r.text() : null;
        }"""
    )
    assert cached is not None, "home page was not cached by the SW"
    assert "<html" in cached.lower()


def test_offline_reload_serves_cached_page(context_page):
    base_url, page, context = context_page
    page.goto(base_url, wait_until="networkidle")
    _sw_ready(page)
    # Go offline and reload — the SW must serve the cached home page.
    context.set_offline(True)
    page.reload(wait_until="networkidle")
    body = page.inner_text("body")
    assert "Welcome" in body, "offline reload did not serve the cached page"


def test_search_index_is_served(context_page):
    base_url, page, _ = context_page
    page.goto(base_url, wait_until="networkidle")
    # The search index must be built and served. Use Playwright's request API
    # (bypasses SW-startup timing races in the page's own fetch()).
    resp = page.request.get(base_url + "search/search_index.json")
    assert resp.ok, f"search_index.json not served: {resp.status}"
    data = resp.json()
    assert len(data["docs"]) > 0, "search_index.json has no docs"


def test_link_hover_prefetches_destination(context_page):
    base_url, page, _ = context_page
    page.goto(base_url, wait_until="networkidle")
    _sw_ready(page)
    # Hover the link to /second — the prefetch script should cache it.
    page.hover("a[href$='second/'], a[href$='second.md']")
    page.wait_for_function(
        """async () => {
            if (!caches) return false;
            const keys = await caches.keys();
            if (!keys.length) return false;
            const cache = await caches.open(keys[0]);
            const r = await cache.match(new URL('second/', location.href));
            return r !== undefined;
        }""",
        timeout=8000,
    )
    # Now go offline and navigate — second/ should load from cache.
    page.context.set_offline(True)
    page.goto(base_url + "second/", wait_until="networkidle")
    assert "Another page" in page.inner_text("body")
