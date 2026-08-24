from __future__ import annotations

import io
import json
import logging
import os
import socket
import sys
from collections.abc import Callable
from os.path import isfile, join
from typing import TYPE_CHECKING, BinaryIO
from urllib.parse import urlsplit

from docsforge.build import build
from docsforge.config_base import load_config
from docsforge.livereload import LiveReloadServer, _serve_url

if TYPE_CHECKING:
    from docsforge.config_defaults import DocsForgeConfig

log = logging.getLogger(__name__)


def _find_available_port(host: str, start_port: int, max_attempts: int = 20) -> int:
    """Find an available port starting from start_port, incrementing until one works."""
    import ipaddress
    # Use the correct address family for the host (IPv4 vs IPv6)
    try:
        is_v6 = isinstance(ipaddress.ip_address(host), ipaddress.IPv6Address)
        family = socket.AF_INET6 if is_v6 else socket.AF_INET
    except ValueError:
        family = socket.AF_INET

    for port in range(start_port, start_port + max_attempts):
        with socket.socket(family, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)  # Prevent WSL firewall hangs (dropped SYN packets)
            try:
                result = s.connect_ex((host, port))
            except (TimeoutError, OSError):
                # Port is likely available but firewall drops the probe
                return port
            if result != 0:
                return port
    raise RuntimeError(f"No available port found in range {start_port}-{start_port + max_attempts - 1}")


def serve(
    config_file: str | BinaryIO | None = None,
    livereload: bool = False,
    watch_theme: bool = False,
    watch: list[str] | None = None,
    *,
    host: str | None = None,
    open_in_browser: bool = True,
    **kwargs,
) -> None:
    """
    Start the DocsForge development server.

    By default it will serve the documentation on http://localhost:8000/.
    When ``livereload`` is enabled, it will rebuild the documentation
    automatically whenever a file is edited (the page must be refreshed
    manually).

    The dev server uses the configured ``site_dir`` exactly like
    ``docsforge build`` so that builds are incremental and caches are reused.
    """
    get_config_file: Callable[[], str | BinaryIO | None]
    if config_file is None or isinstance(config_file, str):
        def get_config_file() -> str | BinaryIO | None:
            return config_file
    elif sys.stdin and config_file is sys.stdin.buffer:
        # Stdin must be read only once, can't be reopened later.
        config_file_content = sys.stdin.buffer.read()

        def get_config_file() -> str | BinaryIO | None:
            return io.BytesIO(config_file_content)
    else:
        # If closed file descriptor, reopen it through the file path instead.
        def get_config_file() -> str | BinaryIO | None:
            return config_file.name if getattr(config_file, "closed", False) else config_file

    # Cache loaded config by config-file mtime so incremental serve rebuilds
    # don't pay the ~1-2s config-loading cost every time.
    _config_cache: dict[str, tuple[float | None, DocsForgeConfig]] = {}
    _watch_applied: set[int] = set()

    def get_config():
        cf = get_config_file()
        if isinstance(cf, str):
            try:
                mtime = os.path.getmtime(cf)
            except OSError:
                mtime = None
            cached = _config_cache.get(cf)
            if cached is not None and cached[0] == mtime:
                config = cached[1]
            else:
                config = load_config(config_file=cf, **kwargs)
                _config_cache[cf] = (mtime, config)
        else:
            # BinaryIO (e.g. stdin) cannot be cached by mtime; reload each time.
            config = load_config(config_file=cf, **kwargs)

        # Extend watch list only once per config object to avoid duplicates.
        if id(config) not in _watch_applied:
            config.watch.extend(watch or [])
            _watch_applied.add(id(config))
        return config

    config = get_config()
    config.plugins.on_startup(command="serve", dirty=True)

    config_host, config_port = config.dev_addr
    host = host or config_host
    port = _find_available_port(host, config_port)
    if port != config_port:
        log.info(f"Port {config_port} is in use, using port {port} instead")
    mount_path = urlsplit(config.site_url or "/").path

    # Use localhost for the display URL when binding to all interfaces.
    display_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    config.site_url = serve_url = _serve_url(display_host, port, mount_path)

    def builder(config: DocsForgeConfig | None = None):
        log.info("Building documentation...")
        if config is None:
            config = get_config()
            config.site_url = serve_url

        try:
            build(config, serve_url=serve_url, dirty=True)
        except Exception as e:
            log.error(f"Build error: {e}")
            log.error("Documentation will continue to be served. Fix the error and the page will auto-reload.")

    server = LiveReloadServer(
        builder=builder, host=host, port=port, root=config.site_dir, mount_path=mount_path
    )
    server.url = serve_url

    def error_handler(code) -> bytes | None:
        if code in (404, 500):
            error_page = join(config.site_dir, f"{code}.html")
            if isfile(error_page):
                try:
                    with open(error_page, "rb") as f:
                        return f.read()
                except OSError as e:
                    log.debug(f"Could not read error page {error_page}: {e}")
                    return None
        return None

    server.error_handler = error_handler

    # Path for the pidfile, used in both try and finally
    pidfile_dir = os.path.dirname(config.config_file_path) if config.config_file_path else os.getcwd()
    pidfile_path = os.path.join(pidfile_dir, ".docsforge", "server.json")
    os.makedirs(os.path.join(pidfile_dir, ".docsforge"), exist_ok=True)

    try:
        # Perform the initial build
        log.info("Preparing initial build...")
        try:
            builder(config)
        except Exception as e:
            log.error(f"Initial build error: {e}")
            log.error("Server will continue running. Fix errors and reload.")

        if livereload:
            # Watch the documentation files, the config file and the theme files.
            server.watch(config.docs_dir)
            if config.config_file_path:
                server.watch(config.config_file_path)

            if watch_theme:
                for d in config.theme.dirs:
                    if os.path.exists(d):
                        server.watch(d)
                    else:
                        log.debug(f"Skipping watch for non-existent theme dir: {d}")

            # Run `serve` plugin events.
            server = config.plugins.on_serve(server, config=config, builder=builder)

            for item in config.watch:
                if os.path.exists(item):
                    server.watch(item)
                else:
                    log.debug(f"Skipping watch for non-existent path: {item}")

        # Write pidfile BEFORE serve() blocks — it must be visible immediately
        try:
            with open(pidfile_path, "w") as f:
                json.dump({
                    "pid": os.getpid(),
                    "url": serve_url,
                    "project_dir": pidfile_dir,
                }, f)
        except Exception:
            pass

        server.serve(open_in_browser=open_in_browser)

    except KeyboardInterrupt:
        log.info("Shutting down...")
        sys.exit(0)
    finally:
        server.shutdown()
        config.plugins.on_shutdown()
        # Clean up pidfile
        try:
            if os.path.isfile(pidfile_path):
                os.remove(pidfile_path)
        except Exception:
            pass
