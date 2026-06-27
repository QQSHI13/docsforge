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


def test_instant_navigation(context_page):
    """Material 'instant' nav swaps page content without a full reload; the
    destination is fetched through the SW's serveCurrentPage."""
    base_url, page, _ = context_page
    page.goto(base_url, wait_until="networkidle")
    _sw_ready(page)
    page.click("a[href$='second/'], a[href$='second.md']")
    page.wait_for_function("document.body.innerText.includes('UniqueTokenSecond')", timeout=8000)
    assert page.url.rstrip("/").endswith("second") or "second" in page.url


def test_search_typeahead(context_page):
    """Typing in the search box yields suggestions from the prebuilt index."""
    base_url, page, _ = context_page
    page.goto(base_url, wait_until="load")
    _sw_ready(page)
    # Open the search modal via the "/" shortcut (Material) — more reliable
    # than clicking the icon, whose selector varies across theme versions.
    page.keyboard.press("/")
    try:
        page.wait_for_selector("input.md-search__input", timeout=4000)
    except Exception:
        pytest.skip("search UI not present in this theme config")
    page.fill("input.md-search__input", "")
    page.type("input.md-search__input", "searchable", delay=60)
    page.wait_for_selector(".md-search-result__item", timeout=12000)
    results = page.inner_text(".md-search-result")
    assert "Second" in results or "searchable" in results.lower()


def test_dev_server_matches_deployed(served_dev):
    """`docsforge serve` must install the SW and serve pages offline just like a
    deployed site (the serve == build parity promise)."""
    from playwright.sync_api import sync_playwright

    url = served_dev
    p = sync_playwright().start()
    browser = p.chromium.launch()
    context = browser.new_context()
    page = context.new_page()
    try:
        page.goto(url, wait_until="load")  # not networkidle: livereload keeps a WS open
        _sw_ready(page)
        # Offline reload must serve the cached page.
        context.set_offline(True)
        page.reload(wait_until="load")
        assert "Welcome" in page.inner_text("body")
    finally:
        context.close()
        browser.close()
        p.stop()
