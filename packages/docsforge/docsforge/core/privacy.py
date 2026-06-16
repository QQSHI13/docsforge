"""Privacy plugin - external asset downloading and link processing."""

from __future__ import annotations

import errno
import logging
import os
import posixpath
import re
import requests
import sys
from colorama import Fore, Style
from concurrent.futures import Future, wait
from concurrent.futures.thread import ThreadPoolExecutor
from fnmatch import fnmatch
from hashlib import sha1
from html.parser import HTMLParser
from re import Match
from urllib.parse import ParseResult as URL, urlparse, unquote
from xml.etree.ElementTree import Element, tostring

from docsforge import is_error_template
from docsforge.config_base import Config
from docsforge.config_defaults import DocsForgeConfig
from docsforge.config_options import (
    Choice,
    Deprecated,
    DictOfItems,
    ExtraScriptValue,
    ListOfItems,
    Type,
)
from docsforge.core.plugin_base import BasePlugin, event_priority
from docsforge.exceptions import PluginError
from docsforge.files import File, Files

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT_IN_SECS = 5

# Expected file extensions
extensions = {
    "application/javascript": ".js",
    "image/avif": ".avif",
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "image/webp": ".webp",
    "text/javascript": ".js",
    "text/css": ".css"
}

# Options for log level
LogLevel = ("error", "warn", "info", "debug")

# Set up logging
log = logging.getLogger("docsforge.privacy")

# ---------------------------------------------------------------------------
# Fragment Parser
# ---------------------------------------------------------------------------

class FragmentParser(HTMLParser):
    """
    Streaming HTML fragment parser.

    Previously used lxml for fault-tolerant HTML5 parsing, but it adds 20 MB
    to Docker images. The built-in XML parser doesn't handle HTML5, so we use
    a streaming parser and construct the element ourselves.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.result = None

    def handle_starttag(self, tag, attrs):
        self.result = Element(tag, dict(attrs))

# ---------------------------------------------------------------------------
# Privacy Configuration
# ---------------------------------------------------------------------------

class PrivacyConfig(Config):
    """Privacy plugin configuration."""

    enabled = Type(bool, default=True)
    concurrency = Type(int, default=max(1, os.cpu_count() - 1))

    # Settings for caching
    cache = Type(bool, default=True)
    cache_dir = Type(str, default=".cache/plugin/privacy")

    # Settings for logging
    log = Type(bool, default=True)
    log_level = Choice(LogLevel, default="info")

    # Settings for external assets
    assets = Type(bool, default=True)
    assets_fetch = Type(bool, default=True)
    assets_fetch_dir = Type(str, default="assets/external")
    assets_include = ListOfItems(Type(str), default=[])
    assets_exclude = ListOfItems(Type(str), default=[])
    assets_expr_map = DictOfItems(Type(str), default={})

    # Settings for external links
    links = Type(bool, default=True)
    links_attr_map = DictOfItems(Type(str), default={})
    links_noopener = Type(bool, default=True)

    # Deprecated settings
    external_assets = Deprecated(message="Deprecated, use 'assets_fetch'")
    external_assets_dir = Deprecated(moved_to="assets_fetch_dir")
    external_assets_include = Deprecated(moved_to="assets_include")
    external_assets_exclude = Deprecated(moved_to="assets_exclude")
    external_assets_expr = Deprecated(moved_to="assets_expr_map")
    external_links = Deprecated(moved_to="links")
    external_links_attr_map = Deprecated(moved_to="links_attr_map")
    external_links_noopener = Deprecated(moved_to="links_noopener")

# ---------------------------------------------------------------------------
# Privacy Plugin
# ---------------------------------------------------------------------------

class PrivacyPlugin(BasePlugin[PrivacyConfig]):
    """Privacy plugin - downloads external assets and processes external links."""

    supports_multiple_instances = True

    # -----------------------------------------------------------------------
    # One-time events
    # -----------------------------------------------------------------------

    def on_config(self, config):
        self.site = urlparse(config.site_url or "")
        if not self.config.enabled:
            return

        # Initialize thread pool
        self.pool = ThreadPoolExecutor(self.config.concurrency)
        self.pool_jobs: list[Future] = []

        # Initialize collections of external assets
        self.assets = Files([])
        self.assets_done: list[File] = []
        self.assets_expr_map = {
            ".css": r"url\(\s*([\"']?)(?P<url>(?:https?:)?//[^)'\"]+)\1\s*\)",
            ".js": r"[\"'](?P<url>(?:https?:)?//[^\"']+\.(?:css|js(?:on)?))[\"']",
            **self.config.assets_expr_map
        }

        # Set log level or disable logging altogether
        if not self.config.log:
            log.disabled = True
        else:
            log.setLevel(self.config.log_level.upper())

    # -----------------------------------------------------------------------
    # Global events
    # -----------------------------------------------------------------------

    # Process external style sheets and scripts (run latest)
    @event_priority(-100)
    def on_files(self, files, *, config):
        if not self.config.enabled:
            return

        if not self.config.assets:
            return

        # Find all external style sheet and script files
        for initiator in files.media_files():
            file = None
            for url in self._parse_media(initiator):
                if not self._is_excluded(url, initiator):
                    file = self._queue(url, config, concurrent=True)

                    # Special case: Mermaid.js without site URL
                    if "mermaid.min.js" in url.path and not config.site_url:
                        script = ExtraScriptValue(url.geturl())
                        if script not in config.extra_javascript:
                            config.extra_javascript.append(script)

            if file:
                self.assets.append(initiator)
                files.remove(initiator)

        # Process external style sheet files
        for path in config.extra_css:
            url = urlparse(path)
            if not self._is_excluded(url):
                self._queue(url, config, concurrent=True)

        # Process external script files
        for script in config.extra_javascript:
            if isinstance(script, str):
                script = ExtraScriptValue(script)
            url = urlparse(script.path)
            if not self._is_excluded(url):
                self._queue(url, config, concurrent=True)

    # Process external images in page (run latest)
    @event_priority(-100)
    def on_page_content(self, html, *, page, config, files):
        if not self.config.enabled:
            return

        if not self.config.assets:
            return

        for match in re.findall(
            r"<img[^>]+src=['\"]?(?:https?:)?//[^>]+>",
            html, flags=re.I | re.M
        ):
            el = self._parse_fragment(match)
            url = urlparse(el.get("src"))
            if not self._is_excluded(url, page.file):
                self._queue(url, config, concurrent=True)

    # Reconcile jobs and pass external assets to MkDocs (run earlier)
    @event_priority(50)
    def on_env(self, env, *, config, files):
        if not self.config.enabled:
            return

        wait(self.pool_jobs)
        self.pool_jobs.clear()

        for file in self.assets:
            _, extension = posixpath.splitext(file.dest_uri)
            if extension not in [".css", ".js"]:
                self.assets_done.append(file)
                files.append(file)

    # Process external assets in template (run later)
    @event_priority(-50)
    def on_post_template(self, output_content, *, template_name, config):
        if not self.config.enabled:
            return

        if not template_name.endswith(".html"):
            return

        initiator = File(template_name, config.docs_dir, config.site_dir, False)
        return self._parse_html(output_content, initiator, config)

    # Process external assets in page (run later)
    @event_priority(-50)
    def on_post_page(self, output, *, page, config):
        if not self.config.enabled:
            return

        return self._parse_html(output, page.file, config)

    # Reconcile jobs (run earlier)
    @event_priority(50)
    def on_post_build(self, *, config):
        if not self.config.enabled:
            return

        wait(self.pool_jobs)
        self.pool_jobs.clear()

        for file in self.assets:
            _, extension = posixpath.splitext(file.dest_uri)
            if extension in [".css", ".js"]:
                self.pool_jobs.append(self.pool.submit(self._patch, file))
            elif file not in self.assets_done:
                if os.path.exists(str(file.abs_src_path)):
                    file.copy_file()

        wait(self.pool_jobs)
        self.pool.shutdown()

    # -----------------------------------------------------------------------
    # URL helpers
    # -----------------------------------------------------------------------

    def _is_external(self, url: URL):
        hostname = url.hostname or self.site.hostname
        return hostname != self.site.hostname

    def _is_excluded(self, url: URL, initiator: File | None = None):
        if not self._is_external(url):
            return True

        if not self.config.assets:
            return True

        via = ""
        if initiator:
            via = "".join([
                Fore.WHITE, Style.DIM,
                f"in '{initiator.src_uri}' ",
                Style.RESET_ALL
            ])

        if self.config.assets_include:
            for pattern in self.config.assets_include:
                if fnmatch(self._path_from_url(url), pattern):
                    return False
            log.debug(
                f"Excluding external file '{url.geturl()}' {via}due to "
                f"inclusion patterns"
            )
            return True

        for pattern in self.config.assets_exclude:
            if fnmatch(self._path_from_url(url), pattern):
                log.debug(
                    f"Excluding external file '{url.geturl()}' {via}due to "
                    f"exclusion patterns"
                )
                return True

        if not self.config.assets_fetch:
            log.warning(f"External file: {url.geturl()} {via}")
            return True

        return False

    # -----------------------------------------------------------------------
    # Parsing helpers
    # -----------------------------------------------------------------------

    def _parse_fragment(self, fragment: str):
        parser = FragmentParser()
        parser.feed(fragment)
        parser.close()

        if isinstance(parser.result, Element):
            return parser.result

        raise PluginError(
            "Couldn't parse due to possible syntax error in HTML: \n\n"
            + fragment
        )

    def _parse_media(self, initiator: File) -> list[URL]:
        _, extension = posixpath.splitext(initiator.dest_uri)
        if extension not in self.assets_expr_map:
            return []

        if not initiator.abs_src_path:
            return []

        expr = re.compile(self.assets_expr_map[extension], flags=re.I | re.M)
        with open(initiator.abs_src_path, encoding="utf-8-sig") as f:
            results = re.finditer(expr, f.read())
            return [urlparse(result.group("url")) for result in results]

    def _parse_html(self, output: str, initiator: File, config: DocsForgeConfig):

        def resolve(file: File):
            if is_error_template(initiator.src_uri):
                base = urlparse(config.site_url or "/")
                return posixpath.join(base.path, file.url)
            else:
                return file.url_relative_to(initiator)

        def replace(match: Match):
            el = self._parse_fragment(match.group())

            if self.config.links and el.tag == "a":
                for key, value in self.config.links_attr_map.items():
                    el.set(key, value)

                if self.config.links_noopener:
                    if el.get("target") == "_blank":
                        rel = re.findall(r"\S+", el.get("rel", ""))
                        if "noopener" not in rel:
                            rel.append("noopener")
                        el.set("rel", " ".join(rel))

            if el.tag == "link":
                url = urlparse(el.get("href"))
                if not self._is_excluded(url, initiator):
                    rel = el.get("rel", "")
                    if rel == "preconnect":
                        return ""
                    if rel in ("icon", "preload", "stylesheet"):
                        file = self._queue(url, config)
                        if file:
                            el.set("href", resolve(file))

            if el.tag == "script" or el.tag == "img":
                url = urlparse(el.get("src"))
                if not self._is_excluded(url, initiator):
                    file = self._queue(url, config)
                    if file:
                        el.set("src", resolve(file))

            if el.tag == "image":
                url = urlparse(el.get("href"))
                if not self._is_excluded(url, initiator):
                    file = self._queue(url, config)
                    if file:
                        el.set("href", resolve(file))

            return self._print(el)

        return re.sub(
            r"<(?:(?:a|link|image)[^>]+href|(?:script|img)[^>]+src)=['\"]?(?:https?:)?//[^>]+>",
            replace, output, flags=re.I | re.M
        )

    def _print(self, el: Element):
        temp = "__temp__"
        for name in el.attrib:
            if not isinstance(el.attrib[name], str):
                el.attrib[name] = temp

        data = tostring(el, encoding="unicode")
        return data.replace(" />", ">").replace(f'="{temp}"', "")

    # -----------------------------------------------------------------------
    # Queue / fetch / patch helpers
    # -----------------------------------------------------------------------

    def _queue(self, url: URL, config: DocsForgeConfig, concurrent=False):
        path = self._path_from_url(url)
        full = posixpath.join(self.config.assets_fetch_dir, path)

        file = self.assets.get_file_from_path(full)
        if not file:
            file = self._path_to_file(path, config)
            file.url = url.geturl()

            _, extension = posixpath.splitext(url.path)
            if extension and concurrent:
                self.pool_jobs.append(self.pool.submit(self._fetch, file, config))
            else:
                if not self._fetch(file, config):
                    return None

            if not self.assets.get_file_from_path(file.src_uri):
                self.assets.append(file)

        if url.fragment:
            file.url += f"#{url.fragment}"

        return file

    def _fetch(self, file: File, config: DocsForgeConfig):
        if not os.path.isfile(file.abs_src_path) or not self.config.cache:
            path = file.abs_src_path

            if file.url.startswith("//"):
                file.url = f"http:{file.url}"

            log.info(f"Downloading external file: {file.url}")
            try:
                res = requests.get(
                    file.url,
                    headers={
                        "User-Agent": " ".join([
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                            "AppleWebKit/537.36 (KHTML, like Gecko)",
                            "Chrome/98.0.4758.102 Safari/537.36",
                        ])
                    },
                    timeout=DEFAULT_TIMEOUT_IN_SECS,
                )
                res.raise_for_status()
            except Exception as error:
                log.warning(f"Couldn't retrieve {file.url}: {error}")
                return False

            mime = res.headers["content-type"].split(";")[0]
            extension = extensions.get(mime)
            if extension and not path.endswith(extension):
                path += extension

            self._save_to_file(path, res.content)
            if path != file.abs_src_path:
                try:
                    os.symlink(os.path.basename(path), file.abs_src_path)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        log.warning(f"Couldn't create symbolic link: {file.src_uri}")
                    file.abs_src_path = path

        _, extension = os.path.splitext(file.abs_src_path)
        if os.path.isfile(file.abs_src_path):
            file.abs_src_path = os.path.realpath(file.abs_src_path)
            _, extension = os.path.splitext(file.abs_src_path)
            if not file.abs_dest_path.endswith(extension):
                file.src_uri += extension
                file.dest_uri += extension
                file.abs_dest_path += extension

        file.url = file.dest_uri

        for url in self._parse_media(file):
            if not self._is_excluded(url, file):
                self._queue(url, config, concurrent=True)

        return True

    def _patch(self, initiator: File):
        with open(initiator.abs_src_path, encoding="utf-8-sig") as f:
            def replace(match: Match):
                value = match.group("url")
                path = self._path_from_url(urlparse(value))
                full = posixpath.join(self.config.assets_fetch_dir, path)

                file = self.assets.get_file_from_path(full)
                if not file:
                    name = os.readlink(os.path.join(self.config.cache_dir, full))
                    full = posixpath.join(posixpath.dirname(full), name)
                    file = self.assets.get_file_from_path(full)

                if not file:
                    log.error(
                        "File not found. This is likely a bug in the built-in "
                        "privacy plugin. Please create an issue with a minimal "
                        "reproduction."
                    )
                    sys.exit(1)

                if file.url.endswith(".js"):
                    url = posixpath.join(self.site.geturl(), file.url)
                else:
                    url = file.url_relative_to(initiator)

                return match.group().replace(value, url)

            _, extension = posixpath.splitext(initiator.dest_uri)
            expr = re.compile(self.assets_expr_map[extension], re.I | re.M)
            self._save_to_file(
                initiator.abs_dest_path,
                expr.sub(replace, f.read())
            )

    # -----------------------------------------------------------------------
    # Path helpers
    # -----------------------------------------------------------------------

    def _path_from_url(self, url: URL):
        path = posixpath.normpath(url.path)
        path = re.sub(r"/\.", "/_", path)

        if url.query:
            name, extension = posixpath.splitext(path)
            digest = sha1(url.query.encode("utf-8")).hexdigest()[:8]
            path = f"{name}.{digest}{extension}"

        url = url._replace(scheme="", query="", fragment="", path=path)
        return url.geturl()[2:]

    def _path_to_file(self, path: str, config: DocsForgeConfig):
        return File(
            posixpath.join(self.config.assets_fetch_dir, unquote(path)),
            os.path.abspath(self.config.cache_dir),
            config.site_dir,
            False
        )

    def _save_to_file(self, path: str, content: str | bytes):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if isinstance(content, str):
            content = bytes(content, "utf-8")
        with open(path, "wb") as f:
            f.write(content)
