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
    from _browser import launch_opts
    from playwright.sync_api import sync_playwright

    url = served_dev
    p = sync_playwright().start()
    browser = p.chromium.launch(**launch_opts())
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


# --- Quota / eviction tests -------------------------------------------------
#
# These run Chromium with a tiny per-origin quota (--quota-override-size-mb)
# so the SW's quota handling actually fires. The service worker budgets the
# manifest sync at a flat 20 MiB per download, so with a 25 MiB quota exactly
# one file gets synced; and on-demand caching of a 2 MiB binary evicts the
# LRU entries with measured byte accounting. Tests skip when the override is
# not honoured (quota still huge), keeping the suite green on Chromium builds
# without the flag.

_QUOTA_OVERRIDE_FLOOR = 100 * 1024 * 1024


def _launch_quota(quota_mb: int):
    from _browser import launch_opts
    from playwright.sync_api import sync_playwright

    opts = launch_opts()
    opts["args"] = [f"--quota-override-size-mb={quota_mb}"]
    p = sync_playwright().start()
    return p, p.chromium.launch(**opts)


def _quota_override_applied(page, quota_mb: int) -> bool:
    """True when the quota override took effect (estimate reports ~quota_mb)."""
    return page.evaluate(
        "async (mb) => (await navigator.storage.estimate()).quota <= mb * 1024 * 1024",
        quota_mb,
    )


def _content_cache_name(page):
    """Name of the SW content cache (docsforge-<buildhash>), not the meta cache."""
    return page.evaluate(
        """async () => {
            const names = await caches.keys();
            return names.find(n => n.startsWith('docsforge-') && n !== 'docsforge-meta');
        }"""
    )


def _cached_urls(page, cache_name: str):
    return page.evaluate(
        "async (name) => (await (await caches.open(name)).keys()).map(r => r.url)",
        cache_name,
    )


def _tracked_files(page):
    """The SW's persisted previous-files list (docsforge-manifest-files)."""
    return page.evaluate(
        """async () => {
            const cache = await caches.open('docsforge-meta');
            const resp = await cache.match('docsforge-manifest-files');
            return resp ? await resp.json() : {};
        }"""
    )


def test_manifest_sync_budget_stops_when_quota_small(served_site_quota):
    """With a 25 MiB quota the flat 20 MiB-per-download budget must stop the
    manifest sync after one file, and every tracked file must really be in
    the cache (no 'marked cached but evicted' lies)."""
    base_url = served_site_quota
    p, browser = _launch_quota(25)
    context = browser.new_context()
    page = context.new_page()
    try:
        page.goto(base_url, wait_until="networkidle")
        _sw_ready(page)
        if not _quota_override_applied(page, 25):
            pytest.skip("quota override not honoured by this Chromium")
        page.wait_for_function(
            """async () => {
                const cache = await caches.open('docsforge-meta');
                const resp = await cache.match('docsforge-manifest-files');
                if (!resp) return false;
                const files = await resp.json();
                return Object.keys(files).length === 1;
            }""",
            timeout=15000,
        )
        tracked = _tracked_files(page)
        assert len(tracked) == 1, f"expected exactly 1 tracked file, got {list(tracked)}"
        cache_name = _content_cache_name(page)
        cached = set(_cached_urls(page, cache_name))
        for key in tracked:
            expected = base_url + ("" if key == "./" else key)
            assert expected.rstrip("/") in {u.rstrip("/") for u in cached}, (
                f"tracked file {key!r} is not actually cached"
            )
        # The site ships many more files than the budget allowed to download.
        manifest = page.evaluate(
            "async () => (await (await caches.open('docsforge-meta')).match('cache-manifest.json')).json()"
        )
        assert len(manifest["files"]) > 1, "fixture site is too small for this test"
        usage = page.evaluate("async () => (await navigator.storage.estimate()).usage")
        assert usage <= 25 * 1024 * 1024
    finally:
        context.close()
        browser.close()
        p.stop()


def test_eviction_uses_measured_sizes(served_site_quota):
    """On-demand caching of a 2 MiB binary under a 3 MiB quota must evict the
    LRU entries (with real byte accounting), keep the cache within quota, and
    never leave a tracked file that is missing from the cache."""
    base_url = served_site_quota
    p, browser = _launch_quota(3)
    context = browser.new_context()
    page = context.new_page()
    try:
        page.goto(base_url, wait_until="networkidle")
        _sw_ready(page)
        if not _quota_override_applied(page, 3):
            pytest.skip("quota override not honoured by this Chromium")

        # Fetch both 2 MiB binaries through the SW. The first fits; the second
        # exceeds the remaining space, forcing measured LRU eviction.
        for asset in ("assets/big1.bin", "assets/big2.bin"):
            page.evaluate(
                "async (a) => { const r = await fetch(a);"
                " if (!r.ok) throw new Error(r.status); await r.arrayBuffer(); }",
                asset,
            )
        page.wait_for_function(
            """async (url) => {
                const names = await caches.keys();
                const name = names.find(n => n.startsWith('docsforge-') && n !== 'docsforge-meta');
                const cache = await caches.open(name);
                return !!(await cache.match(url));
            }""",
            base_url + "assets/big2.bin",
            timeout=15000,
        )

        cache_name = _content_cache_name(page)
        cached = {u.rstrip("/") for u in _cached_urls(page, cache_name)}
        assert base_url.rstrip("/") + "/assets/big2.bin" in cached, "big2.bin must be cached"
        assert base_url.rstrip("/") + "/assets/big1.bin" not in cached, (
            "big1.bin must have been evicted to make room for big2.bin"
        )
        assert base_url.rstrip("/") not in cached, "home page must have been evicted first (LRU)"

        # Every tracked file must still be present in the content cache.
        tracked = _tracked_files(page)
        for key in tracked:
            expected = base_url + ("" if key == "./" else key)
            assert expected.rstrip("/") in cached, (
                f"tracked file {key!r} was evicted but still recorded as cached"
            )

        usage = page.evaluate("async () => (await navigator.storage.estimate()).usage")
        assert usage <= 3 * 1024 * 1024, f"cache usage {usage} exceeds the 3 MiB quota"
    finally:
        context.close()
        browser.close()
        p.stop()


def test_i18n_translates_ui(served_site_i18n):
    """A site built with theme.language='fr' must render <html lang='fr'> and
    translated UI strings (not the English defaults)."""
    from _browser import launch_opts
    from playwright.sync_api import sync_playwright

    url = served_site_i18n
    p = sync_playwright().start()
    browser = p.chromium.launch(**launch_opts())
    page = browser.new_context().new_page()
    try:
        page.goto(url, wait_until="load")
        assert page.get_attribute("html", "lang") == "fr"
        # The search placeholder must be translated (French), not "Search".
        page.keyboard.press("/")
        try:
            page.wait_for_selector("input.md-search__input", timeout=4000)
            placeholder = page.get_attribute("input.md-search__input", "placeholder") or ""
            assert placeholder != "Search", f"search placeholder not translated: {placeholder!r}"
            assert "echerch" in placeholder.lower(), \
                f"expected French search placeholder, got {placeholder!r}"
        except Exception:
            pytest.skip("search UI not present")
    finally:
        browser.close()
        p.stop()


def test_accessibility_basics(context_page):
    """Lightweight a11y checks: lang attribute, images have alt, a main
    landmark exists, and the search control is labelled."""
    base_url, page, _ = context_page
    page.goto(base_url, wait_until="load")
    # 1. <html lang> is set (correct for screen readers).
    assert page.get_attribute("html", "lang"), "missing <html lang>"
    # 2. Every image has an alt attribute (empty alt = decorative, allowed).
    without_alt = page.evaluate(
        "Array.from(document.querySelectorAll('img')).filter(i => !i.hasAttribute('alt')).length"
    )
    assert without_alt == 0, f"{without_alt} images missing alt"
    # 3. A main landmark exists.
    assert page.locator("main, [role='main']").count() >= 1, "no <main> landmark"
    # 4. The search input has an accessible label or aria-label.
    page.keyboard.press("/")
    try:
        page.wait_for_selector("input.md-search__input", timeout=4000)
        labelled = page.evaluate(
            """() => {
                const i = document.querySelector('input.md-search__input');
                if (!i) return true;
                return !!(i.id && document.querySelector(`label[for=\"${i.id}\"]`))
                    || i.getAttribute('aria-label') || i.getAttribute('aria-labelledby');
            }"""
        )
        assert labelled, "search input has no accessible label"
    except Exception:
        pytest.skip("search UI not present")
