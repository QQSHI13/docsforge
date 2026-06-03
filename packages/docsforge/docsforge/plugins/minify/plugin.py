"""
An MkDocs plugin to minify HTML, JS or CSS files prior to being written to disk.
Always enabled with no configuration options.
"""
import hashlib
from pathlib import Path
import os
from typing import Callable, Dict, List, Optional, Tuple, Union

import minify_html
import csscompressor
import jsmin
from docsforge.config_defaults import DocsForgeConfig
from docsforge.plugins import BasePlugin
from docsforge.pages import Page
from packaging import version

EXTRAS: Dict[str, str] = {
    "js": "extra_javascript",
    "css": "extra_css",
}

MINIFIERS: Dict[str, Callable] = {
    "js": jsmin.jsmin,
    "css": csscompressor.compress,
}

if version.parse(csscompressor.__version__) <= version.parse("0.9.5"):
    # Monkey patch csscompressor 0.9.5
    # See https://github.com/sprymix/csscompressor/issues/9#issuecomment-1024417374
    _preserve_call_tokens_original = csscompressor._preserve_call_tokens
    _url_re = csscompressor._url_re

    def my_new_preserve_call_tokens(*args, **kwargs):
        """If regex is for url pattern, switch the keyword remove_ws to False
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

    def _minified_asset(self, file_name: str, file_type: str, file_hash: str) -> str:
        """Add .hash.min. to the asset file name for cache busting."""
        hash_part: str = f".{file_hash[:6]}" if file_hash else ""
        return file_name.replace(f".{file_type}", f"{hash_part}.min.{file_type}")

    def _minify(self, file_type: str, config: DocsForgeConfig) -> None:
        """Minify all extra JS/CSS files and rename with hash."""
        minify_func: Callable = MINIFIERS[file_type]
        extra_key: str = EXTRAS[file_type]
        extra_files = config.get(extra_key, [])
        
        if not extra_files:
            return

        site_dir = Path(config['site_dir'])

        for extra_item in extra_files:
            file_path = str(extra_item.path if hasattr(extra_item, 'path') else extra_item)
            file_path = file_path.lstrip('/')
            
            full_path = site_dir / file_path
            if not full_path.exists():
                continue

            with open(full_path, mode="r+", encoding="utf8") as file:
                file_data = file.read()
                minified = self._minify_file_data_with_func(file_data, minify_func)
                file.seek(0)
                file.write(minified)
                file.truncate()

            # Generate hash for cache busting
            file_hash = hashlib.sha384(minified.encode("utf8")).hexdigest()
            new_name = self._minified_asset(str(full_path), file_type, file_hash)
            os.rename(str(full_path), new_name)

            # Update the config to point to the new file name
            rel_new = os.path.relpath(new_name, str(site_dir))
            if hasattr(extra_item, 'path'):
                extra_item.path = rel_new
            else:
                # Update config list in place
                idx = config[extra_key].index(extra_item)
                config[extra_key][idx] = rel_new

    @staticmethod
    def _minify_file_data_with_func(file_data: str, minify_func: Callable) -> str:
        """Use the minify_func and return the minified data."""
        if minify_func.__name__ == "jsmin":
            return minify_func(file_data, quote_chars="'\"`")
        else:
            return minify_func(file_data)

    def _minify_html_page(self, output: str) -> Optional[str]:
        """Minify HTML page content. Always enabled."""
        return minify_html.minify(output, minify_js=False, minify_css=False)

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
        """Process extras before saving to disk."""
        self._minify("js", config)
        self._minify("css", config)
