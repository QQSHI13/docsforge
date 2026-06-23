from __future__ import annotations

import concurrent.futures
import gzip
import hashlib
import json
import logging
import os
import threading
import time
from collections.abc import Sequence
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
        utils.normalize_url(str(script), page, base_url) for script in config.extra_javascript
    ]
    extra_css = [utils.normalize_url(path, page, base_url) for path in config.extra_css]

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
    template_name: str, files: Files, config: DocsForgeConfig, nav: Navigation
):
    """Build user templates which are not part of the theme."""
    log.debug(f"Building extra template: {template_name}")

    file = files.get_file_from_path(template_name)
    if file is None:
        log.warning(f"Template skipped: '{template_name}' not found in docs_dir.")
        return

    try:
        template = jinja2.Template(file.content_string)
    except Exception as e:
        log.warning(f"Error reading template '{template_name}': {e}")
        return

    output = _build_template(template_name, template, files, config, nav)

    if output.strip():
        utils.write_file(output.encode('utf-8'), file.abs_dest_path)
    else:
        log.info(f"Template skipped: '{template_name}' generated empty output.")


def _populate_page(page: Page, config: DocsForgeConfig, files: Files, dirty: bool = True) -> None:
    """Read page content from docs_dir and render Markdown."""
    config._current_page = page
    try:
        # Run the `pre_page` plugin event
        page = config.plugins.on_pre_page(page, config=config, files=files)

        page.read_source(config)
        assert page.markdown is not None

        # Run `page_markdown` plugin events.
        page.markdown = config.plugins.on_page_markdown(
            page.markdown, page=page, config=config, files=files
        )

        page.render(config, files)
        assert page.content is not None

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
    lock = _page_lock or threading.Lock()  # Always have a lock

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


def build(config: DocsForgeConfig, *, serve_url: str | None = None, dirty: bool = True, progress: bool | None = None) -> None:
    """Perform a site build — always incremental, always complete."""
    logger = logging.getLogger("docsforge")

    # Initialize cache for dirty builds
    cache = CacheManager()
    hasher = FileHasher()
    planner = BuildPlanner(cache, hasher)

    # Check config hash for full rebuild decision
    config_path = Path(config.config_file_path) if config.config_file_path else Path("docsforge.yml")
    needs_full_rebuild = planner.should_full_rebuild(config_path)

    if dirty and needs_full_rebuild:
        # Config changed — invalidate cache for a fresh baseline
        cache.invalidate()

    # Add CountHandler for strict mode
    warning_counter = utils.CountHandler()
    warning_counter.setLevel(logging.WARNING)
    if config.strict:
        logging.getLogger("docsforge").addHandler(warning_counter)

    inclusion = InclusionLevel.is_in_serve if serve_url else InclusionLevel.is_included

    try:
        start = time.monotonic()

        # Run `config` plugin events.
        config = config.plugins.on_config(config)

        # Ensure mermaid fence config is present in markdown extensions.
        # This is done once per build instead of per-page for efficiency.
        if 'pymdownx.superfences' in config['markdown_extensions']:
            import pymdownx.superfences as superfences_mod
            mdx_configs = config.setdefault('mdx_configs', {})
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

        # Remove orphaned output files (pages deleted from source)
        docs_dir = Path(config.docs_dir)
        site_dir = Path(config.site_dir)
        orphaned = planner.find_orphaned_outputs(docs_dir, site_dir)
        for f in orphaned:
            log.debug(f"Removing orphaned output: {f}")
            f.unlink()

        if not serve_url:
            log.info(f"Building documentation to directory: {config.site_dir}")

        # Compile TikZ diagrams BEFORE scanning files so MkDocs discovers the SVGs.
        from docsforge import tikz
        tikz.compile_tikz_files(config, output_to_docs=True)

        # First gather all data from all files/pages to ensure all data is consistent across all pages.

        files = get_files(config)
        env = config.theme.get_env()
        files.add_files_from_theme(env, config)

        # Run `files` plugin events.
        files = config.plugins.on_files(files, config=config)
        # If plugins have added files but haven't set their inclusion level, calculate it again.
        set_exclusions(files, config)

        nav = get_navigation(files, config)

        # Run `nav` plugin events.
        nav = config.plugins.on_nav(nav, config=config, files=files)

        log.debug("Reading markdown pages.")
        # Cache the documentation pages list to avoid repeated iteration
        all_doc_files = list(files.documentation_pages(inclusion=inclusion))
        excluded = []
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
            if not planner.should_rebuild(source_path, output_path):
                log.debug(f"Skipping unchanged page: {file.src_uri}")
                continue
            
            _populate_page(file.page, config, files, True)
        if excluded:
            log.info(
                "The following pages are being built only for the preview "
                "but will be excluded from `docsforge build` per `draft_docs` config:\n  - %s",
                "\n  - ".join(excluded),
            )

        # Run `env` plugin events.
        env = config.plugins.on_env(env, config=config, files=files)

        # Start writing files to site_dir now that all data is gathered. Note that order matters. Files
        # with lower precedence get written first so that files with higher precedence can overwrite them.

        log.debug("Copying static assets.")
        files.copy_static_files(dirty=False, inclusion=inclusion)

        for template in config.theme.static_templates:
            _build_theme_template(template, env, files, config, nav)

        for template in config.extra_templates:
            _build_extra_template(template, files, config, nav)

        log.debug("Building markdown pages.")
        # Reuse the cached doc_files list instead of calling documentation_pages() again
        doc_files = all_doc_files

        # Use ThreadPoolExecutor for parallel page building (I/O-bound: template render + file write)
        page_lock = threading.RLock()
        max_workers = min(32, os.cpu_count() or 1)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for file in doc_files:
                assert file.page is not None

                source_path = Path(file.abs_src_path)
                output_path = Path(file.abs_dest_path)

                # Check if page needs rebuilding
                if not planner.should_rebuild(source_path, output_path):
                    continue

                future = executor.submit(
                    _build_page,
                    file.page, config, doc_files, nav, env, True,
                    file.inclusion.is_excluded(),
                    page_lock,
                )
                futures.append((future, source_path, output_path, file.page))

            # Wait for all pages to complete
            for future, source_path, output_path, page in futures:
                try:
                    future.result()
                except Exception:
                    # Error already logged in _build_page; continue with other pages
                    pass

                # Update cache after successful build
                deps = DependencyTracker.get_file_deps(source_path, page.content or "")
                planner.update_cache(source_path, output_path, deps)

        # Generate PWA manifest and pre-cache all pages in the service worker
        _generate_pwa_manifest_and_precache(config, files, nav)

        log_level = config.validation.links.anchors
        for file in doc_files:
            assert file.page is not None
            file.page.validate_anchor_links(files=files, log_level=log_level)

        # Run `post_build` plugin events.
        config.plugins.on_post_build(config=config)

        # Optimize static assets: remove unused files, source maps, old font formats
        optimize_assets(config.site_dir)

        # Save cache state
        config_hash = hasher.hash_file(config_path) if config_path.exists() else ""
        planner.save(config_hash=config_hash)

        # Save cache after successful build (only if not in strict mode with errors)
        if counts := warning_counter.get_counts():
            msg = ', '.join(f'{v} {k.lower()}s' for k, v in counts)
            raise Abort(f'Aborted with {msg} in strict mode!')

        log.info(f'Documentation built in {time.monotonic() - start:.2f} seconds')

    except Exception as e:
        # Run `build_error` plugin events.
        config.plugins.on_build_error(error=e)
        if isinstance(e, BuildError):
            log.error(str(e))
            raise Abort('Aborted with a BuildError!')
        raise

    finally:
        logger.removeHandler(warning_counter)


def site_directory_contains_stale_files(site_directory: str) -> bool:
    """Check if the site directory contains stale files from a previous build."""
    return bool(os.path.exists(site_directory) and os.listdir(site_directory))


def _generate_pwa_manifest_and_precache(
    config: DocsForgeConfig, files: Files, nav: Navigation
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

    # Also include the home page explicitly
    home_url = nav.homepage.url if nav.homepage else './'
    if home_url not in precache_urls:
        precache_urls.insert(0, home_url)

    # Convert all URLs to be relative to the SW script location
    # SW is now at <site_root>/sw.js (root of site)
    # So URLs are just relative to root
    sw_relative_urls = []
    for url in precache_urls:
        if url.startswith('/'):
            sw_relative_urls.append(url.lstrip('/'))
        else:
            # Already relative, keep as-is
            sw_relative_urls.append(url)

    # Remove redundant ./ in the result
    sw_relative_urls = [url.replace('./', '') for url in sw_relative_urls]

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
            manifest["icons"].append({
                "src": favicon,
                "sizes": "48x48",
                "type": "image/png"
            })

    # Add logo as icon if available
    logo = config.theme.get('logo', '')
    if logo:
        logo_path = os.path.join(config.docs_dir, logo)
        if os.path.isfile(logo_path):
            manifest["icons"].append({
                "src": logo,
                "sizes": "512x512",
                "type": "image/svg+xml" if logo.endswith('.svg') else "image/png"
            })

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
    _generate_cache_manifest(site_dir, sw_relative_urls, files)


def _generate_cache_manifest(site_dir: str, page_urls: list[str], files: Files | None = None) -> None:
    """Generate cache-manifest.json listing every page URL + source content hash.

    Hashes are computed from Markdown SOURCE files, not built HTML, so the
    manifest version only changes when the source actually changes — not when
    the build cache produces different output.

    The service worker fetches this on activation and compares hashes with
    cached responses. Only pages with changed hashes are re-fetched.
    """
    manifest_files = {}

    for url in page_urls:
        # Try to hash the source .md file for deterministic results
        src_path = None
        if files:
            # Find the source file for this URL
            for f in files.documentation_pages():
                if f.url == url or f.url.rstrip("/") == url.rstrip("/"):
                    src_path = f.abs_src_path
                    break

        if src_path and os.path.isfile(src_path):
            with open(src_path, 'rb') as f:
                h = hashlib.sha256(f.read()).hexdigest()[:16]
            manifest_files[url] = h
        else:
            # Fallback: hash the built HTML file (for non-MD files like 404.html)
            file_path = os.path.join(site_dir, url, 'index.html') if not url.endswith('.html') else os.path.join(site_dir, url)
            if os.path.isfile(file_path):
                with open(file_path, 'rb') as f:
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
