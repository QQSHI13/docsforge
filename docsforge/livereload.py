from __future__ import annotations

import contextlib
import ipaddress
import logging
import os
import os.path
import pathlib
import posixpath
import socket
import socketserver
import sys
import threading
import time
import traceback
import urllib.parse
import webbrowser
import wsgiref.simple_server
import wsgiref.util
from collections.abc import Callable, Iterable
from typing import Any, BinaryIO, ClassVar

import watchdog.events
import watchdog.observers
import watchdog.observers.polling


class _LoggerAdapter(logging.LoggerAdapter):
    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:  # type: ignore[override]
        return time.strftime("[%H:%M:%S] ") + msg, kwargs


log = _LoggerAdapter(logging.getLogger(__name__), {})


def _normalize_mount_path(mount_path: str) -> str:
    """Ensure the mount path starts and ends with a slash."""
    return ("/" + mount_path.lstrip("/")).rstrip("/") + "/"


def _serve_url(host: str, port: int, path: str) -> str:
    return f"http://{host}:{port}{_normalize_mount_path(path)}"


class LiveReloadServer(socketserver.ThreadingMixIn, wsgiref.simple_server.WSGIServer):
    daemon_threads = True

    def __init__(
        self,
        builder: Callable[[], None],
        host: str,
        port: int,
        root: str,
        mount_path: str = "/",
        polling_interval: float = 0.5,
        shutdown_delay: float = 0.25,
    ) -> None:
        self.builder = builder
        try:
            if isinstance(ipaddress.ip_address(host), ipaddress.IPv6Address):
                self.address_family = socket.AF_INET6
        except Exception:
            pass
        self.root = os.path.abspath(root)
        self.mount_path = _normalize_mount_path(mount_path)
        self.url = _serve_url(host, port, mount_path)
        self.build_delay = 0.1
        self.shutdown_delay = shutdown_delay
        # To allow custom error pages.
        self.error_handler: Callable[[int], bytes | None] = lambda code: None

        super().__init__((host, port), _Handler, bind_and_activate=False)
        self.set_app(self.serve_request)

        self._wanted_epoch = _timestamp()  # The version of the site that started building.
        self._visible_epoch = self._wanted_epoch  # Latest fully built version of the site.
        self._epoch_cond = threading.Condition()  # Must be held when accessing _visible_epoch.

        self._want_rebuild: bool = False
        self._rebuilding: bool = False
        self._pending_rebuild: bool = False
        self._rebuild_cond = threading.Condition()  # Must be held when accessing _want_rebuild.

        self._shutdown = False
        self.serve_thread = threading.Thread(target=lambda: self.serve_forever(shutdown_delay), daemon=True)
        try:
            # Prefer the native observer (inotify/FSEvents/...); polling is slow and CPU-heavy.
            self.observer = watchdog.observers.Observer()
        except Exception:
            log.warning("Native file-system observer unavailable, falling back to PollingObserver", exc_info=True)
            self.observer = watchdog.observers.polling.PollingObserver(timeout=polling_interval)
        self.observer.daemon = True

        self._watched_paths: dict[str, int] = {}
        self._watch_refs: dict[str, Any] = {}

        # Cheap guard against editors that rewrite a file without changing its
        # content. Maps absolute path -> (mtime_ns, size). Only consulted for
        # ``modified`` events, because create/delete/move are real changes.
        self._last_seen: dict[str, tuple[int, int]] = {}

    def watch(self, path: str, func: None = None, *, recursive: bool = True) -> None:
        """Add the 'path' to watched paths and call the builder when any file changes under it."""
        path = os.path.abspath(path)
        if not (func is None or func is self.builder):  # type: ignore[unreachable]
            raise TypeError("Plugins can no longer pass a 'func' parameter to watch().")

        if path in self._watched_paths:
            self._watched_paths[path] += 1
            return
        self._watched_paths[path] = 1

        handler = watchdog.events.FileSystemEventHandler()
        handler.on_any_event = self._on_file_event  # type: ignore[method-assign]
        log.debug(f"Watching '{path}'")
        self._watch_refs[path] = self.observer.schedule(handler, path, recursive=recursive)

    # Editor and tool artifacts that should never trigger a rebuild.
    _IGNORED_SUFFIXES = frozenset({
        "~",          # nano/emacs backup files
        ".swp",       # vim swap files
        ".swo",       # vim swap files
        ".swx",       # vim swap files
        ".tmp",       # generic temp files
        ".bak",       # generic backup files
        ".part",      # partial downloads
    })
    _IGNORED_NAMES = frozenset({
        ".#",         # emacs lock files (prefix)
        "#",          # emacs auto-save files (prefix)
        ".gitignore",
        ".gitkeep",
    })
    _IGNORED_DIR_SEGMENTS = frozenset({
        ".git",
        ".docsforge",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "venv",
        "node_modules",
        ".cache",
        "site",       # build output directory
    })

    def _is_ignored_event(self, event) -> bool:
        """Return True if the event targets an editor temp/backup/cache file."""
        path = getattr(event, "src_path", "")
        if not path:
            return False

        # Normalize to a pathlib object for component checks.
        try:
            p = pathlib.Path(path)
        except Exception:
            return False

        # Ignore events inside known cache/build/tool directories.
        parts = set(p.parts)
        if parts & self._IGNORED_DIR_SEGMENTS:
            return True

        name = p.name

        # Emacs lock files: .#filename and #filename#
        if name.startswith(".#"):
            return True
        if name.startswith("#") and name.endswith("#"):
            return True

        if name in self._IGNORED_NAMES:
            return True

        suffix = p.suffix.lower()
        if suffix in self._IGNORED_SUFFIXES:
            return True

        # Files whose entire stem looks like a backup, e.g. "file~" (nano).
        # The suffix check above catches "file.md~" because p.suffix is "~";
        # this catches "file~" without an extension.
        if name.endswith("~"):
            return True

        # Hidden files in general are often editor metadata; be conservative.
        return name.startswith(".")

    def _content_unchanged(self, event) -> bool:
        """Return True if a modified event did not actually change file content."""
        if event.event_type != "modified":
            return False
        path = getattr(event, "src_path", "")
        if not path:
            return False
        try:
            stat = os.stat(path)
            key = (stat.st_mtime_ns, stat.st_size)
            prev = self._last_seen.get(path)
            self._last_seen[path] = key
            return prev == key
        except (OSError, ValueError):
            return False

    def _on_file_event(self, event) -> None:
        """Handle a file-change event from the watcher.

        If a build is in progress, queue the change (``_pending_rebuild``) so it
        fires once afterward instead of racing the current build. Otherwise
        signal the build loop to rebuild.
        """
        if event.is_directory:
            return
        # Ignore read-only events. On Linux, simply reading a file emits
        # IN_OPEN/IN_CLOSE_NOWRITE events; treating them as changes causes
        # the build itself to trigger an endless rebuild loop.
        if event.event_type not in ("created", "modified", "moved", "deleted"):
            log.debug(f"Ignoring non-modifying event: {event}")
            return
        if self._is_ignored_event(event):
            log.debug(f"Ignoring editor/temp/cache event: {event}")
            return
        if self._content_unchanged(event):
            log.debug(f"Ignoring no-op modification: {event}")
            return
        log.debug(str(event))
        with self._rebuild_cond:
            if self._rebuilding:
                self._pending_rebuild = True
                return
            self._want_rebuild = True
            self._rebuild_cond.notify_all()

    def unwatch(self, path: str) -> None:
        """Stop watching file changes for path. Raises if there was no corresponding `watch` call."""
        path = os.path.abspath(path)

        self._watched_paths[path] -= 1
        if self._watched_paths[path] <= 0:
            self._watched_paths.pop(path)
            self.observer.unschedule(self._watch_refs.pop(path))

    def serve(self, *, open_in_browser=False):
        self.server_bind()
        self.server_activate()

        if self._watched_paths:
            self.observer.start()

            paths_str = ", ".join(f"'{_try_relativize_path(path)}'" for path in self._watched_paths)
            log.info(f"Watching paths for changes: {paths_str}")

        if open_in_browser:
            log.info(f"Serving on {self.url} and opening it in a browser")
        else:
            log.info(f"Serving on {self.url}")
        self.serve_thread.start()
        if open_in_browser:
            webbrowser.open(self.url)

        self._build_loop()

    def _build_loop(self):
        while True:
            with self._rebuild_cond:
                while not self._rebuild_cond.wait_for(
                    lambda: self._want_rebuild or self._shutdown, timeout=self.shutdown_delay
                ):
                    # We could have used just one wait instead of a loop + timeout, but we need
                    # occasional breaks, otherwise on Windows we can't receive KeyboardInterrupt.
                    pass
                if self._shutdown:
                    break
                log.info("Detected file changes")
                while self._rebuild_cond.wait(timeout=self.build_delay):
                    log.debug("Waiting for file changes to stop happening")

                self._wanted_epoch = _timestamp()
                self._want_rebuild = False

            try:
                self._rebuilding = True
                self.builder()
            except BaseException as e:
                if isinstance(e, SystemExit):
                    print(e, file=sys.stderr)
                else:
                    traceback.print_exc()
                log.error(
                    "An error happened during the rebuild. The server will continue serving the last successful build."
                )
                # Roll back the wanted epoch so requests waiting on the
                # condition variable are unblocked instead of blocking forever.
                with self._epoch_cond:
                    self._wanted_epoch = self._visible_epoch
                continue
            finally:
                self._rebuilding = False
                # If events were queued during rebuild, trigger a new rebuild
                with self._rebuild_cond:
                    if self._pending_rebuild:
                        self._pending_rebuild = False
                        self._want_rebuild = True

            with self._epoch_cond:
                self._visible_epoch = self._wanted_epoch
                self._epoch_cond.notify_all()

    def shutdown(self, wait=False) -> None:
        with self._rebuild_cond:
            self._shutdown = True
            self._rebuild_cond.notify_all()

        if self.serve_thread.is_alive():
            super().shutdown()
        self.server_close()
        if wait:
            with contextlib.suppress(Exception):
                self.observer.stop()
            self.serve_thread.join(timeout=1)
            with contextlib.suppress(Exception):
                self.observer.join(timeout=1)

    def serve_request(self, environ, start_response) -> Iterable[bytes]:
        try:
            result = self._serve_request(environ, start_response)
        except Exception:
            code = 500
            msg = "500 Internal Server Error"
            log.exception(msg)
        else:
            if result is not None:
                return result
            code = 404
            msg = "404 Not Found"

        error_content = None
        try:
            error_content = self.error_handler(code)
        except Exception:
            log.exception("Failed to render an error message!")
        if error_content is None:
            error_content = msg.encode()

        start_response(msg, [("Content-Type", "text/html")])
        return [error_content]

    def _resolve_within_root(self, rel_file_path: str) -> str | None:
        """Resolve a request-relative path to an absolute path inside the site root.

        Returns ``None`` if the result would escape the root. This is the only
        place request-controlled input becomes a filesystem path, so all
        containment reasoning lives here:

        1. ``normpath("/" + rel)`` collapses every ``..`` segment against the
           leading slash, so ``../../etc/passwd`` flattens to ``etc/passwd``
           before it is ever joined to the root. The ``lstrip("/")`` then makes
           it relative so ``join`` cannot be hijacked by an absolute path.
        2. Any ``..`` surviving normalization is rejected outright. This is a
           no-op for legitimate URLs (step 1 removes them all) and a belt-and-
           braces guard against platform-specific normalization quirks.
        3. ``realpath`` resolves symlinks, and the result must equal the root or
           sit beneath ``root + os.sep``. The separator matters: without it a
           sibling directory sharing the root's name prefix (``/site`` vs
           ``/sitezz``) would pass a bare ``startswith``.
        """
        rel_file_path = posixpath.normpath("/" + rel_file_path).lstrip("/")

        if rel_file_path == ".." or rel_file_path.startswith(("../", "..\\")):
            return None
        if "/../" in rel_file_path or "\\..\\" in rel_file_path:
            return None

        base = os.path.realpath(self.root)
        file_path = os.path.realpath(os.path.join(base, rel_file_path))
        if file_path != base and not file_path.startswith(base + os.sep):
            return None
        return file_path

    def _serve_request(self, environ, start_response) -> Iterable[bytes] | None:
        # https://bugs.python.org/issue16679
        # https://github.com/bottlepy/bottle/blob/f9b1849db4/bottle.py#L984
        path = environ["PATH_INFO"].encode("latin-1").decode("utf-8", "ignore")

        # The request path is reflected into response headers; reject CR/LF so
        # it can never split them (HTTP response splitting).
        if "\r" in path or "\n" in path:
            return None

        # Handle browser probes before mount path routing
        if path.startswith("/.well-known/"):
            # Chrome DevTools, etc. — return empty JSON silently
            start_response("200 OK", [("Content-Type", "application/json")])
            return [b"{}"]

        if (path + "/").startswith(self.mount_path):
            rel_file_path = path[len(self.mount_path) :]

            if path.endswith("/"):
                rel_file_path += "index.html"
            # Prevent directory traversal. The guarded value is what every
            # filesystem operation below uses.
            resolved = self._resolve_within_root(rel_file_path)
            if resolved is None:
                return None
            file_path = resolved
        elif path == "/":
            start_response("302 Found", [("Location", urllib.parse.quote(self.mount_path))])
            return []
        else:
            return None  # Not found

        # Wait until the ongoing rebuild (if any) finishes, so we're not serving a half-built site.
        with self._epoch_cond:
            self._epoch_cond.wait_for(lambda: self._visible_epoch == self._wanted_epoch)

        try:
            # Deliberately left open: FileWrapper streams it to the client and
            # closes it when the response finishes.
            file: BinaryIO = open(file_path, "rb")  # noqa: SIM115
        except OSError:
            if not path.endswith("/") and os.path.isfile(os.path.join(file_path, "index.html")):
                # Percent-encode everything (safe="") so the header value can
                # never carry CR/LF or other header syntax.
                start_response("302 Found", [("Location", urllib.parse.quote(path, safe="") + "/")])
                return []
            return None  # Not found

        content_length = os.path.getsize(file_path)

        content_type = self._guess_type(file_path)
        start_response(
            "200 OK", [("Content-Type", content_type), ("Content-Length", str(content_length))]
        )
        return wsgiref.util.FileWrapper(file)

    # Hermetic content-type map. Values are constants — the request path only
    # ever selects a key, so the emitted header can't be influenced by the URL
    # (no response splitting) and the server has no OS mime database to depend on.
    _CONTENT_TYPES: ClassVar[dict[str, str]] = {
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".gz": "application/gzip",
        ".html": "text/html",
        ".htm": "text/html",
        ".css": "text/css",
        ".json": "application/json",
        ".map": "application/json",
        ".xml": "application/xml",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".ttf": "font/ttf",
        ".otf": "font/otf",
        ".eot": "application/vnd.ms-fontobject",
        ".pdf": "application/pdf",
        ".zip": "application/zip",
        ".wasm": "application/wasm",
        ".mp3": "audio/mpeg",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
    }

    @classmethod
    def _guess_type(cls, path):
        suffix = os.path.splitext(path)[1].lower()
        return cls._CONTENT_TYPES.get(suffix, "application/octet-stream")


class _Handler(wsgiref.simple_server.WSGIRequestHandler):
    def log_request(self, code="-", size="-"):
        level = logging.DEBUG if str(code) in ("200", "301", "302", "304") else logging.ERROR
        log.log(level, f'"{self.requestline}" code {code}')

    def log_message(self, format, *args):
        log.debug(format, *args)


def _timestamp() -> int:
    return round(time.monotonic() * 1000)


def _try_relativize_path(path: str) -> str:
    """Make the path relative to current directory if it's under that directory."""
    p = pathlib.Path(path)
    with contextlib.suppress(ValueError):
        p = p.relative_to(os.getcwd())
    return str(p)
