"""Privacy plugin - external asset downloading and link processing."""

from __future__ import annotations

import contextlib
import errno
import logging
import os
import posixpath
import re
import threading
import time
from concurrent.futures import Future, wait
from concurrent.futures.thread import ThreadPoolExecutor
from fnmatch import fnmatch
from hashlib import sha1
from html.parser import HTMLParser
from re import Match
from urllib.parse import ParseResult as URL
from urllib.parse import unquote, urljoin, urlparse
from xml.etree.ElementTree import Element, tostring

import requests
from colorama import Fore, Style

from docsforge import is_error_template
from docsforge.config_base import Config
from docsforge.config_defaults import DEFAULT_CONCURRENCY, DocsForgeConfig
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
MAX_DOWNLOAD_SIZE = 16 * 1024 * 1024  # 16 MiB
# Hard cap on total time spent streaming one asset, so a slow-drip server
# cannot stall the build indefinitely (the per-socket timeout alone does not
# bound the overall transfer).
MAX_DOWNLOAD_TIME = 30
# Maximum number of redirects followed for a single external asset.
MAX_REDIRECTS = 5

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

def _is_remote_url(url: str) -> bool:
    """Whether a File url still points at the remote origin (fetch pending)."""
    return url.startswith(("http://", "https://", "//"))


class PrivacyConfig(Config):
    """Privacy plugin configuration."""

    enabled = Type(bool, default=True)

    # Settings for caching
    cache = Type(bool, default=True)
    cache_dir = Type(str, default=".docsforge/cache/privacy")

    # Settings for logging
    log = Type(bool, default=True)
    log_level = Choice(LogLevel, default="info")

    # Settings for external assets
    assets = Type(bool, default=True)
    assets_fetch = Type(bool, default=True)
    assets_fetch_dir = Type(str, default="assets/external")
    assets_include = ListOfItems(Type(str), default=[])
    assets_exclude = ListOfItems(Type(str), default=[])
    """fnmatch globs deciding which external assets are fetched+vendored.

    Each pattern is tried against the normalized `host/path` and against
    the bare hostname — so `*/mathjax/*` matches by path while
    `*.clouddn.com` or `oayoilchh.bkt.clouddn.com` match by host.
    Excluded URLs are left as remote links, never downloaded. When
    `assets_include` is non-empty it acts as an allowlist (only matching
    assets are fetched).
    """
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

    # Sized by the global `concurrency` setting in on_config; fallback until then.
    _concurrency: int = DEFAULT_CONCURRENCY

    # -----------------------------------------------------------------------
    # Pool lifecycle
    # -----------------------------------------------------------------------

    def _get_pool(self) -> ThreadPoolExecutor:
        """Return the thread pool, creating it on first use.

        The executor is built WITHOUT the jobs lock held: construction
        submits a wakeup handshake to its own worker thread, and a worker
        that immediately grabs the jobs lock (submitting nested downloads)
        would otherwise deadlock with the constructor waiting for that
        handshake.
        """
        if self.pool is not None:
            return self.pool
        candidate = ThreadPoolExecutor(self._concurrency)
        with self._jobs_lock:
            if self.pool is None:
                self.pool = candidate
                return self.pool
        candidate.shutdown(wait=False, cancel_futures=True)
        return self.pool

    def _drain_jobs(self) -> None:
        """Wait for queued jobs until quiescent, surfacing failures as warnings.

        Jobs may queue further jobs while we wait (nested CSS/JS URLs), so
        loop until no jobs remain. Each future's result is consumed so
        exceptions are logged instead of silently dropped.
        """
        while True:
            with self._jobs_lock:
                jobs = list(self.pool_jobs)
                self.pool_jobs.clear()
            if not jobs:
                break
            wait(jobs)
            for f in jobs:
                try:
                    f.result()
                except Exception as e:
                    log.warning(f"External asset job failed: {e}")
        # Drop settled futures so the registry only tracks in-flight work;
        # later lookups re-derive state from the files on disk.
        with self._jobs_lock:
            for full, fut in list(self._futures.items()):
                if fut.done():
                    self._futures.pop(full, None)

    # -----------------------------------------------------------------------
    # One-time events
    # -----------------------------------------------------------------------

    def on_config(self, config):
        self.site = urlparse(config.site_url or "")
        # Global `concurrency` setting sizes the download pool.
        self._concurrency = config.concurrency
        if not hasattr(self, "_jobs_lock"):
            self._jobs_lock = threading.Lock()
        if not self.config.enabled:
            return

        # Serve reuses this plugin instance across rebuilds, and an
        # interrupted build never reaches on_post_build (where the pool is
        # normally shut down). Reap any leaked pool here instead of
        # abandoning its threads. Never wait: workers may be stuck in
        # network I/O with their own timeouts; queued jobs are cancelled.
        old_pool = getattr(self, "pool", None)
        if old_pool is not None:
            with contextlib.suppress(Exception):
                old_pool.shutdown(wait=False, cancel_futures=True)

        # Resolve cache_dir relative to the project root (config file directory)
        # so cached external assets are reused regardless of the current working
        # directory from which docsforge is invoked.
        cache_dir = self.config["cache_dir"]
        if not os.path.isabs(cache_dir):
            project_dir = os.path.dirname(config.config_file_path or "") or os.getcwd()
            cache_dir = os.path.normpath(os.path.join(project_dir, cache_dir))
            self.config["cache_dir"] = cache_dir

        # Thread pool is created lazily: if a site has no external assets,
        # we avoid the cost of starting and shutting down worker threads.
        self.pool: ThreadPoolExecutor | None = None
        self.pool_jobs: list[Future] = []
        if not hasattr(self, "_jobs_lock"):
            self._jobs_lock = threading.Lock()

        # Initialize collections of external assets
        self.assets = Files([])
        self.assets_done: list[File] = []
        # full fetch path -> Future owning its download. A synchronous rewrite
        # must wait for a pending pre-warm job instead of racing it: the job's
        # File still carries the remote URL until its fetch completes, and
        # rewriting HTML to that URL produces garbage like `/https://...`.
        self._futures: dict[str, Future] = {}
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

    def on_shutdown(self) -> None:
        """Stop the download pool promptly so Ctrl-C exits immediately.

        Workers blocked in network I/O finish on their own socket timeouts;
        queued (not yet started) downloads are cancelled instead of joined.
        Without this, interrupting `serve` during the initial build leaves
        pool threads alive and the interpreter hangs joining them until
        every download times out on its own.
        """
        lock = getattr(self, "_jobs_lock", None)
        if lock is not None:
            with lock:
                self.pool_jobs = []
        else:
            self.pool_jobs = []
        pool = getattr(self, "pool", None)
        self.pool = None
        if pool is not None:
            with contextlib.suppress(Exception):
                pool.shutdown(wait=False, cancel_futures=True)

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
                with self._jobs_lock:
                    if not self.assets.get_file_from_path(initiator.src_uri):
                        self.assets.append(initiator)
                files.remove(initiator)

        # Process external style sheet files
        for path in config.extra_css:
            url = urlparse(path)
            if not self._is_excluded(url):
                self._queue(url, config, concurrent=True)

        # Process external script files
        for entry in config.extra_javascript:
            script = ExtraScriptValue(entry) if isinstance(entry, str) else entry
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
            html, flags=re.IGNORECASE | re.MULTILINE
        ):
            el = self._parse_fragment(match)
            url = urlparse(el.get("src"))
            if not self._is_excluded(url, page.file):
                self._queue(url, config, concurrent=True)

    # Reconcile jobs and pass external assets to the build (run earlier)
    @event_priority(50)
    def on_env(self, env, *, config, files):
        if not self.config.enabled:
            return

        self._drain_jobs()

        with self._jobs_lock:
            assets_snapshot = list(self.assets)
        for file in assets_snapshot:
            _, extension = posixpath.splitext(file.dest_uri)
            if extension not in [".css", ".js"]:
                if not os.path.exists(str(file.abs_src_path)):
                    # Download failed or the cache was wiped after the file
                    # was queued — skip it so copy_static_files never sees a
                    # dangling source. The next build re-downloads it.
                    log.warning(f"Skipping unavailable external asset: {file.src_uri}")
                    continue
                self.assets_done.append(file)
                files.append(file)

    # Process external assets in template (run later)
    @event_priority(-50)
    def on_post_template(self, output_content, *, template_name, config):
        if not self.config.enabled:
            return None

        if not template_name.endswith(".html"):
            return None

        initiator = File(template_name, config.docs_dir, config.site_dir, False)
        return self._parse_html(output_content, initiator, config)

    # Process external assets in page (run later)
    @event_priority(-50)
    def on_post_page(self, output, *, page, config):
        if not self.config.enabled:
            return None

        return self._parse_html(output, page.file, config)

    # Reconcile jobs (run earlier)
    @event_priority(50)
    def on_post_build(self, *, config):
        if not self.config.enabled:
            return

        self._drain_jobs()

        # First pass: discover nested URLs in downloaded CSS/JS files
        # (e.g., font files referenced inside Google Fonts CSS)
        with self._jobs_lock:
            assets_snapshot = list(self.assets)
        for file in assets_snapshot:
            _, extension = posixpath.splitext(file.dest_uri)
            if extension in [".css", ".js"]:
                for url in self._parse_media(file):
                    if not self._is_excluded(url, file):
                        self._queue(url, config, concurrent=True)

        # Wait for nested downloads
        self._drain_jobs()

        # Second pass: patch CSS/JS files with local URLs and copy remaining assets
        with self._jobs_lock:
            assets_snapshot = list(self.assets)
        for file in assets_snapshot:
            _, extension = posixpath.splitext(file.dest_uri)
            if extension in [".css", ".js"]:
                pool = self._get_pool()
                with self._jobs_lock:
                    self.pool_jobs.append(pool.submit(self._patch, file))
            elif file not in self.assets_done and os.path.exists(str(file.abs_src_path)):
                file.copy_file()

        self._drain_jobs()
        pool = self.pool
        self.pool = None
        if pool is not None:
            with contextlib.suppress(Exception):
                pool.shutdown(wait=False, cancel_futures=True)

    # -----------------------------------------------------------------------
    # URL helpers
    # -----------------------------------------------------------------------

    def _is_external(self, url: URL):
        hostname = url.hostname or self.site.hostname
        return hostname != self.site.hostname

    def _match_candidates(self, url: URL) -> list[str]:
        """Strings a pattern may match against: host/path and bare host.

        `_path_from_url` yields `host/normalized-path`, so path globs keep
        working; adding the bare hostname lets users exclude whole hosts
        (`*.clouddn.com`) instead of guessing path prefixes.
        """
        candidates = [self._path_from_url(url)]
        if url.hostname:
            candidates.append(url.hostname)
        return candidates

    def _matches_any(self, url: URL, patterns) -> bool:
        candidates = self._match_candidates(url)
        return any(
            fnmatch(candidate, pattern)
            for candidate in candidates
            for pattern in patterns
        )

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
            if self._matches_any(url, self.config.assets_include):
                return False
            log.debug(
                f"Excluding external file '{url.geturl()}' {via}due to "
                f"inclusion patterns"
            )
            return True

        for pattern in self.config.assets_exclude:
            if self._matches_any(url, [pattern]):
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

        if not initiator.abs_src_path or not os.path.isfile(initiator.abs_src_path):
            return []

        expr = re.compile(self.assets_expr_map[extension], flags=re.IGNORECASE | re.MULTILINE)
        try:
            with open(initiator.abs_src_path, encoding="utf-8-sig") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError) as e:
            log.warning(f"Skipping unparsable file {initiator.src_uri}: {e}")
            return []
        results = re.finditer(expr, content)
        return [urlparse(result.group("url")) for result in results]

    def _parse_html(self, output: str, initiator: File, config: DocsForgeConfig):

        def resolve(file: File):
            if is_error_template(initiator.src_uri):
                base = urlparse(config.site_url or "/")
                return posixpath.join(base.path, file.url)
            return file.url_relative_to(initiator)

        def replace(match: Match):
            el = self._parse_fragment(match.group())

            if self.config.links and el.tag == "a":
                for key, value in self.config.links_attr_map.items():
                    el.set(key, value)

                if self.config.links_noopener and el.get("target") == "_blank":
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

            if el.tag in {"script", "img"}:
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
            replace, output, flags=re.IGNORECASE | re.MULTILINE
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

        with self._jobs_lock:
            file = self.assets.get_file_from_path(full)
            fut = self._futures.get(full)
        if fut is not None and not fut.done():
            if concurrent:
                # Pre-warm only: a job is already running, nothing to rewrite.
                return file
            # A rewrite needs the real outcome — wait for the owning job.
            # Returning the pending File would rewrite HTML to its still-
            # remote URL (`/https://...` garbage), and if the job then fails
            # the garbage is permanent. Afterwards fall through to the
            # readiness gate, which retries synchronously on failure.
            try:
                fut.result(
                    timeout=MAX_DOWNLOAD_TIME + 2 * DEFAULT_TIMEOUT_IN_SECS + 5
                )
            except Exception:
                log.debug(f"Timed out waiting for pending fetch of '{full}'")
            with self._jobs_lock:
                self._futures.pop(full, None)
                file = self.assets.get_file_from_path(full)
        elif fut is not None:
            with self._jobs_lock:
                self._futures.pop(full, None)

        if file is not None and not _is_remote_url(file.url):
            # Landed: local destination already resolved.
            return self._with_fragment(file, url)

        if file is None:
            file = self._path_to_file(path, config)
            file.url = url.geturl()
            with self._jobs_lock:
                # Another thread may have queued the same URL while we
                # were creating the File; prefer the existing entry.
                existing = self.assets.get_file_from_path(full)
                if existing is not None:
                    file = existing
                elif not self.assets.get_file_from_path(file.src_uri):
                    self.assets.append(file)

        if concurrent:
            # Best-effort pre-warm: submit unless a job owns this URL, and
            # never rewrite here — the synchronous pass decides that later.
            # Build the pool BEFORE taking the jobs lock: the executor
            # constructor joins a worker-handshake, and that worker needs
            # the jobs lock if it submits nested downloads — nesting the
            # constructor inside this lock deadlocked both threads.
            pool = self._get_pool()
            with self._jobs_lock:
                pending = self._futures.get(full)
                if pending is None or pending.done():
                    self._futures[full] = pool.submit(self._fetch, file, config)
                    self.pool_jobs.append(self._futures[full])
            return file

        # Queued but never landed (failed pre-warm): fetch synchronously.
        # The isfile check inside _fetch makes this a no-op when another
        # job just wrote the file; otherwise this is the per-build retry.
        if not self._fetch(file, config):
            # Forget the dead entry so later lookups retry instead of
            # reusing this remote-URL object.
            with self._jobs_lock, contextlib.suppress(ValueError):
                self.assets.remove(file)
            return None
        with self._jobs_lock:
            if not self.assets.get_file_from_path(file.src_uri):
                self.assets.append(file)
        return self._with_fragment(file, url)

    def _with_fragment(self, file: File, url: URL) -> File:
        if url.fragment:
            with self._jobs_lock:
                if not file.url.endswith(f"#{url.fragment}"):
                    file.url += f"#{url.fragment}"
        return file

    def _fetch(self, file: File, config: DocsForgeConfig):
        if not os.path.isfile(file.abs_src_path) or not self.config.cache:
            if file.url.startswith("//"):
                file.url = f"http:{file.url}"

            parsed = urlparse(file.url)
            if parsed.scheme not in ("http", "https"):
                log.warning(f"Unsupported URL scheme for external file: {file.url}")
                return False

            log.info(f"Downloading external file: {file.url}")
            res = None
            try:
                # Validate redirects manually so a https:// asset can never be
                # silently downgraded to http://, and so a redirect cannot
                # escape to an unsupported scheme.
                current_url = file.url
                for _ in range(MAX_REDIRECTS + 1):
                    res = requests.get(
                        current_url,
                        headers={
                            "User-Agent": " ".join([
                                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                                "AppleWebKit/537.36 (KHTML, like Gecko)",
                                "Chrome/98.0.4758.102 Safari/537.36",
                            ])
                        },
                        timeout=(DEFAULT_TIMEOUT_IN_SECS, DEFAULT_TIMEOUT_IN_SECS),
                        stream=True,
                        allow_redirects=False,
                    )
                    if res.is_redirect or res.is_permanent_redirect:
                        location = res.headers.get("location", "")
                        res.close()
                        res = None
                        next_url = urljoin(current_url, location)
                        parsed_next = urlparse(next_url)
                        if parsed_next.scheme not in ("http", "https"):
                            log.warning(f"Redirect to unsupported scheme blocked: {file.url} -> {next_url}")
                            return False
                        if urlparse(current_url).scheme == "https" and parsed_next.scheme == "http":
                            log.warning(f"Redirect downgraded https to http, blocked: {file.url} -> {next_url}")
                            return False
                        current_url = next_url
                        continue
                    break
                else:
                    log.warning(f"Too many redirects retrieving {file.url}")
                    return False
            except Exception as error:
                if res is not None:
                    with contextlib.suppress(Exception):
                        res.close()
                log.warning(f"Couldn't retrieve {file.url}: {error}")
                return False

            try:
                res.raise_for_status()
            except Exception as error:
                with contextlib.suppress(Exception):
                    res.close()
                log.warning(f"Couldn't retrieve {file.url}: {error}")
                return False

            # Validate the final URL after any redirects resolved.
            parsed_final = urlparse(res.url) if hasattr(res, "url") else urlparse(current_url)
            if parsed_final.scheme not in ("http", "https"):
                with contextlib.suppress(Exception):
                    res.close()
                log.warning(f"Unsupported URL scheme for external file: {file.url}")
                return False

            # Enforce a response size cap while streaming, plus a hard overall
            # deadline so a slow-drip server cannot stall the build forever.
            content_length = res.headers.get("content-length")
            if content_length:
                try:
                    if int(str(content_length).strip()) > MAX_DOWNLOAD_SIZE:
                        with contextlib.suppress(Exception):
                            res.close()
                        log.warning(f"External file too large: {file.url}")
                        return False
                except ValueError:
                    # Ignore malformed content-length; the streaming cap below
                    # still bounds the download.
                    pass

            chunks: list[bytes] = []
            total_size = 0
            download_deadline = time.monotonic() + MAX_DOWNLOAD_TIME
            try:
                for chunk in res.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    chunks.append(chunk)
                    total_size += len(chunk)
                    if total_size > MAX_DOWNLOAD_SIZE:
                        log.warning(f"External file too large: {file.url}")
                        return False
                    if time.monotonic() > download_deadline:
                        log.warning(f"Download timed out: {file.url}")
                        return False
            finally:
                # Always release the connection back to the pool, including
                # on the early-return paths above. iter_content() consumed
                # the stream, so res.content is unavailable here.
                res.close()
            content = b"".join(chunks)

            mime = res.headers.get("content-type", "").split(";")[0]
            extension = extensions.get(mime)

            # Save with content-based hash for cache busting
            download_base = file.abs_src_path
            if extension and not download_base.endswith(extension):
                download_base += extension

            content_hash = sha1(content).hexdigest()[:12]
            base, ext = os.path.splitext(download_base)
            hashed_path = f"{base}.{content_hash}{ext}"

            self._save_to_file(hashed_path, content)

            # Symlink from file.abs_src_path to the content-hashed file
            # so URL-based lookups resolve correctly.
            link_target = os.path.basename(hashed_path)
            if hashed_path != file.abs_src_path:
                try:
                    os.symlink(link_target, file.abs_src_path)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        log.warning(f"Couldn't create symbolic link: {file.src_uri}")
                    # Write the already-streamed bytes. `res.content` is not
                    # available here: iter_content above consumed the stream, so
                    # touching it raises RuntimeError.
                    self._save_to_file(file.abs_src_path, content)
                    hashed_path = file.abs_src_path

            # NOTE: the destination URI keeps the *unhashed* name on purpose.
            # The content-hashed file lives only in the cache (referenced by a
            # symlink at the unhashed path). If we propagated the content hash
            # into dest_uri, the URL written into patched CSS/HTML would flip
            # between hashed (fresh download) and unhashed (cache hit) across
            # builds, so the referenced name and the copied file would disagree
            # and produce 404s for fonts/emojis. Keeping dest_uri unhashed makes
            # referenced name == copied file on every build. Cache invalidation
            # is handled by the service-worker build hash + cache manifest.

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
        if not os.path.isfile(initiator.abs_src_path):
            log.debug(f"Skipping patch for unavailable file: {initiator.src_uri}")
            return
        try:
            with open(initiator.abs_src_path, encoding="utf-8-sig") as f:
                raw = f.read()
        except (OSError, UnicodeDecodeError) as e:
            log.warning(f"Skipping patch for unreadable file {initiator.src_uri}: {e}")
            return
        def replace(match: Match):
            value = match.group("url")
            path = self._path_from_url(urlparse(value))
            full = posixpath.join(self.config.assets_fetch_dir, path)

            file = self.assets.get_file_from_path(full)
            if not file:
                try:
                    name = os.readlink(os.path.join(self.config.cache_dir, full))
                    full = posixpath.join(posixpath.dirname(full), name)
                    file = self.assets.get_file_from_path(full)
                except (OSError, FileNotFoundError):
                    log.warning(f"Skipping unavailable asset: {full}")
                    return match.group()

            if not file:
                log.warning(f"Skipping unavailable asset (not in cache): {full}")
                return match.group()

            if file.url.endswith(".js"):
                url = posixpath.join(self.site.geturl(), file.url)
            else:
                url = file.url_relative_to(initiator)

            return match.group().replace(value, url)

        _, extension = posixpath.splitext(initiator.dest_uri)
        if extension not in self.assets_expr_map:
            return
        expr = re.compile(self.assets_expr_map[extension], re.IGNORECASE | re.MULTILINE)
        self._save_to_file(
            initiator.abs_dest_path,
            expr.sub(replace, raw)
        )

    # -----------------------------------------------------------------------
    # Path helpers
    # -----------------------------------------------------------------------

    def _path_from_url(self, url: URL):
        path = url.path or "/"
        # Reject traversal attempts before normalization
        if any(part == ".." for part in path.split("/")):
            raise PluginError(
                f"External asset URL contains traversal: {url.geturl()}"
            )

        path = posixpath.normpath(path)
        # Strip leading slashes so the local path is always relative and cannot
        # be interpreted as an absolute filesystem path.
        path = path.lstrip("/")

        # Only replace /. when followed by / (current dir .) or end-of-string,
        # not /.icons or other valid dot-prefixed directories.
        path = re.sub(r"/\.(?=/|$)", "/_", path)

        if url.query:
            name, extension = posixpath.splitext(path)
            digest = sha1(url.query.encode("utf-8")).hexdigest()[:8]
            path = f"{name}.{digest}{extension}"

        url = url._replace(scheme="", query="", fragment="", path=path)
        return url.geturl()[2:]

    def _is_within(self, path: str, base: str) -> bool:
        """Return True if *path* is inside *base* after resolving symlinks."""
        try:
            return os.path.commonpath([path, base]) == base
        except ValueError:
            return False

    def _path_to_file(self, path: str, config: DocsForgeConfig):
        base = os.path.abspath(self.config.cache_dir)
        src_uri = posixpath.join(self.config.assets_fetch_dir, unquote(path))
        abs_src_path = os.path.abspath(os.path.join(base, src_uri))
        if not self._is_within(abs_src_path, base):
            raise PluginError(
                f"External asset path escapes cache directory: {path}"
            )

        return File(
            src_uri,
            base,
            config.site_dir,
            False
        )

    def _save_to_file(self, path: str, content: str | bytes):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if isinstance(content, str):
            content = bytes(content, "utf-8")
        with open(path, "wb") as f:
            f.write(content)
