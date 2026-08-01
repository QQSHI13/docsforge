"""A DocsForge plugin to minify HTML, JS or CSS files prior to being written to disk.

Always enabled with no configuration options.
"""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import csscompressor
import jsmin
import minify_html
from packaging import version

from docsforge.config_defaults import DocsForgeConfig
from docsforge.pages import Page
from docsforge.core.plugin_base import BasePlugin

EXTRAS: Dict[str, str] = {
    "js": "extra_javascript",
    "css": "extra_css",
}

MINIFIERS: Dict[str, Callable] = {
    "js": jsmin.jsmin,
    "css": csscompressor.compress,
}

log = logging.getLogger(__name__)

if not getattr(csscompressor, "__version__", None):
    csscompressor.__version__ = "0.9.6"

if version.parse(csscompressor.__version__) <= version.parse("0.9.5"):
    # Monkey patch csscompressor 0.9.5
    # See https://github.com/sprymix/csscompressor/issues/9#issuecomment-1024417374
    _preserve_call_tokens_original = csscompressor._preserve_call_tokens
    _url_re = csscompressor._url_re

    def my_new_preserve_call_tokens(*args, **kwargs):
        """If regex is for url pattern, switch the keyword remove_ws to False.
        
        Such configuration will preserve svg code in url() pattern of CSS file.
        """
        if _url_re == args[1]:
            kwargs["remove_ws"] = False
        return _preserve_call_tokens_original(*args, **kwargs)

    csscompressor._preserve_call_tokens = my_new_preserve_call_tokens
    assert csscompressor._preserve_call_tokens == my_new_preserve_call_tokens


class MinifyPlugin(BasePlugin):
    """Always-on minify plugin. No configuration options."""

    config_scheme: Tuple = ()

    def __init__(self) -> None:
        # original site-relative path -> minified content
        self._pending_minified: dict[str, str] = {}

    @staticmethod
    def _item_path(item) -> str:
        """Return the path string from an extra item (ExtraScriptValue or str)."""
        return str(item.path if hasattr(item, 'path') else item).strip()

    @staticmethod
    def _is_within(path: Path, base: Path) -> bool:
        """Return True if *path* is contained within *base* after resolving."""
        try:
            path.resolve().relative_to(base.resolve())
            return True
        except ValueError:
            return False

    def _minify_file_data_with_func(self, file_data: str, minify_func: Callable) -> str:
        """Use the minify_func and return the minified data."""
        if minify_func.__name__ == "jsmin":
            return minify_func(file_data, quote_chars="'\"`")
        else:
            return minify_func(file_data)

    def _process_extras(self, file_type: str, config: DocsForgeConfig) -> None:
        """Minify extra JS/CSS files and update config before pages are rendered.

        The minified content is written to disk in on_post_build, after static
        files have been copied to the site directory.  Config paths are updated
        here (before rendering) with a cache-busting query string so the HTML
        references match the file that will exist on disk.
        """
        minify_func: Callable = MINIFIERS[file_type]
        extra_key: str = EXTRAS[file_type]
        extra_files = config.get(extra_key, [])
        if not extra_files:
            return

        docs_dir = Path(config['docs_dir'])
        extra_list = config[extra_key]

        for idx, extra_item in enumerate(extra_files):
            file_path = self._item_path(extra_item)
            # Skip absolute/external URLs and empty paths.
            if not file_path or file_path.startswith(('http://', 'https://', '//')):
                continue
            src_path = docs_dir / file_path.lstrip('/')
            try:
                src_path = src_path.resolve()
            except (OSError, ValueError):
                log.warning(f"Invalid extra {file_type} path: {file_path}")
                continue
            if not src_path.exists():
                continue
            if not self._is_within(src_path, docs_dir):
                log.warning(f"Extra {file_type} path escapes docs_dir: {file_path}")
                continue

            try:
                file_data = src_path.read_text(encoding='utf-8')
                minified = self._minify_file_data_with_func(file_data, minify_func)
                file_hash = hashlib.sha384(minified.encode('utf-8')).hexdigest()[:8]
                site_rel_path = file_path.lstrip('/')
                self._pending_minified[site_rel_path] = minified
                new_path = f"{file_path}?v={file_hash}"
                if hasattr(extra_item, 'path'):
                    extra_item.path = new_path
                else:
                    extra_list[idx] = new_path
            except Exception as e:
                log.warning(f"Failed to minify extra {file_type} file {file_path}: {e}")

    def _minify_html_page(self, output: str) -> Optional[str]:
        """Minify HTML page content. Always enabled."""
        return minify_html.minify(output, minify_js=False, minify_css=False)

    def on_pre_build(self, *, config: DocsForgeConfig) -> None:
        """Prepare minified extra assets and update config before rendering."""
        self._pending_minified.clear()
        self._process_extras("js", config)
        self._process_extras("css", config)

    def on_post_page(self, output: str, *, page: Page, config: DocsForgeConfig) -> Optional[str]:
        """Minify HTML page before saving to disk."""
        return self._minify_html_page(output)

    def on_post_template(
        self, output_content: str, *, template_name: str, config: DocsForgeConfig
    ) -> Optional[str]:
        """Minify HTML template files, e.g. 404.html, before saving to disk."""
        if template_name.endswith(".html"):
            return self._minify_html_page(output_content)
        return output_content

    def on_post_build(self, *, config: DocsForgeConfig) -> None:
        """Write minified extra JS/CSS files to the site directory."""
        site_dir = Path(config['site_dir']).resolve()
        for site_rel_path, minified in self._pending_minified.items():
            dest_path = (site_dir / site_rel_path).resolve()
            if not self._is_within(dest_path, site_dir):
                log.warning(f"Minified file path escapes site_dir: {site_rel_path}")
                continue
            try:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_text(minified, encoding='utf-8')
            except Exception as e:
                log.warning(f"Failed to write minified file {site_rel_path}: {e}")
