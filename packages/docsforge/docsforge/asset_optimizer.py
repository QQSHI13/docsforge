import logging
import os
import re
from html.parser import HTMLParser
from pathlib import Path

log = logging.getLogger(__name__)

# File extensions considered assets.
_ASSET_EXTENSIONS = frozenset({
    'css', 'js', 'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp',
    'woff', 'woff2', 'ttf', 'eot', 'otf',
})


class _AssetReferenceParser(HTMLParser):
    """Extract relative asset references from HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.refs: list[str] = []
        self._in_style = False
        self._style_buffer: list[str] = []

    def _collect(self, url: str | None) -> None:
        if not url:
            return
        url = url.strip()
        if not url:
            return
        self.refs.append(url)

    def _collect_srcset(self, value: str | None) -> None:
        if not value:
            return
        for entry in value.split(','):
            entry = entry.strip()
            if not entry:
                continue
            parts = entry.split()
            if parts:
                self._collect(parts[0])

    def _collect_inline_style(self, content: str) -> None:
        for match in _CSS_URL_RE.finditer(content):
            url = next(g for g in match.groups() if g is not None)
            self._collect(url)
        for match in _CSS_IMPORT_RE.finditer(content):
            url = next(g for g in match.groups() if g is not None)
            self._collect(url)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == 'style':
            self._in_style = True
            self._style_buffer = []
            return

        attr_dict = dict(attrs)
        if tag == 'link':
            self._collect(attr_dict.get('href'))
        elif tag in ('script', 'img', 'video', 'audio', 'source'):
            self._collect(attr_dict.get('src'))
            if tag in ('img', 'source'):
                self._collect_srcset(attr_dict.get('srcset'))
        elif tag == 'image':
            self._collect(attr_dict.get('href'))
        else:
            # data-* attributes that reference assets.
            for name, value in attr_dict.items():
                if name.startswith('data-') and value:
                    ext = value.split('.')[-1].split('?')[0].lower()
                    if ext in _ASSET_EXTENSIONS:
                        self._collect(value)

    def handle_endtag(self, tag: str) -> None:
        if tag == 'style' and self._in_style:
            self._collect_inline_style(''.join(self._style_buffer))
            self._in_style = False
            self._style_buffer = []

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self._style_buffer.append(data)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)


_CSS_URL_RE = re.compile(
    r"""
    url\(\s*
    (?:
        "([^"\\]*)" |
        '([^'\\]*)' |
        ([^)\s]*)
    )
    \s*\)
    """,
    re.VERBOSE,
)

_CSS_IMPORT_RE = re.compile(
    r"""
    @import\s+
    (?:
        url\(\s*(?:
            "([^"\\]*)" |
            '([^'\\]*)' |
            ([^)\s]*)
        )\s*\) |
        "([^"]*)" |
        '([^']*)'
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)


def _is_external_url(url: str) -> bool:
    """Return True if the URL is external, a fragment, or a data URI."""
    if not url:
        return True
    if url.startswith(('http://', 'https://', '//', 'data:', 'mailto:', 'tel:', '#')):
        return True
    return False


def _normalize_asset_url(url: str, file_dir: str) -> str | None:
    """Return a site-relative posix path for a local asset URL, or None."""
    if _is_external_url(url):
        return None
    url = url.split('?')[0].split('#')[0]
    if not url:
        return None

    if url.startswith('/'):
        rel_path = url.lstrip('/')
    else:
        rel_path = os.path.join(file_dir, url) if file_dir else url

    try:
        rel_path = os.path.normpath(rel_path).replace('\\', '/')
    except Exception:
        return None

    if rel_path.startswith('..'):
        return None
    return rel_path or None


def _find_referenced_assets(site_dir: str) -> set[str]:
    """Scan all HTML, CSS, and JS files in site_dir for referenced assets.

    Returns a set of relative paths (from site_dir) of referenced assets.
    """
    referenced: set[str] = set()
    site_path = Path(site_dir)

    for file_path in site_path.rglob('*'):
        if not file_path.is_file():
            continue
        ext = file_path.suffix.lower()
        if ext not in ('.html', '.css', '.js'):
            continue

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue

        file_dir = file_path.parent.relative_to(site_path)
        file_dir_str = str(file_dir).replace('\\', '/') if str(file_dir) != '.' else ''

        if ext == '.html':
            parser = _AssetReferenceParser()
            parser.feed(content)
            for url in parser.refs:
                normalized = _normalize_asset_url(url, file_dir_str)
                if normalized:
                    referenced.add(normalized)

        elif ext == '.css':
            for match in _CSS_URL_RE.finditer(content):
                url = next(g for g in match.groups() if g is not None)
                normalized = _normalize_asset_url(url, file_dir_str)
                if normalized:
                    referenced.add(normalized)
            for match in _CSS_IMPORT_RE.finditer(content):
                url = next(g for g in match.groups() if g is not None)
                normalized = _normalize_asset_url(url, file_dir_str)
                if normalized:
                    referenced.add(normalized)

        elif ext == '.js':
            # Conservative regex for string literals that look like asset paths.
            for match in re.finditer(
                r'''["']([^"']+\.(?:css|js|png|jpg|jpeg|gif|svg|webp|woff|woff2|ttf|eot|otf))["']''',
                content,
                re.IGNORECASE,
            ):
                url = match.group(1)
                normalized = _normalize_asset_url(url, file_dir_str)
                if normalized:
                    referenced.add(normalized)

    return referenced


def cleanup_unused_assets(site_dir: str, extra_whitelist: set[str] | None = None) -> None:
    """Remove unused static assets from the built site.

    This is a post-build cleanup that removes assets that are not referenced
    by any HTML, CSS, or JS file in the site.

    Args:
        site_dir: The built site directory
        extra_whitelist: Additional file paths to keep (relative to site_dir)
    """
    site_path = Path(site_dir)
    if not site_path.exists():
        return

    referenced = _find_referenced_assets(site_dir)

    # Add whitelist patterns
    if extra_whitelist:
        referenced.update(extra_whitelist)

    # Always keep these important files even if not directly referenced
    always_keep = {
        'sitemap.xml', 'sitemap.xml.gz',
        '404.html', 'search.html',
        'assets/javascripts/workers/search.js',  # Search worker loaded dynamically
    }
    referenced.update(always_keep)

    # Find all files that might be candidates for removal
    # Focus on heavy directories: icons, fonts, images
    candidate_dirs = ['.icons', 'assets/images', 'assets/fonts']

    removed_count = 0
    removed_size = 0

    for candidate_dir in candidate_dirs:
        dir_path = site_path / candidate_dir
        if not dir_path.exists():
            continue

        for file_path in dir_path.rglob('*'):
            if not file_path.is_file():
                continue

            rel_path = file_path.relative_to(site_path).as_posix()

            # Check if this file is referenced
            if rel_path not in referenced:
                # Double-check: is this file referenced by a relative path from another directory?
                # e.g., "../.icons/material/home.svg" from "assets/stylesheets/"
                is_referenced = False
                for ref in referenced:
                    if ref.endswith(os.path.basename(rel_path)) or rel_path in ref:
                        is_referenced = True
                        break

                if not is_referenced:
                    file_size = file_path.stat().st_size
                    try:
                        file_path.unlink()
                        removed_count += 1
                        removed_size += file_size
                        log.debug(f"Removed unused asset: {rel_path}")
                    except Exception as e:
                        log.warning(f"Could not remove {rel_path}: {e}")

    # Clean up empty directories
    for candidate_dir in candidate_dirs:
        dir_path = site_path / candidate_dir
        if not dir_path.exists():
            continue

        # Remove empty directories bottom-up
        for dirpath, dirnames, filenames in os.walk(str(dir_path), topdown=False):
            if not dirnames and not filenames:
                try:
                    os.rmdir(dirpath)
                    log.debug(f"Removed empty directory: {dirpath}")
                except Exception:
                    pass

    if removed_count > 0:
        log.info(
            f"Removed {removed_count} unused assets ({removed_size / 1024 / 1024:.2f} MB saved)"
        )


def remove_source_maps(site_dir: str) -> None:
    """Remove .map files and sourceMappingURL comments from the built site."""
    site_path = Path(site_dir)
    if not site_path.exists():
        return

    # Remove .map files
    removed_count = 0
    removed_size = 0

    for map_file in site_path.rglob('*.map'):
        if not map_file.is_file():
            continue

        file_size = map_file.stat().st_size
        try:
            map_file.unlink()
            removed_count += 1
            removed_size += file_size
        except Exception as e:
            log.warning(f"Could not remove {map_file}: {e}")

    if removed_count > 0:
        log.info(
            f"Removed {removed_count} source map files ({removed_size / 1024:.2f} KB saved)"
        )

    # Strip sourceMappingURL comments from JS files to prevent 404 requests
    js_files_modified = 0
    sourcemap_pattern = re.compile(r'//# sourceMappingURL=[^\s]+\s*\n?')

    for js_file in site_path.rglob('*.js'):
        if not js_file.is_file():
            continue

        try:
            content = js_file.read_text(encoding='utf-8', errors='ignore')
            if 'sourceMappingURL=' in content:
                cleaned = sourcemap_pattern.sub('', content)
                js_file.write_text(cleaned, encoding='utf-8')
                js_files_modified += 1
        except Exception as e:
            log.warning(f"Could not strip source map comment from {js_file}: {e}")

    if js_files_modified > 0:
        log.info(f"Stripped source map comments from {js_files_modified} JS files")


def remove_unused_font_formats(site_dir: str) -> None:
    """Remove font formats that are not needed (keep only WOFF2).

    Modern browsers support WOFF2. We keep WOFF as a fallback for older browsers
    but remove TTF, EOT, and SVG font formats.
    """
    site_path = Path(site_dir)
    if not site_path.exists():
        return

    font_dirs = list(site_path.rglob('**/fonts'))

    removed_count = 0
    removed_size = 0

    # Remove old font formats
    old_extensions = {'.ttf', '.eot', '.svg'}

    for font_dir in font_dirs:
        if not font_dir.is_dir():
            continue

        for font_file in font_dir.iterdir():
            if not font_file.is_file():
                continue

            if font_file.suffix.lower() in old_extensions:
                file_size = font_file.stat().st_size
                try:
                    font_file.unlink()
                    removed_count += 1
                    removed_size += file_size
                except Exception as e:
                    log.warning(f"Could not remove {font_file}: {e}")

    if removed_count > 0:
        log.info(
            f"Removed {removed_count} old font files ({removed_size / 1024:.2f} KB saved)"
        )


def optimize_assets(site_dir: str) -> None:
    """Run all asset optimization passes on the built site."""
    log.info("Optimizing static assets...")

    # Remove source maps (pure bloat)
    remove_source_maps(site_dir)

    # Remove unused font formats
    remove_unused_font_formats(site_dir)

    # Remove unused assets (icons, images, etc.)
    cleanup_unused_assets(site_dir)

    log.info("Asset optimization complete")
