from __future__ import annotations

import io
import json
import logging
import os
import shutil
import socket
import sys
import tempfile
from collections.abc import Callable
from os.path import isdir, isfile, join
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
        if isinstance(ipaddress.ip_address(host), ipaddress.IPv6Address):
            family = socket.AF_INET6
        else:
            family = socket.AF_INET
    except ValueError:
        family = socket.AF_INET

    for port in range(start_port, start_port + max_attempts):
        with socket.socket(family, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)  # Prevent WSL firewall hangs (dropped SYN packets)
            try:
                result = s.connect_ex((host, port))
            except (socket.timeout, OSError):
                # Port is likely available but firewall drops the probe
                return port
            if result != 0:
                return port
    raise RuntimeError(f"No available port found in range {start_port}-{start_port + max_attempts - 1}")


def serve(
    config_file: str | BinaryIO | None = None,
    livereload: bool = False,
    watch_theme: bool = False,
    watch: list[str] = [],
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
    """
    # Create a temporary build directory, and set some options to serve it
    site_dir = tempfile.mkdtemp(prefix='docsforge_')

    get_config_file: Callable[[], str | BinaryIO | None]
    if config_file is None or isinstance(config_file, str):
        get_config_file = lambda: config_file
    elif sys.stdin and config_file is sys.stdin.buffer:
        # Stdin must be read only once, can't be reopened later.
        config_file_content = sys.stdin.buffer.read()
        get_config_file = lambda: io.BytesIO(config_file_content)
    else:
        # If closed file descriptor, reopen it through the file path instead.
        get_config_file = lambda: (
            config_file.name if getattr(config_file, 'closed', False) else config_file
        )

    def get_config():
        config = load_config(
            config_file=get_config_file(),
            site_dir=site_dir,
            **kwargs,
        )
        config.watch.extend(watch)
        return config

    config = get_config()
    config.plugins.on_startup(command='serve', dirty=True)

    config_host, config_port = config.dev_addr
    host = host or config_host
    port = _find_available_port(host, config_port)
    if port != config_port:
        log.info(f"Port {config_port} in use, using port {port} instead")
    mount_path = urlsplit(config.site_url or '/').path
    config.site_url = serve_url = _serve_url(host, port, mount_path)

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
        builder=builder, host=host, port=port, root=site_dir, mount_path=mount_path
    )

    def error_handler(code) -> bytes | None:
        if code in (404, 500):
            error_page = join(site_dir, f'{code}.html')
            if isfile(error_page):
                with open(error_page, 'rb') as f:
                    return f.read()
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
                    server.watch(d)

            # Run `serve` plugin events.
            server = config.plugins.on_serve(server, config=config, builder=builder)

            for item in config.watch:
                server.watch(item)

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
        if isdir(site_dir):
            shutil.rmtree(site_dir)
        # Clean up pidfile
        try:
            if os.path.isfile(pidfile_path):
                os.remove(pidfile_path)
        except Exception:
            pass
