from __future__ import annotations

import concurrent.futures
import contextlib
import copy
import gzip
import hashlib
import json
import logging
import mimetypes
import os
import re
import struct
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlsplit

import jinja2
from jinja2.exceptions import TemplateNotFound

import docsforge
from docsforge import templates, utils
from docsforge.asset_optimizer import OPTIMIZER_MANAGED_DIRS, optimize_assets
from docsforge.cache import BuildPlanner, CacheManager, DependencyTracker, FileHasher
from docsforge.exceptions import Abort, BuildError
from docsforge.files import File, Files, InclusionLevel, get_files, set_exclusions
from docsforge.git_info import get_git_page_info, prefetch_git_page_info
from docsforge.nav import Navigation, get_navigation
from docsforge.pages import Page
from docsforge.slugger import SlugRules, compute_rules, write_rules
from docsforge.structure import restore_rendering_page, set_rendering_page

if TYPE_CHECKING:
    import jinja2

    from docsforge.config_defaults import DocsForgeConfig


# Poll interval for blocking waits. Unbounded `Future.result()` /
# `as_completed()` park in lock waits that swallow console Ctrl+C on
# Windows; polling with a short timeout keeps the total wait identical
# while letting signals land between polls (same pattern as the
# livereload rebuild loop).
_INTERRUPTIBLE_POLL = 0.25


def _wait_future(future: concurrent.futures.Future):
    """Wait for one future, staying responsive to KeyboardInterrupt."""
    while True:
        try:
            return future.result(timeout=_INTERRUPTIBLE_POLL)
        except concurrent.futures.TimeoutError:
            continue


def _as_completed(futures):
    """Yield futures in completion order, responsive to KeyboardInterrupt."""
    pending = set(futures)
    while pending:
        done, pending = concurrent.futures.wait(pending, timeout=_INTERRUPTIBLE_POLL)
        yield from done


log = logging.getLogger(__name__)


# Shared fallback lock for page building when the caller does not provide one.
# An RLock: `_build_page` can be re-entered via plugin hooks even when the
# caller passes no lock (callers that do pass one always pass `threading.RLock()`).
_default_page_lock = threading.RLock()


def get_context(
    nav: Navigation,
    files: Sequence[File] | Files,
    config: DocsForgeConfig,
    page: Page | None = None,
    base_url: str = "",
) -> templates.TemplateContext:
    """Return the template context for a given page or template."""
    if page is not None:
        base_url = utils.get_relative_url(page.url, ".")
        if base_url and not base_url.endswith("/"):
            base_url += "/"

        # Inject git revision info into page meta if available and not disabled
        extra_cfg = config.get("extra", {})
        git_enabled = getattr(extra_cfg, "git_revision_date", True) if extra_cfg else True
        # Generated files (File.generated / a plugin's temp source) have no
        # on-disk source, so there is no history to look up.
        if git_enabled and page.file.abs_src_path and not page.meta.get("git_revision_date_localized"):
            git_info = get_git_page_info(page.file.abs_src_path)
            if git_info:
                page.meta["git_revision_date_localized"] = git_info["updated_display"]
                page.meta["git_creation_date_localized"] = git_info["created_display"]

    extra_javascript = [
        utils.normalize_url(str(script), base_url) for script in config.extra_javascript
    ]
    extra_css = [utils.normalize_url(path, base_url) for path in config.extra_css]

    if isinstance(files, Files):
        files = files.documentation_pages()

    i18n_locale = getattr(page.file if page is not None else None, "i18n_locale", None)

    # Sidebar highlight path: the current page plus its ancestors. Templates
    # check membership instead of the global `page.active` flag so page writes
    # can run in parallel without a sidebar-highlight race.
    active_path: set[int] = set()
    if page is not None:
        active_path.add(id(page))
        active_path.update(id(a) for a in page.ancestors)

    return templates.TemplateContext(
        nav=nav,
        pages=files,
        base_url=base_url,
        extra_css=extra_css,
        extra_javascript=extra_javascript,
        docsforge_version=docsforge.__version__,
        build_date_utc=utils.get_build_datetime(),
        config=config,
        page=page,
        lang_partial=templates.resolve_lang_partial(
            i18n_locale or config.theme.get("language"), config.theme.dirs
        ),
        active_path=active_path,
    )


def _build_template(
    name: str, template: jinja2.Template, files: Files, config: DocsForgeConfig, nav: Navigation
) -> str:
    """Return rendered output for given template as a string."""
    # Run `pre_template` plugin events.
    template = config.plugins.on_pre_template(template, template_name=name, config=config)

    if utils.is_error_template(name):
        # Force absolute URLs in the nav of error pages and account for the
        # possibility that the docs root might be different than the server root.
        # See https://github.com/mkdocs/mkdocs/issues/77.
        # However, if site_url is not set, assume the docs root and server root
        # are the same. See https://github.com/mkdocs/mkdocs/issues/1598.
        base_url = urlsplit(config.site_url or "/").path
    else:
        base_url = utils.get_relative_url(name, ".")
        if base_url and not base_url.endswith("/"):
            base_url += "/"

    context = get_context(nav, files, config, base_url=base_url)

    # Run `template_context` plugin events.
    context = config.plugins.on_template_context(context, template_name=name, config=config)

    output = template.render(context)

    # Run `post_template` plugin events.
    return config.plugins.on_post_template(output, template_name=name, config=config)


def _write_if_changed(path: str, data: bytes) -> bool:
    """Write data to path only when the content differs (avoids mtime churn)."""
    try:
        with open(path, "rb") as f:
            if f.read() == data:
                return False
    except OSError:
        pass
    utils.write_file(data, path)
    return True


def _build_theme_template(
    template_name: str,
    env: jinja2.Environment,
    files: Files,
    config: DocsForgeConfig,
    nav: Navigation,
) -> None:
    """Build a template using the theme environment."""
    log.debug(f"Building theme template: {template_name}")

    try:
        template = env.get_template(template_name)
    except TemplateNotFound:
        log.warning(f"Template skipped: '{template_name}' not found in theme directories.")
        return

    output = _build_template(template_name, template, files, config, nav)

    if output.strip():
        output_path = os.path.join(config.site_dir, template_name)
        data = output.encode("utf-8")
        changed = _write_if_changed(output_path, data)
        if changed:
            log.debug(f"Wrote theme template: {template_name}")

        if template_name == "sitemap.xml":
            if not changed and os.path.exists(f"{output_path}.gz"):
                return
            log.debug(f"Gzipping template: {template_name}")
            gz_filename = f"{output_path}.gz"
            with open(gz_filename, "wb") as f:
                timestamp = utils.get_build_timestamp(
                    pages=[f.page for f in files.documentation_pages() if f.page is not None]
                )
                with gzip.GzipFile(
                    # filename="" keeps the build reproducible: writing the
                    # absolute output path into the gzip header would change
                    # the bytes of every build.
                    fileobj=f, filename="", mode="wb", mtime=timestamp
                ) as gz_buf:
                    gz_buf.write(data)
    else:
        log.info(f"Template skipped: '{template_name}' generated empty output.")


def _build_locale_static_templates(
    env: jinja2.Environment,
    files: Files,
    config: DocsForgeConfig,
    nav: Navigation,
) -> None:
    """Render HTML static templates (e.g. 404.html) once per non-default locale.

    Error pages are rendered at build time without a page context, so without
    this they would always show the default language. The locale variants are
    written as sibling files (``404.zh.html``) and served by the service worker
    based on the user's stored preference.
    """
    from urllib.parse import urlsplit

    from docsforge.core.i18n import I18nPlugin

    plugin = next(
        (p for p in config.plugins.values() if isinstance(p, I18nPlugin)),
        None,
    )
    if plugin is None or not plugin._languages:
        return

    base_url = urlsplit(config.site_url or "/").path
    # The language is a GLOBAL template variable: partials/language.html and
    # base.html read `config.theme.language` (and `config.extra.i18n_current_locale`)
    # directly, so there is no render-local override the templates honour —
    # threading it through the context would mean editing every template that
    # reads it. Instead the mutation window is kept as short as possible and
    # both values are restored in a `finally`, so a failing render (or a plugin
    # reading the theme language afterwards) can never observe a locale that is
    # not the site's own. Nothing else runs concurrently here: this function is
    # called sequentially before page rendering starts.
    had_prev_language = "language" in config.theme
    prev_language = config.theme.get("language")
    prev_locale = getattr(config.extra, "i18n_current_locale", None)
    had_prev_locale = hasattr(config.extra, "i18n_current_locale")
    try:
        for template_name in config.theme.static_templates:
            if not template_name.endswith(".html"):
                continue
            template = env.get_template(template_name)
            for locale in plugin.locales:
                if locale == plugin.default_locale:
                    continue
                locale_nav = plugin._locale_navs.get(locale)
                if locale_nav is None:
                    continue
                # `page` stays None so the template renders like the default
                # 404 (absolute base URL, no page fields). The language is
                # switched via the theme language so partials/language.html
                # resolves the right translations.
                config.theme["language"] = locale
                config.extra.i18n_current_locale = locale
                plugin._fix_locale_nav_titles(locale_nav, locale)
                context = get_context(
                    locale_nav, files, config, page=None, base_url=base_url
                )
                context = config.plugins.on_template_context(
                    context, template_name=template_name, config=config
                )
                output = template.render(context)
                output = config.plugins.on_post_template(
                    output, template_name=template_name, config=config
                )
                if output.strip():
                    out_name = template_name.replace(".html", f".{locale}.html")
                    utils.write_file(
                        output.encode("utf-8", errors="xmlcharrefreplace"),
                        os.path.join(config.site_dir, out_name),
                    )
    finally:
        # Restore key *presence*, not just value: a language set to None must
        # not silently become an explicit None after the loop.
        if had_prev_language:
            config.theme["language"] = prev_language
        else:
            config.theme.pop("language", None)
        if had_prev_locale:
            config.extra.i18n_current_locale = prev_locale
        else:
            with contextlib.suppress(AttributeError):
                del config.extra.i18n_current_locale


def _build_extra_template(
    template_name: str, env: jinja2.Environment, files: Files, config: DocsForgeConfig, nav: Navigation
):
    """Build user templates which are not part of the theme."""
    log.debug(f"Building extra template: {template_name}")

    file = files.get_file_from_path(template_name)
    if file is None:
        log.warning(f"Template skipped: '{template_name}' not found in docs_dir.")
        return

    try:
        template = env.from_string(file.content_string)
    except Exception as e:
        log.warning(f"Error reading template '{template_name}': {e}")
        return

    output = _build_template(template_name, template, files, config, nav)

    if output.strip():
        _write_if_changed(file.abs_dest_path, output.encode("utf-8"))
    else:
        log.info(f"Template skipped: '{template_name}' generated empty output.")


def _populate_page(
    page: Page,
    config: DocsForgeConfig,
    files: Files,
    dirty: bool = True,
    plugin_lock: threading.RLock | None = None,
) -> None:
    """Read page content from docs_dir and render Markdown.

    The heavy work — `read_source` (file I/O) and `render` (markdown.convert,
    which uses a per-thread Markdown instance) — is thread-safe and runs
    without the lock. The plugin event calls and `config._current_page` are
    guarded by `plugin_lock` because plugin handlers may mutate shared state.
    """
    lock = plugin_lock or threading.RLock()
    try:
        with lock:
            config._current_page = page
            # Run the `pre_page` plugin event
            page = config.plugins.on_pre_page(page, config=config, files=files)

        page.read_source(config)
        assert page.markdown is not None

        with lock:
            # Run `page_markdown` plugin events.
            page.markdown = config.plugins.on_page_markdown(
                page.markdown, page=page, config=config, files=files
            )

        page.render(config, files)
        assert page.content is not None

        with lock:
            # Run `page_content` plugin events.
            page.content = config.plugins.on_page_content(
                page.content, page=page, config=config, files=files
            )

        # Parse search entries here — not in on_page_context. This runs in
        # parallel without the global plugin lock (page-local data plus
        # atomic appends only); on_page_context runs serialized under the
        # lock during _build_page, where 16M+ HTMLParser calls stall every
        # render worker. on_page_context skips pages already indexed here.
        from docsforge.core.search import SearchPlugin

        for plugin in config.plugins.values():
            if isinstance(plugin, SearchPlugin):
                plugin.index_page_entries(page)
    except Exception as e:
        message = f"Error reading page '{page.file.src_uri}':"
        # Prevent duplicated the error message because it will be printed immediately afterwards.
        if not isinstance(e, BuildError):
            message += f" {e}"
        log.error(message)
        raise
    finally:
        with lock:
            config._current_page = None


def _build_page(
    page: Page,
    config: DocsForgeConfig,
    doc_files: Sequence[File],
    nav: Navigation,
    env: jinja2.Environment,
    dirty: bool = True,
    excluded: bool = False,
    _page_lock: threading.RLock | None = None,
) -> None:
    """Pass a Page to theme template and write output to site_dir.

    Only shared-state work runs under the lock (``page.active`` toggling,
    ``config._current_page`` for plugin hooks, ``get_context`` git-meta
    writes, and plugin hooks). ``_current_page`` is (re-)set inside each
    locked block and only cleared when still ours, so a concurrent build
    cannot observe or clear another page. ``env.get_template`` is
    thread-safe and ``template.render``/``write_file`` are thread-local,
    so they run outside the lock for real concurrency.

    Template ``active`` reads are isolated per thread instead: the render
    marker (``structure.set_rendering_page``) makes ``active`` report only
    this page and its ancestors, so concurrent renders never bake each
    other's highlights into the output.
    """
    lock = _page_lock or _default_page_lock  # Always have a lock

    # Thread-local render marker (see structure.set_rendering_page): parallel
    # builds share one nav tree, so `active` reads during this render must
    # reflect only this page — never a sibling rendering concurrently.
    prev_rendering = set_rendering_page(page)
    try:
        with lock:
            page.active = True
            config._current_page = page
            log.debug(f"Building page {page.file.src_uri}")

            context = get_context(nav, doc_files, config, page)

            # Run `page_context` plugin events.
            context = config.plugins.on_page_context(context, page=page, config=config, nav=nav)

        # Allow 'template:' override in md source files.
        # Jinja Environment.get_template is thread-safe; no locking needed.
        template = env.get_template(page.meta.get("template", "main.html"))

        if excluded:
            page.content = (
                '<div class="docsforge-draft-marker" title="This page will not be included into the built site.">'
                'DRAFT'
                '</div>' + (page.content or "")
            )

        # Render the template.
        output = template.render(context)

        with lock:
            # Re-assert current page: another build may have overwritten the
            # shared pointer while we rendered without the lock.
            config._current_page = page
            # Run `post_page` plugin events.
            output = config.plugins.on_post_page(output, page=page, config=config)

        # Write the output file.
        if output.strip():
            utils.write_file(
                output.encode("utf-8", errors="xmlcharrefreplace"), page.file.abs_dest_path
            )
        else:
            log.info(f"Page skipped: '{page.file.src_uri}'. Generated empty output.")

    except Exception as e:
        message = f"Error building page '{page.file.src_uri}':"
        # Prevent duplicated the error message because it will be printed immediately afterwards.
        if not isinstance(e, BuildError):
            message += f" {e}"
        log.error(message)
        # Strict builds abort here; non-strict ones skip this page in place
        # (nothing is written for it) and carry on with the others. Deliberate
        # behaviour change gap: an in-place skip returns normally, so the write
        # phase counts the page as processed and caches it — pre-existing, and
        # pinned by a test that expects built_any=True for such a page. Render
        # and dependency failures do not take this path: _populate_page raises,
        # so those pages are marked failed, never written and never cached.
        if config.strict:
            raise
        return
    finally:
        with lock:
            # Deactivate page (sibling-aware: parent stays active while a
            # concurrent build in the same section is still rendering).
            page.active = False
            if config._current_page is page:
                config._current_page = None
        restore_rendering_page(prev_rendering)


def _prepare_build(
    config: DocsForgeConfig,
    planner: BuildPlanner,
    config_path: Path,
    theme_sig: str,
    serve_url: str | None,
) -> tuple[DocsForgeConfig, utils.CountHandler, Callable[[InclusionLevel], bool]]:
    """Initialize cache and run pre-build plugin events."""
    needs_full_rebuild = planner.should_full_rebuild(config_path, docsforge.__version__, theme_sig)
    if needs_full_rebuild:
        planner.invalidate()

    warning_counter = utils.CountHandler()
    warning_counter.setLevel(logging.WARNING)
    if config.strict:
        logging.getLogger("docsforge").addHandler(warning_counter)

    inclusion = InclusionLevel.is_in_serve if serve_url else InclusionLevel.is_included

    # Run `config` plugin events.
    config = config.plugins.on_config(config)

    # Ensure mermaid fence config is present in markdown extensions.
    # This is done once per build instead of per-page for efficiency.
    # Work on a deep copy so the original config object is not mutated in place.
    if "pymdownx.superfences" in config["markdown_extensions"]:
        import pymdownx.superfences as superfences_mod
        mdx_configs = copy.deepcopy(config.get("mdx_configs") or {})
        config["mdx_configs"] = mdx_configs
        sf_cfg = mdx_configs.setdefault("pymdownx.superfences", {})
        custom_fences = sf_cfg.setdefault("custom_fences", [])
        if not any(f.get("name") == "mermaid" for f in custom_fences):
            custom_fences.append({
                "name": "mermaid",
                "class": "mermaid",
                "format": superfences_mod.fence_code_format,
            })

    # Run `pre_build` plugin events.
    config.plugins.on_pre_build(config=config)

    if not serve_url:
        log.info(f"Building documentation to directory: {config.site_dir}")

    return config, warning_counter, inclusion


def _get_i18n_plugin(config: DocsForgeConfig):
    """Return the configured i18n plugin, if any (both entry-point names)."""
    plugins = getattr(config, "plugins", None)
    if not plugins:
        return None
    for key in ("material/i18n", "i18n"):
        plugin = plugins.get(key) if hasattr(plugins, "get") else None
        if plugin is not None:
            return plugin
    return None


def _read_nav_source(page: Page, config: DocsForgeConfig) -> None:
    """Read one page's source for its nav title, never silently failing.

    A page whose source cannot be read must not abort the build here — it will
    fail loudly (or be skipped, depending on `strict`) in the render stage.
    But the failure must be *reported*: swallowing it silently left the page's
    title as None, which made `nav_sig` depend on which pages happened to be
    readable and could force a spurious full rebuild.
    """
    if getattr(page, "markdown", None) is not None:
        return
    try:
        page.read_source(config)
    except Exception as e:
        message = f"Could not read source of '{page.file.src_uri}' for the navigation title:"
        if not isinstance(e, BuildError):
            message += f" {e}"
        log.warning(message)


def _apply_cached_title(page: Page, cached_titles: dict[str, str] | None) -> None:
    """Seed ``_title_from_render`` from the last build's rendered title.

    ``Page.title`` prefers ``_title_from_render``, which only ``Page.render()``
    sets. An incremental build renders just the dirty pages, so without this
    every other page falls back to a naive ``# `` scan or its filename — and a
    rebuilt page then labels its siblings wrongly while untouched pages keep
    the right label. A dirty page overwrites this value when it renders, so the
    cache can only ever supply the label the last render produced.

    Frontmatter ``title`` still wins: ``Page.title`` checks ``meta['title']``
    before ``_title_from_render``, so an edited frontmatter title takes effect
    from the freshly read source.
    """
    if not cached_titles:
        return
    cached = cached_titles.get(page.file.src_uri)
    if cached and page._title_from_render is None:
        page._title_from_render = cached


def _ensure_nav_titles(
    nav: Navigation,
    config: DocsForgeConfig,
    cached_titles: dict[str, str] | None = None,
) -> None:
    """Load Markdown source titles for every page in the navigation.

    Navigation titles are not available until a page's source has been read.
    Reading them here is much cheaper than a full render and lets the nav
    signature detect title changes on incremental builds.

    ``cached_titles`` restores the authoritative label for pages this build will
    not render — see `_apply_cached_title`.
    """
    for page in nav.pages:
        _read_nav_source(page, config)
        _apply_cached_title(page, cached_titles)

    # i18n: locale navs hold distinct Page objects (e.g. setup/index.zh.md)
    # whose frontmatter (title, meta.icon for tabs/sidebar) is otherwise only
    # loaded when that file is dirty. On incremental rebuilds skipped locale
    # index pages kept meta={} so translated tabs lost their icons. Preload
    # them here just like the default nav.
    i18n_plugin = _get_i18n_plugin(config)
    locale_navs = getattr(i18n_plugin, "_locale_navs", None) or {}
    for locale_nav in locale_navs.values():
        if locale_nav is nav:
            continue
        for page in getattr(locale_nav, "pages", []):
            _read_nav_source(page, config)


def _nav_signature(nav: Navigation, config: DocsForgeConfig) -> str:
    """Return a deterministic hash of the navigation structure.

    Any change to page order, titles, section structure, i18n titles, or the
    effective site URL invalidates the signature and forces all pages to be
    re-rendered so navigation/previous/next links stay consistent.

    The *full* site_url (not just its path) is included: ``docsforge build``
    and ``docsforge serve`` differ only in origin (production vs localhost) but
    share the same path, so a path-only signature would let serve reuse stale
    production output (wrong canonical/absolute URLs). Including the full URL
    makes the first serve build re-render everything.
    """

    def _sorted_dict(d: dict) -> dict:
        return {k: d[k] for k in sorted(d)}

    def _serialize(item):
        if getattr(item, "is_page", False):
            meta = getattr(item, "meta", None)
            icon = None
            try:
                if isinstance(meta, dict):
                    icon = meta.get("icon")
            except Exception:
                icon = None
            return {
                "type": "page",
                "src_uri": item.file.src_uri,
                "url": item.url,
                "title": item.title,
                "is_homepage": item.is_homepage,
                "i18n_titles": _sorted_dict(item.i18n_titles),
                "icon": icon,
            }
        if getattr(item, "is_section", False):
            return {
                "type": "section",
                "title": item.title,
                "i18n_titles": _sorted_dict(item.i18n_titles),
                "children": [_serialize(c) for c in item.children],
            }
        if getattr(item, "is_link", False):
            return {
                "type": "link",
                "title": item.title,
                "url": item.url,
                "i18n_titles": _sorted_dict(item.i18n_titles),
            }
        return {}

    data = {
        "site_url": config.site_url or "",
        "items": [_serialize(i) for i in nav.items],
    }
    # i18n: locale nav titles/icons must also invalidate the signature.
    # Otherwise a zh-only frontmatter title/icon change rebuilds just that
    # file while other zh pages keep stale nav text/icons.
    i18n_plugin = _get_i18n_plugin(config)
    locale_navs = getattr(i18n_plugin, "_locale_navs", None) or {}
    others = {locale: nav_ for locale, nav_ in locale_navs.items() if nav_ is not nav}
    if others:
        data["i18n"] = {
            str(locale): [_serialize(i) for i in locale_nav.items]
            for locale, locale_nav in sorted(others.items(), key=lambda kv: str(kv[0]))
        }
    hasher = hashlib.sha256()
    hasher.update(json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    return hasher.hexdigest()[:32]


def _collect_files_and_nav(
    config: DocsForgeConfig,
    planner: BuildPlanner,
    inclusion: Callable[[InclusionLevel], bool],
) -> tuple[Files, jinja2.Environment, Navigation, list[File], bool, bool]:
    """Gather files from docs_dir and theme, cleanup orphans, build navigation."""
    # Compile TikZ diagrams BEFORE scanning files so the build discovers the SVGs.
    from docsforge import tikz
    tikz.compile_tikz_files(config, output_to_docs=True)

    files = get_files(config)
    env = config.theme.get_env()
    files.add_files_from_theme(env, config)

    # Run `files` plugin events.
    files = config.plugins.on_files(files, config=config)
    # If plugins have added files but haven't set their inclusion level, calculate it again.
    set_exclusions(files, config)

    # Remove orphaned output files (pages deleted from source). Orphans can
    # only appear when a source is removed, so skip the site_dir walk when
    # the source set is unchanged or only grew since the last build.
    docs_dir = Path(config.docs_dir)
    site_dir = Path(config.site_dir)
    current_sources = {f.src_uri for f in files}
    prev_sources = set(planner.cache.get_sources())
    sources_changed = prev_sources != current_sources
    if planner.should_scan_orphans(current_sources):
        known_dest_uris = {f.dest_uri for f in files}
        orphaned = planner.find_orphaned_outputs(docs_dir, site_dir, known_dest_uris)
        for f in orphaned:
            log.debug(f"Removing orphaned output: {f}")
            _remove_orphaned_output(f, site_dir)
    planner.update_sources(current_sources)

    nav = get_navigation(files, config)

    # Run `nav` plugin events.
    nav = config.plugins.on_nav(nav, config=config, files=files)

    # Detect navigation/global changes that require every page to be re-rendered.
    # Titles must be loaded first so the signature reflects page title changes.
    # `planner.titles` holds the labels the last build actually rendered, so
    # pages this build skips keep their authoritative title instead of falling
    # back to the naive `# ` scan.
    _ensure_nav_titles(nav, config, planner.titles)
    nav_sig = _nav_signature(nav, config)
    nav_changed = planner.nav_sig != nav_sig
    if nav_changed:
        planner.nav_sig = nav_sig
        log.debug("Navigation signature changed; all pages will be re-rendered")

    log.debug("Reading markdown pages.")
    all_doc_files = list(files.documentation_pages(inclusion=inclusion))

    return files, env, nav, all_doc_files, sources_changed, nav_changed


def _remove_orphaned_output(path: Path, site_dir: Path | None = None) -> None:
    """Remove an orphaned output file, logging a warning on transient errors.

    When `site_dir` is given, directories left empty by the removal are pruned
    too (never `site_dir` itself) — otherwise every deleted page/asset leaves an
    empty directory behind in the built site.
    """
    try:
        path.unlink()
    except OSError as exc:
        log.warning(f"Could not remove orphaned output {path}: {exc}")
        return
    if site_dir is not None:
        BuildPlanner.prune_empty_dirs(site_dir, path)


@dataclass
class _PagePlan:
    """One documentation page's rebuild decision, shared by both build stages.

    The dependency set is computed exactly once, here, because that is the only
    point where it can be: `pymdownx.snippets` consumes the ``--8<--`` markers
    during `md.convert()`, so the marker text only exists in `page.markdown`
    right after `read_source`. Re-deriving the set later (the write stage used
    to re-read the file from disk) produced a *different* set whenever a plugin
    rewrote the markdown in `on_page_markdown`, and every such mismatch made
    `update_cache` prune deps the freshness check had just counted on — which
    rebuilt every snippet-include page on every build.
    """

    page: Page
    # None for generated files (`File.generated`, a plugin's temp source): they
    # have nothing on disk to stat or hash, so they are always rebuilt.
    source_path: Path | None
    output_path: Path
    deps: list[str]
    rebuild: bool
    # Set when any per-page stage failed for this page — `_populate_page`
    # (render) or `_build_page` (template + write). A failed page is never
    # written and never cached, so a non-strict build neither publishes broken
    # output nor remembers the failure as "up to date" (the next build retries
    # it). Named for the stage that introduced the flag; both stages set it.
    populate_failed: bool = False


def _page_failure(config: DocsForgeConfig, plan: _PagePlan, exc: BaseException) -> None:
    """Apply the build's single per-page error policy.

    Every per-page stage routes its failures here, so strict and non-strict
    cannot diverge between rendering and writing:

    - strict: re-raise, aborting the build on the first bad page. The error was
      already logged where it happened.
    - non-strict: mark the plan failed and carry on with the other pages. The
      write phase skips a failed plan, so nothing is published for it.
    """
    if config.strict:
        raise exc.with_traceback(exc.__traceback__)
    plan.populate_failed = True


def _page_deps(page: Page, config: DocsForgeConfig, files: Files) -> list[str]:
    """Return the full dependency list for one page (snippets + plugin deps)."""
    abs_src = page.file.abs_src_path
    source_path = Path(abs_src) if abs_src else Path(config.docs_dir) / page.file.src_uri
    # Snippet includes are file dependencies. `base_paths` must match the set
    # `update_cache` records, otherwise the freshness check and the cache
    # disagree and the page rebuilds forever.
    file_deps = DependencyTracker.get_file_deps(
        source_path,
        page.markdown,
        base_paths=[Path(config.docs_dir)],
    )
    # Let plugins declare render dependencies (e.g. a blog entrypoint whose
    # listing derives from every post). An added/removed dependency forces a
    # re-render even when the page's own source is unchanged.
    return config.plugins.on_page_deps(file_deps, page=page, files=files, config=config)


def _plan_pages(
    config: DocsForgeConfig,
    files: Files,
    planner: BuildPlanner,
    all_doc_files: list[File],
    force_all: bool = False,
) -> list[_PagePlan]:
    """Decide which pages need rebuilding, once, for both build stages."""
    plans: list[_PagePlan] = []
    for file in all_doc_files:
        assert file.page is not None
        abs_src = file.abs_src_path
        source_path = Path(abs_src) if abs_src else None
        output_path = Path(file.abs_dest_path)
        deps = _page_deps(file.page, config, files)

        if force_all or source_path is None:
            # No source on disk (generated file) means no mtime/hash to
            # compare: treat it as always fresh rather than crashing on
            # `Path(None)`.
            rebuild = True
        else:
            rebuild = planner.should_rebuild(source_path, output_path) or planner.deps_changed(
                source_path, deps
            )
        if not rebuild:
            log.debug(f"Skipping unchanged page: {file.src_uri}")
        plans.append(_PagePlan(file.page, source_path, output_path, deps, rebuild))
    return plans


def _ensure_page_objects(
    config: DocsForgeConfig,
    all_doc_files: list[File],
    serve_url: str | None,
) -> None:
    """Give every documentation file a `Page` and report excluded drafts.

    Files outside the nav get a Page too (they are still rendered and written,
    just unlisted); a serve build reports the drafts it previews but a real
    build would drop.
    """
    excluded: list[str] = []
    for file in all_doc_files:
        log.debug(f"Reading: {file.src_uri}")
        if file.page is None and file.inclusion.is_not_in_nav():
            if serve_url and file.inclusion.is_excluded():
                excluded.append(urljoin(serve_url, file.url))
            Page(None, file, config)
        assert file.page is not None

    if excluded:
        log.info(
            "The following pages are being built only for the preview "
            "but will be excluded from `docsforge build` per `draft_docs` config:\n  - %s",
            "\n  - ".join(excluded),
        )


def _populate_changed_pages(
    config: DocsForgeConfig,
    files: Files,
    planner: BuildPlanner,
    all_doc_files: list[File],
    inclusion: Callable[[InclusionLevel], bool],
    serve_url: str | None,
    force_all: bool = False,
    plans: list[_PagePlan] | None = None,
) -> list[_PagePlan]:
    """Render phase of the page pipeline: plan, then render Markdown in parallel.

    Returns the plans annotated with which pages failed; the write phase
    (_write_pages) consumes the same list, so both agree on the rebuild set and
    on the dependency set recorded in the cache. Failures go through the single
    `_page_failure` policy (strict: abort; non-strict: mark and continue).

    The heavy work (read_source + render/markdown.convert) runs in the pool: it
    is thread-safe (per-thread Markdown instance) and only plugin events are
    serialized via plugin_lock.
    """
    _ensure_page_objects(config, all_doc_files, serve_url)

    if plans is None:
        plans = _plan_pages(config, files, planner, all_doc_files, force_all=force_all)
    to_render = [plan for plan in plans if plan.rebuild]
    if not to_render:
        return plans

    plugin_lock = threading.RLock()
    max_workers = max(1, config.concurrency)
    log.info(f"Rendering {len(to_render)} pages...")
    ex = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
    failures = 0
    try:
        futures = [
            (ex.submit(_populate_page, plan.page, config, files, True, plugin_lock), plan)
            for plan in to_render
        ]
        for future, plan in futures:
            try:
                _wait_future(future)
            except Exception as e:
                # Error already logged in _populate_page. In strict mode
                # _page_failure re-raises and the shutdown below cancels the
                # queued work; otherwise the page is marked and skipped.
                failures += 1
                _page_failure(config, plan, e)
    except BaseException:
        # Interrupted (e.g. Ctrl-C during serve): don't join running workers,
        # just cancel what's queued so shutdown is prompt. Pages keep no
        # partial cache state, so the next build retries.
        ex.shutdown(wait=False, cancel_futures=True)
        raise
    else:
        ex.shutdown(wait=True)

    if failures:
        log.warning(f"Skipped {failures} page(s) that failed to render")
    return plans


def _record_rendered_title(planner: BuildPlanner, page: Page) -> None:
    """Persist the nav title this page's render produced.

    Stored so the next incremental build can label pages it skips. Only
    ``_title_from_render`` is recorded — the value ``Page.render()`` derived
    from the first heading. A page with no heading leaves it ``None``, and the
    key is dropped rather than cached, so the fallback still applies next time
    (nothing authoritative was learned).
    """
    src_uri = page.file.src_uri
    if page._title_from_render:
        planner.titles[src_uri] = page._title_from_render
    else:
        planner.titles.pop(src_uri, None)


def _serialize_validation(page: Page) -> dict:
    """Serialize a page's link/anchor validation data for the build cache."""
    return {
        "warnings": [[level, msg] for level, msg in page.link_warnings],
        "links": {
            to_file.src_uri: links
            for to_file, links in (page.links_to_anchors or {}).items()
        },
        "anchors": sorted(a for a in (page.present_anchor_ids or []) if a is not None),
    }


def _restore_validation(page: Page, data: dict | None, files: Files) -> None:
    """Restore a page's link/anchor data from the build cache (not re-rendered).

    Lets the validation pass report the page's problems on incremental builds
    exactly like a fresh build would, without re-rendering it.
    """
    if not data:
        return
    page.link_warnings = [tuple(w) for w in data.get("warnings", [])]
    page.present_anchor_ids = set(data.get("anchors", []))
    links: dict[File, dict[str, str]] = {}
    for src_uri, anchors in (data.get("links") or {}).items():
        to_file = files.get_file_from_path(src_uri)
        if to_file is not None:
            links[to_file] = anchors
    page.links_to_anchors = links or None


def _write_pages(
    config: DocsForgeConfig,
    files: Files,
    nav: Navigation,
    env: jinja2.Environment,
    planner: BuildPlanner,
    all_doc_files: list[File],
    force_all: bool = False,
    plans: list[_PagePlan] | None = None,
) -> tuple[bool, set[str]]:
    """Write phase: template, write and cache every successfully rendered page.

    Serial on purpose: writes and cache mutations must stay ordered, and only
    one page may be ``active`` at a time (the sidebar-highlight race). Renders
    already happened in parallel in the render phase.

    Pages no longer needing a rebuild, and pages that failed to render, are
    skipped together: a failed page has missing or stale markdown, so writing
    it would publish broken output. The cache is updated only for pages that
    were actually written — otherwise the next run would treat a broken page as
    up to date and silently keep its old output.

    Returns ``(built_any, built_sources)``: whether any page was written, and
    the set of source paths that were rebuilt.
    """
    if plans is None:
        plans = _plan_pages(config, files, planner, all_doc_files, force_all=force_all)
    pages_to_build = [plan for plan in plans if plan.rebuild and not plan.populate_failed]

    built_any = False
    built_sources: set[str] = set()
    if not pages_to_build:
        return built_any, built_sources

    # Warm git revision dates concurrently (S1): every page render below calls
    # get_git_page_info, whose history walks cost ~100ms each. Prefetching
    # fills the same cache through the same per-file git commands, so output is
    # identical — the renders just stop waiting on serial walks. Generated
    # files have no source path to warm.
    prefetch_git_page_info(
        [plan.page.file.abs_src_path for plan in pages_to_build if plan.page.file.abs_src_path]
    )
    page_lock = threading.RLock()
    log.info(f"Writing {len(pages_to_build)} pages...")
    failures = 0

    # Serial on purpose: writes and cache mutations must stay ordered, and the
    # per-page git revision dates are populated during get_context via a shared
    # prefetch cache — parallel writes raced that cache and dropped the date
    # block from some locale pages. The thread-local nav_is_active() keeps the
    # sidebar correct, but git-meta and plugin hook ordering require serial.
    for plan in pages_to_build:
        try:
            _build_page(
                plan.page,
                config,
                all_doc_files,
                nav,
                env,
                True,
                plan.page.file.inclusion.is_excluded(),
                page_lock,
            )
        except Exception as e:
            # Error already logged in _build_page. Strict mode re-raises and
            # aborts; otherwise the page is skipped, uncached, and retried next
            # build. Same policy function as the render phase.
            failures += 1
            _page_failure(config, plan, e)
            continue

        # Cache only what was written. Reuse the deps computed once while
        # planning: same raw markdown (snippet markers are consumed during
        # md.convert(), so page.content cannot be used), same plugin-declared
        # extras, hence the same set the freshness check compared against.
        if plan.source_path is not None:
            planner.update_cache(plan.source_path, plan.output_path, plan.deps)
        # Persist link/anchor validation data so skipped pages can be
        # re-validated on later incremental builds.
        planner.validation[plan.page.file.src_uri] = _serialize_validation(plan.page)
        # Persist the rendered nav title so pages skipped by the *next*
        # incremental build still label the sidebar correctly. Only the value
        # `Page.render()` derived is stored: frontmatter titles are re-read from
        # source every build and win over this cache anyway.
        _record_rendered_title(planner, plan.page)
        built_sources.add(plan.page.file.src_uri)
        built_any = True

    if failures:
        log.warning(f"Skipped {failures} page(s) that failed to build")
    return built_any, built_sources


def _write_static_outputs(
    config: DocsForgeConfig,
    files: Files,
    nav: Navigation,
    env: jinja2.Environment,
    inclusion: Callable[[InclusionLevel], bool],
) -> jinja2.Environment:
    """Run `env` plugins, copy static assets, build theme/extra templates."""
    # Run `env` plugin events.
    env = config.plugins.on_env(env, config=config, files=files)

    # Start writing files to site_dir now that all data is gathered. Note that order matters. Files
    # with lower precedence get written first so that files with higher precedence can overwrite them.
    log.debug("Copying static assets.")
    files.copy_static_files(dirty=True, inclusion=inclusion)

    for template in config.theme.static_templates:
        _build_theme_template(template, env, files, config, nav)

    # Render per-locale static templates (e.g. 404.zh.html) so error pages show
    # the correct language when the i18n plugin is configured.
    _build_locale_static_templates(env, files, config, nav)

    for template in config.extra_templates:
        _build_extra_template(template, env, files, config, nav)

    return env


def _build_page_pipeline(
    config: DocsForgeConfig,
    files: Files,
    nav: Navigation,
    env: jinja2.Environment,
    planner: BuildPlanner,
    all_doc_files: list[File],
    inclusion: Callable[[InclusionLevel], bool],
    serve_url: str | None = None,
    force_all: bool = False,
) -> tuple[bool, set[str]]:
    """The single per-page pipeline: plan -> render (parallel) -> write -> cache.

    One error policy for the whole pipeline (`_page_failure`): strict raises on
    the first failure, non-strict logs it, marks the page failed and continues;
    a failed page is never written and never cached.

    The two phases are kept as two drain points rather than interleaved on
    purpose: renders fully complete before any write starts, which is exactly
    the isolation the previous split imposed. Interleaving would let a
    `_build_page` hook (holding ``page_lock``) run concurrently with a
    `_populate_page` hook (holding ``plugin_lock``) — different locks, so no
    mutual exclusion, and plugins may assume the stages never overlap.
    """
    _ensure_page_objects(config, all_doc_files, serve_url)
    plans = _plan_pages(config, files, planner, all_doc_files, force_all=force_all)

    # Render phase: parallel, and it annotates the shared plans with failures.
    _populate_changed_pages(config, files, planner, all_doc_files, inclusion, serve_url, plans=plans)

    env = _write_static_outputs(config, files, nav, env, inclusion)
    return _write_pages(config, files, nav, env, planner, all_doc_files, plans=plans)


def _write_outputs(
    config: DocsForgeConfig,
    files: Files,
    nav: Navigation,
    env: jinja2.Environment,
    planner: BuildPlanner,
    all_doc_files: list[File],
    inclusion: Callable[[InclusionLevel], bool],
    force_all: bool = False,
    plans: list[_PagePlan] | None = None,
) -> tuple[bool, set[str]]:
    """Static assets + the write phase, for a plan list produced elsewhere.

    Kept as a separate entry point for callers that supply already-rendered
    pages; `_build_page_pipeline` is the path a real build takes. Shares the
    write implementation and error policy with it — nothing is duplicated.

    Returns ``(built_any, built_sources)``: whether any page was written, and
    the set of source paths that were rebuilt.
    """
    env = _write_static_outputs(config, files, nav, env, inclusion)
    return _write_pages(
        config, files, nav, env, planner, all_doc_files, force_all=force_all, plans=plans
    )


def _restore_missing_static_outputs(files: Files) -> int:
    """Re-copy expected static outputs absent from the site directory.

    Safety net running after asset optimization: if a produced file (theme
    asset, downloaded external asset, extra file) went missing from the
    site — hand-deleted, lost to a crash, or removed by an older optimizer
    that didn't track its reference kind — copy it back from its source when
    the source still exists. Returns the number of files restored.

    Deliberately narrow so it can never undo intentional work:
    - Documentation pages are skipped (a missing page output triggers a
      rebuild via ``should_rebuild``, not a copy — copying the .md source
      would be wrong).
    - ``OPTIMIZER_MANAGED_DIRS`` are skipped (deletions there are the
      optimizer's deliberate pruning of unreferenced files).
    - Files whose source is gone (failed downloads, in-memory-only content
      is still restored) are skipped.
    """
    restored = 0
    for file in files:
        if file.is_documentation_page():
            continue
        dest_uri = (file.dest_uri or "").replace("\\", "/")
        if any(
            dest_uri == managed or dest_uri.startswith(f"{managed}/")
            for managed in OPTIMIZER_MANAGED_DIRS
        ):
            continue
        src = file.abs_src_path
        if src is None or not os.path.isfile(src):
            continue
        try:
            dest = file.abs_dest_path
        except Exception:
            continue
        if os.path.isfile(dest):
            continue
        try:
            file.copy_file()
        except OSError as e:
            log.debug(f"Could not restore static output '{dest_uri}': {e}")
            continue
        restored += 1
    if restored:
        log.info(f"Restored {restored} static output(s) missing from the site")
    return restored


def _slug_rules_from_config(config: DocsForgeConfig) -> SlugRules:
    """Read the site's real ``toc`` extension config into canonical slug rules.

    The engine renders heading anchors with the ``toc`` extension's ``slugify``,
    so its ``separator`` and its stock-vs-custom ``slugify`` choice decide the
    ids -- writing the built-in defaults would be wrong for any site that
    overrides either. A custom callable is not derivable from parameters, so
    those rules are flagged ``predictable=False`` and the Studio falls back to
    its own implementation instead of trusting ``separator``/``unicode``.

    ``mdx_configs`` is populated from ``markdown_extensions``, and the ``toc``
    builtin is always registered, so the empty-config path yields the stock
    rules.
    """
    from markdown.extensions.toc import slugify as toc_slugify
    from markdown.extensions.toc import slugify_unicode as toc_slugify_unicode

    toc_cfg = (config.get("mdx_configs") or {}).get("toc") or {}
    slugify_fn = toc_cfg.get("slugify") or toc_slugify
    predictable = slugify_fn in (toc_slugify, toc_slugify_unicode)
    return compute_rules(
        separator=toc_cfg.get("separator") or "-",
        # Only the stock unicode variant keeps non-ASCII word characters; an
        # unknown callable is unpredictable, so ``unicode`` is moot there.
        unicode=slugify_fn is toc_slugify_unicode,
        predictable=predictable,
    )


def _finalize_build(
    config: DocsForgeConfig,
    files: Files,
    nav: Navigation,
    planner: BuildPlanner,
    warning_counter: utils.CountHandler,
    built_any: bool,
    built_sources: set[str],
    sources_changed: bool,
    nav_changed: bool,
    config_path: Path,
    theme_sig: str,
    start: float,
) -> None:
    """Generate PWA assets, validate links, run post-build events, and save cache."""
    # Restore link/anchor data for pages not re-rendered this build, so the
    # validation pass below reports every page's problems on EVERY build, not
    # just the first one (a broken cross-link used to surface only when the
    # linking page itself was rebuilt).
    for file in files.documentation_pages():
        page = file.page
        if page is None or file.src_uri in built_sources:
            continue
        _restore_validation(page, planner.validation.get(file.src_uri), files)

    # Re-emit collected link warnings (fresh from render, or restored above)
    # and validate anchors — always, regardless of what changed this build.
    # validate_anchor_links appends to page.link_warnings, so it must run
    # BEFORE the emission loop below, or the fresh anchor problems would be
    # logged only on the next build (and lost entirely for unbuilt pages,
    # which are never re-serialized).
    log_level = config.validation.links.anchors
    for file in files.documentation_pages():
        page = file.page
        assert page is not None
        page.validate_anchor_links(files=files, log_level=log_level)

    # Re-serialize validation for ALL pages now that anchor warnings have been
    # appended — the serialization inside _write_outputs happened before the
    # anchor pass, and restored pages only carry cache data, so without this
    # the anchor problems would never reach validation.json (and thus never
    # reach the VS Code extension).
    for file in files.documentation_pages():
        page = file.page
        if page is not None:
            planner.validation[file.src_uri] = _serialize_validation(page)

    for file in files.documentation_pages():
        page = file.page
        for level, msg in page.link_warnings:
            log.log(level, msg)

    # Run `post_build` plugin events.
    config.plugins.on_post_build(config=config)

    # Optimize static assets: remove unused files, source maps, old font
    # formats. Source-map stripping is incremental (skips unchanged JS files
    # using cached mtime+size). The expensive reference scan for unused assets
    # is skipped when nothing changed.
    optimize_assets(
        config.site_dir,
        built_any=built_any,
        sources_changed=sources_changed,
        cache_dir=planner.cache.cache_dir,
        site_url=config.site_url or "",
    )

    # Safety net after optimization: re-copy expected static outputs that are
    # absent from the site but still have a source (hand-deleted, crash-lost,
    # or pruned by an older optimizer revision). Per-producer restore already
    # covers pages (rebuild on missing output), templates/manifests (write if
    # missing), and social cards (cache copy in on_post_build); this covers
    # everything else carried in the Files collection.
    _restore_missing_static_outputs(files)

    # Generate PWA manifest + pre-cache list + service worker build hash.
    # Runs AFTER optimize_assets (so the manifest reflects the final file
    # set) and on EVERY build — static assets (CSS, icons) can change without
    # any page/source/nav change, and the service worker needs the updated
    # hashes to re-sync them. The manifest version is deterministic (hash of
    # file hashes), so an unchanged build produces the same version and causes
    # no service-worker churn.
    _generate_pwa_manifest_and_precache(config, files, nav, planner)

    # Write the canonical heading-slug rules next to validation.json so the
    # Studio extension reproduces the engine's anchor ids instead of relying
    # on a hand-maintained second implementation (they drifted before).
    # Guarded: unit tests drive _finalize_build with a Mock planner whose
    # cache_dir is not a real path.
    cache_dir = getattr(planner.cache, "cache_dir", None)
    if isinstance(cache_dir, (str, os.PathLike)):
        write_rules(Path(cache_dir) / "slug-rules.json", _slug_rules_from_config(config))

    # Save cache state
    config_hash = FileHasher.hash_file(config_path) if config_path.exists() else ""
    # Recompute the nav signature now that every rendered page carries its
    # authoritative title. `_collect_files_and_nav` computed it *before* the
    # render phase, when a page that this build renders still only had the
    # naive `# `-scan fallback (or, on a cold build, the filename). Saving that
    # pre-render signature made the NEXT build compute a different one from the
    # now-correct titles and force a spurious full re-render — so every cold
    # build was followed by one wasted full rebuild.
    planner.nav_sig = _nav_signature(nav, config)
    planner.save(
        config_hash=config_hash,
        pkg_version=docsforge.__version__,
        theme_sig=theme_sig,
        nav_sig=planner.nav_sig,
    )

    # Save cache after successful build (only if not in strict mode with errors)
    if counts := warning_counter.get_counts():
        msg = ", ".join(f"{v} {k.lower()}s" for k, v in counts)
        raise Abort(f"Aborted with {msg} in strict mode!")

    # Run `build_done` plugin events — after EVERYTHING (validation,
    # post-build plugins, asset optimization, PWA manifest + service worker
    # generation, cache save) so hooks can inspect or modify the final build
    # output. Skipped when the build is aborted in strict mode.
    config.plugins.on_build_done(config=config)

    log.info(f"Documentation built in {time.monotonic() - start:.2f} seconds")


def build(
    config: DocsForgeConfig,
    *,
    serve_url: str | None = None,
    dirty: bool = True,
    progress: bool | None = None,
) -> None:
    """Perform a site build — always incremental, always complete."""
    logger = logging.getLogger("docsforge")

    cache = CacheManager()
    hasher = FileHasher()
    planner = BuildPlanner(cache, hasher)
    config_path = Path(config.config_file_path) if config.config_file_path else Path("docsforge.yml")
    theme_sig = planner.theme_signature(config.theme.dirs)

    warning_counter: utils.CountHandler | None = None
    try:
        start = time.monotonic()
        config, warning_counter, inclusion = _prepare_build(
            config, planner, config_path, theme_sig, serve_url
        )
        files, env, nav, all_doc_files, sources_changed, nav_changed = _collect_files_and_nav(
            config, planner, inclusion
        )
        # One pipeline for the page work: plan -> render (parallel) -> write
        # (serial) -> cache. The dependency set can only be derived from the raw
        # markdown, so it is computed once while planning and threaded through,
        # keeping the freshness check and the cache update in exact agreement.
        # One error policy covers both phases (see `_page_failure`).
        built_any, built_sources = _build_page_pipeline(
            config, files, nav, env, planner, all_doc_files, inclusion,
            serve_url=serve_url, force_all=nav_changed,
        )
        _finalize_build(
            config, files, nav, planner, warning_counter,
            built_any, built_sources, sources_changed, nav_changed, config_path, theme_sig, start,
        )

    except Exception as e:
        # Run `build_error` plugin events.
        config.plugins.on_build_error(error=e)
        if isinstance(e, BuildError):
            log.error(str(e))
            raise Abort("Aborted with a BuildError!")
        raise

    finally:
        if warning_counter is not None:
            logger.removeHandler(warning_counter)


def _parse_svg_length(value: str) -> int | None:
    """Extract a numeric pixel length from an SVG width/height attribute."""
    value = value.strip()
    match = re.match(r"^([0-9]*\.?[0-9]+)", value)
    if match:
        try:
            return int(float(match.group(1)))
        except ValueError:
            return None
    return None


def _svg_dimensions(data: bytes) -> tuple[int | None, int | None]:
    """Return (width, height) for an SVG, derived from width/height/viewBox."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None, None
    svg_match = re.search(r"<svg[^>]*>", text, re.DOTALL | re.IGNORECASE)
    if not svg_match:
        return None, None
    svg_tag = svg_match.group(0)

    width_match = re.search(r'\bwidth=["\']([^"\']+)', svg_tag, re.IGNORECASE)
    height_match = re.search(r'\bheight=["\']([^"\']+)', svg_tag, re.IGNORECASE)
    viewbox_match = re.search(r'\bviewBox=["\']([^"\']+)', svg_tag, re.IGNORECASE)

    width = _parse_svg_length(width_match.group(1)) if width_match else None
    height = _parse_svg_length(height_match.group(1)) if height_match else None

    if (width is None or height is None) and viewbox_match:
        parts = viewbox_match.group(1).split()
        if len(parts) == 4:
            try:
                vb_width = float(parts[2])
                vb_height = float(parts[3])
                if width is None:
                    width = int(vb_width)
                if height is None:
                    height = int(vb_height)
            except ValueError:
                pass

    return width, height


def _png_dimensions(data: bytes) -> tuple[int | None, int | None]:
    """Return (width, height) from a PNG IHDR chunk."""
    if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
        return None, None
    return (
        int.from_bytes(data[16:20], "big"),
        int.from_bytes(data[20:24], "big"),
    )


def _jpeg_dimensions(data: bytes) -> tuple[int | None, int | None]:
    """Return (width, height) from a JPEG SOF marker."""
    i = 0
    while i + 1 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker == 0xD8:  # SOI
            i += 2
            continue
        if marker == 0xD9:  # EOI
            break
        if 0xD0 <= marker <= 0xD7 or marker in (0x00, 0x01):
            i += 2
            continue
        # SOF markers contain dimensions.
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            if len(data) < i + 9:
                return None, None
            return (
                int.from_bytes(data[i + 7:i + 9], "big"),
                int.from_bytes(data[i + 5:i + 7], "big"),
            )
        if i + 4 > len(data):
            break
        length = struct.unpack(">H", data[i + 2:i + 4])[0]
        i += 2 + length
    return None, None


def _get_image_info(path: str) -> tuple[int | None, int | None, str | None]:
    """Return (width, height, mime_type) for an image file, using the file contents.

    Supports PNG, JPEG and SVG. Width/height may be ``None`` for formats where
    they cannot be determined without additional dependencies.
    """
    mime_type, _ = mimetypes.guess_type(path)
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError:
        return None, None, mime_type
    if not data:
        return None, None, mime_type

    lower_path = path.lower()
    if lower_path.endswith(".png") or mime_type == "image/png":
        width, height = _png_dimensions(data)
    elif lower_path.endswith((".jpg", ".jpeg")) or mime_type in ("image/jpeg", "image/jpg"):
        width, height = _jpeg_dimensions(data)
    elif lower_path.endswith(".svg") or mime_type == "image/svg+xml":
        width, height = _svg_dimensions(data)
    else:
        width, height = None, None

    return width, height, mime_type


def _generate_pwa_manifest_and_precache(
    config: DocsForgeConfig, files: Files, nav: Navigation, planner: BuildPlanner | None = None
) -> None:
    """Generate PWA manifest and inject pre-cache list into the service worker.

    After all pages are built, this function:
    1. Generates a manifest.json with site metadata and icons
    2. Collects all built HTML page URLs for pre-caching
    3. Injects the pre-cache list into the service worker template

    This enables full offline browsing of all documentation pages.
    """
    site_dir = config.site_dir

    if config.offline.mode == "none":
        # Mode 'none' eliminates the service worker and all its caching: no
        # registration, no sw.js at the site root, no cache/PWA manifest. Drop
        # the template copy of sw.js that was copied into assets so no worker
        # ships with the site at all.
        with contextlib.suppress(OSError):
            os.remove(os.path.join(site_dir, "assets", "javascripts", "sw.js"))
        log.debug("offline.mode 'none': skipping service worker and cache manifest")
        return

    # Collect all HTML page URLs for pre-caching
    precache_urls = []
    for file in files.documentation_pages():
        if file.inclusion.is_included() or file.inclusion.is_not_in_nav():
            page_url = file.url
            if page_url:
                precache_urls.append(page_url)

    # Also include static templates (404.html, sitemap.xml, etc.)
    for template in config.theme.static_templates:
        if template.endswith(".html"):
            template_url = template.replace(".html", "/")
            if template == "404.html":
                template_url = "/404.html"
            precache_urls.append(template_url)

    # Also include the home page explicitly. Page.url returns '' for the
    # homepage, but File.url uses './'; keep the explicit './' form so the
    # root page survives deduplication and is written into cache-manifest.json.
    home_url = nav.homepage.url if nav.homepage else "./"
    if home_url and home_url not in precache_urls:
        precache_urls.insert(0, home_url)

    # Convert all URLs to be relative to the SW script location
    # SW is now at <site_root>/sw.js (root of site)
    # So URLs are just relative to root
    sw_relative_urls = []
    for url in precache_urls:
        if url.startswith("/"):
            sw_relative_urls.append(url.lstrip("/"))
        elif url in ("", "./"):
            sw_relative_urls.append("./")
        else:
            # Already relative, keep as-is
            sw_relative_urls.append(url)

    # Always include cache manifest for hash-based syncing
    sw_relative_urls.append("cache-manifest.json")

    # Remove duplicates and sort for deterministic output
    sw_relative_urls = sorted({url for url in sw_relative_urls if url})

    # Inject pre-cache list and deterministic build hash into service worker.
    # The SW is placed at site root for maximum scope coverage.
    sw_source = os.path.join(site_dir, "assets", "javascripts", "sw.js")
    sw_dest = os.path.join(site_dir, "sw.js")
    if os.path.isfile(sw_source):
        try:
            with open(sw_source, encoding="utf-8") as f:
                content = f.read()

            if "__PRE_CACHE_PAGES__" in content:
                content = content.replace(
                    "__PRE_CACHE_PAGES__",
                    json.dumps(sw_relative_urls)
                )

            if "__DOCSFORGE_BASE_URL__" in content:
                # Inject the site base path so the SW works correctly when the
                # documentation is deployed under a subpath (e.g. /docs/).
                base_url_path = urlsplit(config.site_url or "/").path or "/"
                base_url_path = "/" + base_url_path.strip("/")
                if base_url_path != "/":
                    base_url_path += "/"
                content = content.replace("__DOCSFORGE_BASE_URL__", base_url_path)
                log.debug(f"Injected service worker base URL {base_url_path}")

            if "__DOCSFORGE_BUILD_HASH__" in content:
                # Deterministic hash: identical source + config + precache list
                # produces identical SW hash, so unchanged builds don't force
                # clients to reinstall the service worker.
                hasher = hashlib.sha256()
                hasher.update(content.encode("utf-8"))
                hasher.update(json.dumps(sw_relative_urls).encode("utf-8"))
                config_path = Path(config.config_file_path) if config.config_file_path else Path("docsforge.yml")
                if config_path.exists():
                    hasher.update(config_path.read_bytes())
                build_hash = hasher.hexdigest()[:12]
                content = content.replace("__DOCSFORGE_BUILD_HASH__", build_hash)
                log.debug(f"Injected deterministic build hash {build_hash} into service worker")

            _write_if_changed(sw_dest, content.encode("utf-8"))

            # Remove the template copy in assets to avoid a duplicate worker.
            try:
                os.remove(sw_source)
            except OSError as e:
                log.debug(f"Could not remove duplicate service worker template: {e}")

            log.debug(f"Injected {len(sw_relative_urls)} pages into service worker pre-cache")
        except Exception as e:
            log.warning(f"Failed to inject pre-cache list into SW: {e}")

    # Generate manifest.json
    manifest = {
        "name": config.site_name,
        "short_name": config.site_name[:12],
        "description": config.site_description or f"Documentation for {config.site_name}",
        "start_url": ".",
        "display": "standalone",
        "background_color": "#fff",
        # theme.palette.primary holds a Material palette *name* ("teal"), which
        # is not a valid CSS color, so it must be resolved to a real one here.
        "theme_color": templates.primary_color_of(config.theme.get("palette")),
        "icons": []
    }

    # Add favicon as icon if available
    favicon = config.theme.get("favicon", "") or config.theme.get("icon", {}).get("favicon", "")
    if favicon:
        favicon_path = os.path.join(config.docs_dir, favicon)
        if os.path.isfile(favicon_path):
            width, height, mime_type = _get_image_info(favicon_path)
            icon = {"src": favicon}
            if width is not None and height is not None:
                icon["sizes"] = f"{width}x{height}"
            if mime_type:
                icon["type"] = mime_type
            manifest["icons"].append(icon)

    # Add logo as icon if available
    logo = config.theme.get("logo", "")
    if logo:
        logo_path = os.path.join(config.docs_dir, logo)
        if os.path.isfile(logo_path):
            width, height, mime_type = _get_image_info(logo_path)
            icon = {"src": logo}
            if width is not None and height is not None:
                icon["sizes"] = f"{width}x{height}"
            if mime_type:
                icon["type"] = mime_type
            manifest["icons"].append(icon)

    # Add extra icons if specified. `config.extra` is a `Config` (a UserDict),
    # not a `dict`, so these guards must test for the Mapping protocol.
    extra = config.extra or {}
    if isinstance(extra, Mapping):
        pwa_config = extra.get("pwa", {})
        if isinstance(pwa_config, Mapping):
            extra_icons = pwa_config.get("icons", [])
            if extra_icons:
                manifest["icons"].extend(extra_icons)

    # Write manifest.json
    manifest_path = os.path.join(site_dir, "manifest.json")
    try:
        _write_if_changed(manifest_path, json.dumps(manifest, indent=2).encode("utf-8"))
        log.debug(f"Generated PWA manifest at {manifest_path}")
    except Exception as e:
        log.warning(f"Failed to generate PWA manifest: {e}")

    # Generate cache-manifest.json with page hashes for SW hash-based invalidation
    _generate_cache_manifest(site_dir, sw_relative_urls, files, planner)


def _generate_cache_manifest(
    site_dir: str,
    page_urls: list[str],
    files: Files | None = None,
    planner: BuildPlanner | None = None,
) -> None:
    """Generate cache-manifest.json listing every build output + source hash.

    Every file written to site_dir is included (pages, theme assets, search
    index, sitemap, PWA manifest, fonts, etc.). Hashes are computed from the
    Markdown SOURCE file when one exists, otherwise from the built file on disk.
    The SW uses this manifest to cache everything directly, without parsing HTML.

    The ``sizes`` map records the byte size of every built file on disk (the
    exact number of bytes the SW stores in the browser cache), so quota
    eviction can free precisely the space it claims instead of guessing.
    """
    manifest_files = {}
    manifest_sizes = {}

    # Build a lookup from page URL to source Markdown path. Multiple URL forms
    # can map to the same source (e.g. 'second/', 'second', 'second/index.html').
    src_by_url: dict[str, str] = {}
    if files:
        for f in files.documentation_pages():
            if not (f.inclusion.is_included() or f.inclusion.is_not_in_nav()):
                continue
            src_path = f.abs_src_path
            if not src_path or not os.path.isfile(src_path):
                continue

            url = f.url
            if url in ("", "./"):
                forms = ("./", "index.html")
            else:
                forms = (url, url.rstrip("/"), url.rstrip("/") + "/index.html")
            for form in forms:
                src_by_url[form] = src_path

    # Walk the built site and hash every file.
    for root, dirs, filenames in os.walk(site_dir):
        dirs.sort()
        for filename in sorted(filenames):
            abs_path = os.path.join(root, filename)
            rel_path = os.path.relpath(abs_path, site_dir)
            rel_unix = rel_path.replace(os.sep, "/")

            # The SW should not cache itself or its manifest.
            if rel_unix in ("cache-manifest.json", "sw.js"):
                continue

            # Directory-index pages are addressed by their directory URL.
            if filename == "index.html":
                dir_part = os.path.dirname(rel_unix)
                url = "./" if dir_part == "" else dir_part + "/"
            else:
                url = rel_unix

            # Source-first hashing for Markdown-backed pages, built-file fallback
            # for everything else (theme assets, 404.html, sitemap, etc.).
            src_path = src_by_url.get(url)
            hash_path = src_path if src_path and os.path.isfile(src_path) else abs_path

            if planner is not None:
                h = planner._current_hash(Path(hash_path))[:16]
            else:
                with open(hash_path, "rb") as f:
                    h = hashlib.sha256(f.read()).hexdigest()[:16]

            manifest_files[url] = h
            manifest_sizes[url] = os.path.getsize(abs_path)

    manifest = {
        "version": hashlib.sha256(json.dumps(manifest_files, sort_keys=True).encode()).hexdigest()[:12],
        "files": manifest_files,
        "sizes": manifest_sizes,
    }

    manifest_path = os.path.join(site_dir, "cache-manifest.json")
    _write_if_changed(manifest_path, json.dumps(manifest, indent=2).encode("utf-8"))
    log.debug(f"Generated cache manifest with {len(manifest_files)} entries at {manifest_path}")
