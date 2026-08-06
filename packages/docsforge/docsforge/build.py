from __future__ import annotations

import concurrent.futures
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
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlsplit

import jinja2
from jinja2.exceptions import TemplateNotFound

import docsforge
from docsforge import utils
from docsforge.exceptions import Abort, BuildError
from docsforge.files import File, Files, InclusionLevel, get_files, set_exclusions
from docsforge.nav import Navigation, get_navigation
from docsforge.pages import Page
from docsforge.cache import BuildPlanner, CacheManager, DependencyTracker, FileHasher
from docsforge import templates
from docsforge.git_info import get_git_page_info
from docsforge.asset_optimizer import optimize_assets

if TYPE_CHECKING:
    from docsforge.config_defaults import DocsForgeConfig
    import jinja2


log = logging.getLogger(__name__)

# Shared fallback lock for page building when the caller does not provide one.
_default_page_lock = threading.Lock()


def get_context(
    nav: Navigation,
    files: Sequence[File] | Files,
    config: DocsForgeConfig,
    page: Page | None = None,
    base_url: str = '',
) -> templates.TemplateContext:
    """Return the template context for a given page or template."""
    if page is not None:
        base_url = utils.get_relative_url(page.url, '.')
        if base_url and not base_url.endswith('/'):
            base_url += '/'

        # Inject git revision info into page meta if available and not disabled
        extra_cfg = config.get('extra', {})
        git_enabled = getattr(extra_cfg, 'git_revision_date', True) if extra_cfg else True
        if git_enabled and not page.meta.get('git_revision_date_localized'):
            git_info = get_git_page_info(page.file.abs_src_path)
            if git_info:
                page.meta['git_revision_date_localized'] = git_info['updated_display']
                page.meta['git_creation_date_localized'] = git_info['created_display']

    extra_javascript = [
        utils.normalize_url(str(script), base_url) for script in config.extra_javascript
    ]
    extra_css = [utils.normalize_url(path, base_url) for path in config.extra_css]

    if isinstance(files, Files):
        files = files.documentation_pages()

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
        base_url = urlsplit(config.site_url or '/').path
    else:
        base_url = utils.get_relative_url(name, '.')
        if base_url and not base_url.endswith('/'):
            base_url += '/'

    context = get_context(nav, files, config, base_url=base_url)

    # Run `template_context` plugin events.
    context = config.plugins.on_template_context(context, template_name=name, config=config)

    output = template.render(context)

    # Run `post_template` plugin events.
    return config.plugins.on_post_template(output, template_name=name, config=config)


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
        utils.write_file(output.encode('utf-8'), output_path)

        if template_name == 'sitemap.xml':
            log.debug(f"Gzipping template: {template_name}")
            gz_filename = f'{output_path}.gz'
            with open(gz_filename, 'wb') as f:
                timestamp = utils.get_build_timestamp(
                    pages=[f.page for f in files.documentation_pages() if f.page is not None]
                )
                with gzip.GzipFile(
                    fileobj=f, filename=gz_filename, mode='wb', mtime=timestamp
                ) as gz_buf:
                    gz_buf.write(output.encode('utf-8'))
    else:
        log.info(f"Template skipped: '{template_name}' generated empty output.")


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
        utils.write_file(output.encode('utf-8'), file.abs_dest_path)
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
    """Pass a Page to theme template and write output to site_dir."""
    lock = _page_lock or _default_page_lock  # Always have a lock

    with lock:
        config._current_page = page
        page.active = True
        try:
            log.debug(f"Building page {page.file.src_uri}")

            context = get_context(nav, doc_files, config, page)

            # Allow 'template:' override in md source files.
            template = env.get_template(page.meta.get('template', 'main.html'))

            # Run `page_context` plugin events.
            context = config.plugins.on_page_context(context, page=page, config=config, nav=nav)

            if excluded:
                page.content = (
                    '<div class="docsforge-draft-marker" title="This page will not be included into the built site.">'
                    'DRAFT'
                    '</div>' + (page.content or '')
                )

            # Render the template.
            output = template.render(context)

            # Run `post_page` plugin events.
            output = config.plugins.on_post_page(output, page=page, config=config)

            # Write the output file.
            if output.strip():
                utils.write_file(
                    output.encode('utf-8', errors='xmlcharrefreplace'), page.file.abs_dest_path
                )
            else:
                log.info(f"Page skipped: '{page.file.src_uri}'. Generated empty output.")

        except Exception as e:
            message = f"Error building page '{page.file.src_uri}':"
            # Prevent duplicated the error message because it will be printed immediately afterwards.
            if not isinstance(e, BuildError):
                message += f" {e}"
            log.error(message)
            # Continue building other pages instead of crashing
            if config.strict:
                raise
            return
        finally:
            # Deactivate page
            page.active = False
            config._current_page = None


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
    if 'pymdownx.superfences' in config['markdown_extensions']:
        import pymdownx.superfences as superfences_mod
        mdx_configs = copy.deepcopy(config.get('mdx_configs') or {})
        config['mdx_configs'] = mdx_configs
        sf_cfg = mdx_configs.setdefault('pymdownx.superfences', {})
        custom_fences = sf_cfg.setdefault('custom_fences', [])
        if not any(f.get('name') == 'mermaid' for f in custom_fences):
            custom_fences.append({
                'name': 'mermaid',
                'class': 'mermaid',
                'format': superfences_mod.fence_code_format,
            })

    # Run `pre_build` plugin events.
    config.plugins.on_pre_build(config=config)

    if not serve_url:
        log.info(f"Building documentation to directory: {config.site_dir}")

    return config, warning_counter, inclusion


def _ensure_nav_titles(nav: Navigation, config: DocsForgeConfig) -> None:
    """Load Markdown source titles for every page in the navigation.

    Navigation titles are not available until a page's source has been read.
    Reading them here is much cheaper than a full render and lets the nav
    signature detect title changes on incremental builds.
    """
    for page in nav.pages:
        try:
            if getattr(page, "markdown", None) is None:
                page.read_source(config)
        except Exception:
            pass


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
        if getattr(item, 'is_page', False):
            return {
                'type': 'page',
                'src_uri': item.file.src_uri,
                'url': item.url,
                'title': item.title,
                'is_homepage': item.is_homepage,
                'i18n_titles': _sorted_dict(item.i18n_titles),
            }
        if getattr(item, 'is_section', False):
            return {
                'type': 'section',
                'title': item.title,
                'i18n_titles': _sorted_dict(item.i18n_titles),
                'children': [_serialize(c) for c in item.children],
            }
        if getattr(item, 'is_link', False):
            return {
                'type': 'link',
                'title': item.title,
                'url': item.url,
                'i18n_titles': _sorted_dict(item.i18n_titles),
            }
        return {}

    data = {
        'site_url': config.site_url or '',
        'items': [_serialize(i) for i in nav.items],
    }
    hasher = hashlib.sha256()
    hasher.update(json.dumps(data, ensure_ascii=False, sort_keys=True).encode('utf-8'))
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
        orphaned = planner.find_orphaned_outputs(docs_dir, site_dir)
        for f in orphaned:
            log.debug(f"Removing orphaned output: {f}")
            _remove_orphaned_output(f)
    planner.update_sources(current_sources)

    nav = get_navigation(files, config)

    # Run `nav` plugin events.
    nav = config.plugins.on_nav(nav, config=config, files=files)

    # Detect navigation/global changes that require every page to be re-rendered.
    # Titles must be loaded first so the signature reflects page title changes.
    _ensure_nav_titles(nav, config)
    nav_sig = _nav_signature(nav, config)
    nav_changed = planner.nav_sig != nav_sig
    if nav_changed:
        planner.nav_sig = nav_sig
        log.debug("Navigation signature changed; all pages will be re-rendered")

    log.debug("Reading markdown pages.")
    all_doc_files = list(files.documentation_pages(inclusion=inclusion))

    return files, env, nav, all_doc_files, sources_changed, nav_changed


def _remove_orphaned_output(path: Path) -> None:
    """Remove an orphaned output file, logging a warning on transient errors."""
    try:
        path.unlink()
    except OSError as exc:
        log.warning(f"Could not remove orphaned output {path}: {exc}")


def _populate_changed_pages(
    config: DocsForgeConfig,
    files: Files,
    planner: BuildPlanner,
    all_doc_files: list[File],
    inclusion: Callable[[InclusionLevel], bool],
    serve_url: str | None,
    force_all: bool = False,
) -> list[Page]:
    """Render Markdown for all changed pages in parallel."""
    excluded: list[str] = []
    to_populate: list[Page] = []
    for file in all_doc_files:
        log.debug(f"Reading: {file.src_uri}")
        if file.page is None and file.inclusion.is_not_in_nav():
            if serve_url and file.inclusion.is_excluded():
                excluded.append(urljoin(serve_url, file.url))
            Page(None, file, config)
        assert file.page is not None

        # Check if page needs rebuilding
        source_path = Path(file.abs_src_path)
        output_path = Path(file.abs_dest_path)

        if not force_all and not planner.should_rebuild(source_path, output_path):
            log.debug(f"Skipping unchanged page: {file.src_uri}")
            continue

        to_populate.append(file.page)

    # Render Markdown for all changed pages in parallel. The heavy work
    # (read_source + render/markdown.convert) is thread-safe (per-thread
    # Markdown instance); only plugin events are serialized via plugin_lock.
    plugin_lock = threading.RLock()
    max_workers = min(32, os.cpu_count() or 1)
    if to_populate:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [
                ex.submit(_populate_page, p, config, files, True, plugin_lock)
                for p in to_populate
            ]
            errors: list[BaseException] = []
            for f in concurrent.futures.as_completed(futures):
                try:
                    f.result()
                except BaseException as e:
                    errors.append(e)
            if errors:
                if len(errors) == 1:
                    raise errors[0]
                raise ExceptionGroup("Errors populating pages", errors)

    if excluded:
        log.info(
            "The following pages are being built only for the preview "
            "but will be excluded from `docsforge build` per `draft_docs` config:\n  - %s",
            "\n  - ".join(excluded),
        )

    return to_populate


def _write_outputs(
    config: DocsForgeConfig,
    files: Files,
    nav: Navigation,
    env: jinja2.Environment,
    planner: BuildPlanner,
    all_doc_files: list[File],
    inclusion: Callable[[InclusionLevel], bool],
    force_all: bool = False,
) -> bool:
    """Copy static assets and build all changed pages in parallel."""
    # Run `env` plugin events.
    env = config.plugins.on_env(env, config=config, files=files)

    # Start writing files to site_dir now that all data is gathered. Note that order matters. Files
    # with lower precedence get written first so that files with higher precedence can overwrite them.
    log.debug("Copying static assets.")
    files.copy_static_files(dirty=False, inclusion=inclusion)

    for template in config.theme.static_templates:
        _build_theme_template(template, env, files, config, nav)

    for template in config.extra_templates:
        _build_extra_template(template, env, files, config, nav)

    log.debug("Building markdown pages.")
    # Use ThreadPoolExecutor for parallel page building (I/O-bound: template render + file write)
    page_lock = threading.RLock()

    # Collect pages that need rebuilding first so we don't create an executor
    # (and pay its worker-thread shutdown cost) when nothing changed.
    pages_to_build: list[tuple[Page, Path, Path]] = []
    for file in all_doc_files:
        assert file.page is not None
        source_path = Path(file.abs_src_path)
        output_path = Path(file.abs_dest_path)
        if force_all or planner.should_rebuild(source_path, output_path):
            pages_to_build.append((file.page, source_path, output_path))

    built_any = False
    if pages_to_build:
        max_workers = min(32, os.cpu_count() or 1)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                (
                    executor.submit(
                        _build_page,
                        page, config, all_doc_files, nav, env, True,
                        page.file.inclusion.is_excluded(),
                        page_lock,
                    ),
                    source_path,
                    output_path,
                    page,
                )
                for page, source_path, output_path in pages_to_build
            ]

            # Wait for all pages to complete
            for future, source_path, output_path, page in futures:
                try:
                    future.result()
                except Exception:
                    # Error already logged in _build_page; continue with other pages
                    # unless strict mode is enabled, in which case we must fail.
                    # Do NOT update the cache for a failed build — otherwise the
                    # next run would consider the page up-to-date and silently keep
                    # the broken output.
                    if config.strict:
                        raise
                    continue

                # Update cache after successful build. Use page.markdown (the
                # raw source) not page.content (rendered HTML): the snippet
                # include markers are consumed during md.convert(), so only
                # the raw markdown still contains them.
                deps = DependencyTracker.get_file_deps(
                    source_path,
                    page.markdown or "",
                    base_paths=[Path(config.docs_dir)],
                )
                planner.update_cache(source_path, output_path, deps)
                built_any = True

    return built_any


def _finalize_build(
    config: DocsForgeConfig,
    files: Files,
    nav: Navigation,
    planner: BuildPlanner,
    warning_counter: utils.CountHandler,
    built_any: bool,
    sources_changed: bool,
    nav_changed: bool,
    config_path: Path,
    theme_sig: str,
    start: float,
) -> None:
    """Generate PWA assets, validate links, run post-build events, and save cache."""
    nothing_changed = not built_any and not sources_changed and not nav_changed

    if not nothing_changed:
        log_level = config.validation.links.anchors
        for file in files.documentation_pages():
            assert file.page is not None
            file.page.validate_anchor_links(files=files, log_level=log_level)

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
    )

    # Generate PWA manifest + pre-cache list + service worker build hash.
    # Runs AFTER optimize_assets (so the manifest reflects the final file
    # set) and on EVERY build — static assets (CSS, icons) can change without
    # any page/source/nav change, and the service worker needs the updated
    # hashes to re-sync them. The manifest version is deterministic (hash of
    # file hashes), so an unchanged build produces the same version and causes
    # no service-worker churn.
    _generate_pwa_manifest_and_precache(config, files, nav, planner)

    # Save cache state
    config_hash = FileHasher.hash_file(config_path) if config_path.exists() else ""
    planner.save(
        config_hash=config_hash,
        pkg_version=docsforge.__version__,
        theme_sig=theme_sig,
        nav_sig=planner.nav_sig,
    )

    # Save cache after successful build (only if not in strict mode with errors)
    if counts := warning_counter.get_counts():
        msg = ', '.join(f'{v} {k.lower()}s' for k, v in counts)
        raise Abort(f'Aborted with {msg} in strict mode!')

    log.info(f'Documentation built in {time.monotonic() - start:.2f} seconds')


def build(config: DocsForgeConfig, *, serve_url: str | None = None, dirty: bool = True, progress: bool | None = None) -> None:
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
        _populate_changed_pages(
            config, files, planner, all_doc_files, inclusion, serve_url, force_all=nav_changed
        )
        built_any = _write_outputs(
            config, files, nav, env, planner, all_doc_files, inclusion, force_all=nav_changed
        )
        _finalize_build(
            config, files, nav, planner, warning_counter,
            built_any, sources_changed, nav_changed, config_path, theme_sig, start,
        )

    except Exception as e:
        # Run `build_error` plugin events.
        config.plugins.on_build_error(error=e)
        if isinstance(e, BuildError):
            log.error(str(e))
            raise Abort('Aborted with a BuildError!')
        raise

    finally:
        if warning_counter is not None:
            logger.removeHandler(warning_counter)


def site_directory_contains_stale_files(site_directory: str) -> bool:
    """Check if the site directory contains stale files from a previous build."""
    return bool(os.path.exists(site_directory) and os.listdir(site_directory))


def _parse_svg_length(value: str) -> int | None:
    """Extract a numeric pixel length from an SVG width/height attribute."""
    value = value.strip()
    match = re.match(r'^([0-9]*\.?[0-9]+)', value)
    if match:
        try:
            return int(float(match.group(1)))
        except ValueError:
            return None
    return None


def _svg_dimensions(data: bytes) -> tuple[int | None, int | None]:
    """Return (width, height) for an SVG, derived from width/height/viewBox."""
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return None, None
    svg_match = re.search(r'<svg[^>]*>', text, re.DOTALL | re.IGNORECASE)
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
    if data[:8] != b'\x89PNG\r\n\x1a\n' or len(data) < 24:
        return None, None
    return (
        int.from_bytes(data[16:20], 'big'),
        int.from_bytes(data[20:24], 'big'),
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
                int.from_bytes(data[i + 7:i + 9], 'big'),
                int.from_bytes(data[i + 5:i + 7], 'big'),
            )
        if i + 4 > len(data):
            break
        length = struct.unpack('>H', data[i + 2:i + 4])[0]
        i += 2 + length
    return None, None


def _get_image_info(path: str) -> tuple[int | None, int | None, str | None]:
    """Return (width, height, mime_type) for an image file, using the file contents.

    Supports PNG, JPEG and SVG. Width/height may be ``None`` for formats where
    they cannot be determined without additional dependencies.
    """
    mime_type, _ = mimetypes.guess_type(path)
    try:
        with open(path, 'rb') as f:
            data = f.read()
    except OSError:
        return None, None, mime_type
    if not data:
        return None, None, mime_type

    lower_path = path.lower()
    if lower_path.endswith('.png') or mime_type == 'image/png':
        width, height = _png_dimensions(data)
    elif lower_path.endswith(('.jpg', '.jpeg')) or mime_type in ('image/jpeg', 'image/jpg'):
        width, height = _jpeg_dimensions(data)
    elif lower_path.endswith('.svg') or mime_type == 'image/svg+xml':
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

    # Collect all HTML page URLs for pre-caching
    precache_urls = []
    for file in files.documentation_pages():
        if file.inclusion.is_included() or file.inclusion.is_not_in_nav():
            page_url = file.url
            if page_url:
                precache_urls.append(page_url)

    # Also include static templates (404.html, sitemap.xml, etc.)
    for template in config.theme.static_templates:
        if template.endswith('.html'):
            template_url = template.replace('.html', '/')
            if template == '404.html':
                template_url = '/404.html'
            precache_urls.append(template_url)

    # Also include the home page explicitly. Page.url returns '' for the
    # homepage, but File.url uses './'; keep the explicit './' form so the
    # root page survives deduplication and is written into cache-manifest.json.
    home_url = nav.homepage.url if nav.homepage else './'
    if home_url and home_url not in precache_urls:
        precache_urls.insert(0, home_url)

    # Convert all URLs to be relative to the SW script location
    # SW is now at <site_root>/sw.js (root of site)
    # So URLs are just relative to root
    sw_relative_urls = []
    for url in precache_urls:
        if url.startswith('/'):
            sw_relative_urls.append(url.lstrip('/'))
        elif url in ('', './'):
            sw_relative_urls.append('./')
        else:
            # Already relative, keep as-is
            sw_relative_urls.append(url)

    # Always include cache manifest for hash-based syncing
    sw_relative_urls.append('cache-manifest.json')

    # Remove duplicates and sort for deterministic output
    sw_relative_urls = sorted(set(url for url in sw_relative_urls if url))

# Inject pre-cache list and deterministic build hash into service worker.
    # The SW is placed at site root for maximum scope coverage.
    sw_source = os.path.join(site_dir, 'assets', 'javascripts', 'sw.js')
    sw_dest = os.path.join(site_dir, 'sw.js')
    if os.path.isfile(sw_source):
        try:
            with open(sw_source, 'r', encoding='utf-8') as f:
                content = f.read()

            if '__PRE_CACHE_PAGES__' in content:
                content = content.replace(
                    '__PRE_CACHE_PAGES__',
                    json.dumps(sw_relative_urls)
                )

            if '__DOCSFORGE_BASE_URL__' in content:
                # Inject the site base path so the SW works correctly when the
                # documentation is deployed under a subpath (e.g. /docs/).
                base_url_path = urlsplit(config.site_url or '/').path or '/'
                base_url_path = '/' + base_url_path.strip('/')
                if base_url_path != '/':
                    base_url_path += '/'
                content = content.replace('__DOCSFORGE_BASE_URL__', base_url_path)
                log.debug(f"Injected service worker base URL {base_url_path}")

            if '__DOCSFORGE_BUILD_HASH__' in content:
                # Deterministic hash: identical source + config + precache list
                # produces identical SW hash, so unchanged builds don't force
                # clients to reinstall the service worker.
                hasher = hashlib.sha256()
                hasher.update(content.encode('utf-8'))
                hasher.update(json.dumps(sw_relative_urls).encode('utf-8'))
                config_path = Path(config.config_file_path) if config.config_file_path else Path('docsforge.yml')
                if config_path.exists():
                    hasher.update(config_path.read_bytes())
                build_hash = hasher.hexdigest()[:12]
                content = content.replace('__DOCSFORGE_BUILD_HASH__', build_hash)
                log.debug(f"Injected deterministic build hash {build_hash} into service worker")

            with open(sw_dest, 'w', encoding='utf-8') as f:
                f.write(content)

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
        "short_name": config.site_name[:12] if len(config.site_name) > 12 else config.site_name,
        "description": config.site_description or f"Documentation for {config.site_name}",
        "start_url": ".",
        "display": "standalone",
        "background_color": "#fff",
        "theme_color": "#4051b5",
        "icons": []
    }

    # Use primary color from palette if available
    palette = config.theme.get('palette', {})
    if isinstance(palette, list) and palette:
        palette = palette[0]
    if isinstance(palette, dict):
        primary = palette.get('primary', 'indigo')
        manifest["theme_color"] = primary

    # Add favicon as icon if available
    favicon = config.theme.get('favicon', '') or config.theme.get('icon', {}).get('favicon', '')
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
    logo = config.theme.get('logo', '')
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

    # Add extra icons if specified
    extra = config.extra or {}
    if isinstance(extra, dict):
        pwa_config = extra.get('pwa', {})
        if isinstance(pwa_config, dict):
            extra_icons = pwa_config.get('icons', [])
            if extra_icons:
                manifest["icons"].extend(extra_icons)

    # Write manifest.json
    manifest_path = os.path.join(site_dir, 'manifest.json')
    try:
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2)
        log.debug(f"Generated PWA manifest at {manifest_path}")
    except Exception as e:
        log.warning(f"Failed to generate PWA manifest: {e}")

    # Generate cache-manifest.json with page hashes for SW hash-based invalidation
    _generate_cache_manifest(site_dir, sw_relative_urls, files, planner)


def _generate_cache_manifest(site_dir: str, page_urls: list[str], files: Files | None = None, planner: BuildPlanner | None = None) -> None:
    """Generate cache-manifest.json listing every build output + source hash.

    Every file written to site_dir is included (pages, theme assets, search
    index, sitemap, PWA manifest, fonts, etc.). Hashes are computed from the
    Markdown SOURCE file when one exists, otherwise from the built file on disk.
    The SW uses this manifest to cache everything directly, without parsing HTML.
    """
    manifest_files = {}

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
            if url in ('', './'):
                forms = ('./', 'index.html')
            else:
                forms = (url, url.rstrip('/'), url.rstrip('/') + '/index.html')
            for form in forms:
                src_by_url[form] = src_path

    # Walk the built site and hash every file.
    for root, dirs, filenames in os.walk(site_dir):
        dirs.sort()
        for filename in sorted(filenames):
            abs_path = os.path.join(root, filename)
            rel_path = os.path.relpath(abs_path, site_dir)
            rel_unix = rel_path.replace(os.sep, '/')

            # The SW should not cache itself or its manifest.
            if rel_unix in ('cache-manifest.json', 'sw.js'):
                continue

            # Directory-index pages are addressed by their directory URL.
            if filename == 'index.html':
                dir_part = os.path.dirname(rel_unix)
                url = './' if dir_part == '' else dir_part + '/'
            else:
                url = rel_unix

            # Source-first hashing for Markdown-backed pages, built-file fallback
            # for everything else (theme assets, 404.html, sitemap, etc.).
            src_path = src_by_url.get(url)
            if src_path and os.path.isfile(src_path):
                hash_path = src_path
            else:
                hash_path = abs_path

            if planner is not None:
                h = planner._current_hash(Path(hash_path))[:16]
            else:
                with open(hash_path, 'rb') as f:
                    h = hashlib.sha256(f.read()).hexdigest()[:16]

            manifest_files[url] = h

    manifest = {
        "version": hashlib.sha256(json.dumps(manifest_files, sort_keys=True).encode()).hexdigest()[:12],
        "files": manifest_files,
    }

    manifest_path = os.path.join(site_dir, 'cache-manifest.json')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
    log.debug(f"Generated cache manifest with {len(manifest_files)} entries at {manifest_path}")
