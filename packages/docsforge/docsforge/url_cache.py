# Copyright (c) 2023 Oleh Prypin <oleh@pryp.in>

from __future__ import annotations

import datetime
import hashlib
import ipaddress
import logging
import os
import random
import urllib.request
from collections.abc import Callable
from urllib.parse import urlparse

import platformdirs
import re

import docsforge

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30


def _is_local_url(url: str) -> bool:
    """Return True for file:// URLs and hosts that are loopback or private."""
    parsed = urlparse(url)
    if parsed.scheme == "file":
        return True
    if parsed.scheme not in ("http", "https"):
        return True
    hostname = parsed.hostname
    if hostname is None:
        return False
    try:
        addr = ipaddress.ip_address(hostname)
        return addr.is_loopback or addr.is_private or addr.is_link_local or addr.is_multicast
    except ValueError:
        # Not an IP address: reject common local hostnames.
        lower = hostname.lower()
        if lower in ("localhost", "localhost.localdomain"):
            return True
        if lower.endswith(".local"):
            return True
    return False


def download_url(url: str) -> bytes:
    if _is_local_url(url):
        raise ValueError(f"Refusing to fetch local URL: {url}")

    req = urllib.request.Request(
        url, headers={"User-Agent": f"docsforge/{docsforge.__version__}"}
    )
    with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
        return resp.read()


def download_and_cache_url(
    url: str,
    cache_duration: datetime.timedelta,
    *,
    download: Callable[[str], bytes] = download_url,
    comment: bytes = b"# ",
) -> bytes:
    """
    Downloads a file from the URL, stores it under ~/.cache/, and returns its content.

    For tracking the age of the content, a prefix is inserted into the stored file, rather than relying on mtime.

    Args:
        url: URL to use.
        download: Callback that will accept the URL and actually perform the download.
        cache_duration: How long to consider the URL content cached.
        comment: The appropriate comment prefix for this file format.
    """
    directory = os.path.join(platformdirs.user_cache_dir("docsforge"), "docsforge_url_cache")
    name_hash = hashlib.sha256(url.encode()).hexdigest()[:32]

    # Sanitize the URL-derived extension so cache paths only contain safe
    # characters and a reasonable length.
    ext = os.path.splitext(url)[1]
    ext = re.sub(r"[^a-zA-Z0-9._-]", "", ext)
    ext = ext[:16]
    path = os.path.join(directory, name_hash + ext)

    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    prefix = b"%s%s downloaded at timestamp " % (comment, url.encode())
    # Check for cached file and try to return it
    if os.path.isfile(path):
        try:
            with open(path, "rb") as f:
                line = f.readline()
                if line.startswith(prefix):
                    line = line[len(prefix) :]
                    timestamp = int(line)
                    if datetime.timedelta(seconds=(now - timestamp)) <= cache_duration:
                        log.debug(f"Using cached '{path}' for '{url}'")
                        return f.read()
        except (OSError, ValueError) as e:
            log.debug(f"{type(e).__name__}: {e}")

    # Download and cache the file
    log.debug(f"Downloading '{url}' to '{path}'")
    content = download(url)
    os.makedirs(directory, exist_ok=True)
    temp_filename = f"{path}.{random.randrange(1 << 32):08x}.part"
    with open(temp_filename, "wb") as f:
        f.write(b"%s%d\n" % (prefix, now))
        f.write(content)
    os.replace(temp_filename, path)
    return content
