from __future__ import annotations

import contextlib
import functools
import ipaddress
import logging
import mimetypes
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
from typing import Any, BinaryIO

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

    def _on_file_event(self, event) -> None:
        """Handle a file-change event from the watcher.

        If a build is in progress, queue the change (``_pending_rebuild``) so it
        fires once afterward instead of racing the current build. Otherwise
        signal the build loop to rebuild.
        """
        if event.is_directory:
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
                    print(e, file=sys.stderr)  # noqa: T201
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
            try:
                self.observer.stop()
            except Exception:
                pass
            self.serve_thread.join(timeout=1)
            try:
                self.observer.join(timeout=1)
            except Exception:
                pass

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

    def _serve_request(self, environ, start_response) -> Iterable[bytes] | None:
        # https://bugs.python.org/issue16679
        # https://github.com/bottlepy/bottle/blob/f9b1849db4/bottle.py#L984
        path = environ["PATH_INFO"].encode("latin-1").decode("utf-8", "ignore")

        # Handle browser probes before mount path routing
        if path.startswith("/.well-known/"):
            # Chrome DevTools, etc. — return empty JSON silently
            start_response("200 OK", [("Content-Type", "application/json")])
            return [b"{}"]

        if (path + "/").startswith(self.mount_path):
            rel_file_path = path[len(self.mount_path) :]

            if path.endswith("/"):
                rel_file_path += "index.html"
            # Prevent directory traversal - normalize the path.
            rel_file_path = posixpath.normpath("/" + rel_file_path).lstrip("/")
            file_path = os.path.join(self.root, rel_file_path)
        elif path == "/":
            start_response("302 Found", [("Location", urllib.parse.quote(self.mount_path))])
            return []
        else:
            return None  # Not found

        # Wait until the ongoing rebuild (if any) finishes, so we're not serving a half-built site.
        with self._epoch_cond:
            self._epoch_cond.wait_for(lambda: self._visible_epoch == self._wanted_epoch)

        try:
            file: BinaryIO = open(file_path, "rb")
        except OSError:
            if not path.endswith("/") and os.path.isfile(os.path.join(file_path, "index.html")):
                start_response("302 Found", [("Location", urllib.parse.quote(path) + "/")])
                return []
            return None  # Not found

        content_length = os.path.getsize(file_path)

        content_type = self._guess_type(file_path)
        start_response(
            "200 OK", [("Content-Type", content_type), ("Content-Length", str(content_length))]
        )
        return wsgiref.util.FileWrapper(file)

    @classmethod
    def _guess_type(cls, path):
        # DocsForge only ensures a few common types (as seen in livereload_tests.py::test_mime_types).
        # Other uncommon types will not be accepted.
        if path.endswith((".js", ".JS", ".mjs")):
            return "application/javascript"
        if path.endswith(".gz"):
            return "application/gzip"

        guess, _ = mimetypes.guess_type(path)
        if guess:
            return guess
        return "application/octet-stream"


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
