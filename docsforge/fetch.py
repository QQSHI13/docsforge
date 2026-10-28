"""Guarded HTTP fetching for URLs that come from untrusted input.

Two plugins download remote bytes during a build, and both were carrying their
own drifting copy of the same guards:

- the privacy plugin vendors every external asset a page points at (the page is
  author-controlled, so a docs PR could otherwise make the build read
  `http://127.0.0.1:port/…` or the cloud metadata address and publish it)
- the social plugin downloads fonts listed in a Google Fonts manifest (a third
  party's response body, cached and fed to `ImageFont`)

This module holds the union of the good behavior in one place: a private/link-
local/loopback/metadata address check, per-hop redirect re-validation (including
an https -> http downgrade block), and a hard cap on both the size and the total
time of the transfer.
"""

from __future__ import annotations

import contextlib
import ipaddress
import socket
import time
from urllib.parse import urljoin, urlparse

import requests

from docsforge.exceptions import PluginError

# A browser-ish user agent: several CDNs serve different (or no) content to
# unknown clients.
USER_AGENT = " ".join([
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "AppleWebKit/537.36 (KHTML, like Gecko)",
    "Chrome/98.0.4758.102 Safari/537.36",
])

# Per-request (connect, read) timeouts. This bounds one socket operation, not
# the transfer as a whole - see `deadline`.
DEFAULT_TIMEOUT = 10
# Hard cap on the total time spent fetching one resource, checked between
# chunks, so a slow-drip server cannot stall a build indefinitely.
DEFAULT_DEADLINE = 60
DEFAULT_MAX_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_REDIRECTS = 5
CHUNK_SIZE = 8192

# Which guard refused or ended the fetch. Callers phrase the same refusal
# differently (an asset vendor vs. a font download), so the reason travels with
# the error instead of being re-derived from its message.
SCHEME = "scheme"
INTERNAL = "internal"
DOWNGRADE = "downgrade"
REDIRECTS = "redirects"
SIZE = "size"
DEADLINE = "deadline"
HTTP = "http"


class FetchError(PluginError):
    """A guarded fetch refused the URL or did not complete.

    A `PluginError` because both callers report a failed fetch as a plugin
    problem (a skipped asset, a skipped card) rather than aborting the build.
    """

    def __init__(self, message: str, *, kind: str = HTTP) -> None:
        super().__init__(message)
        self.kind = kind


def is_internal_host(hostname: str | None) -> bool:
    """True when *hostname* resolves to a non-public address.

    Every resolved address is checked, not just the first: a host with both a
    public and a private A record must still be rejected. An unresolvable host
    is NOT treated as internal - the request fails on its own terms instead of
    reporting a misleading "internal host" error. A missing hostname is
    treated as internal, since it cannot be validated at all.
    """
    if not hostname:
        return True
    try:
        infos = socket.getaddrinfo(hostname, None)
    except (socket.gaierror, UnicodeError):
        return False
    for info in infos:
        address = info[4][0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            continue
        if ip.version == 6 and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return True
    return False


def fetch_bytes(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    deadline: float = DEFAULT_DEADLINE,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    session=None,
    response_headers: dict[str, str] | None = None,
) -> bytes:
    """Download *url* and return its body, or raise :class:`FetchError`.

    The initial URL and *every* redirect hop are validated: plain http(s) only,
    never a private/loopback/metadata address, and never an https -> http
    downgrade. Redirects are followed by hand for exactly that reason - once
    `requests` follows them itself, the hop it took is no longer visible.

    The body is streamed, so `max_bytes` (a larger response is refused as soon
    as it is exceeded) and `deadline` (seconds of wall clock for the whole
    transfer) are enforced rather than merely advertised. `timeout` bounds a
    single socket operation underneath.

    Pass *session* to fetch through an existing `requests` session (connection
    reuse); without one, the module-level `requests.get` is used. If
    *response_headers* is given, the final response's headers are copied into
    it - callers that need the content type to name the downloaded file use it.
    """
    get = requests.get if session is None else session.get

    end = time.monotonic() + deadline
    current = url
    for _hop in range(max_redirects + 1):
        _validate(current)
        if time.monotonic() > end:
            raise FetchError(f"Fetching {current} exceeded {deadline}s", kind=DEADLINE)
        try:
            res = get(
                current,
                headers={"User-Agent": USER_AGENT},
                timeout=(timeout, timeout),
                stream=True,
                allow_redirects=False,
            )
        except Exception as error:
            raise FetchError(f"Couldn't retrieve {current}: {error}") from error

        try:
            location = _redirect_target(res, current, max_redirects)
            if location is not None:
                current = location
                continue
            try:
                res.raise_for_status()
            except Exception as error:
                raise FetchError(f"Couldn't retrieve {current}: {error}") from error
            if response_headers is not None:
                response_headers.update(res.headers)
            return _read_body(res, current, max_bytes, end, deadline)
        finally:
            # Always release the connection, including on the early exits
            # above; iter_content() consumed the stream, so res.content is
            # unavailable afterwards.
            with contextlib.suppress(Exception):
                res.close()

    raise FetchError(f"Too many redirects retrieving {url}", kind=REDIRECTS)


def _validate(url: str) -> None:
    """Refuse a URL that must not be requested at all, before any I/O."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise FetchError(f"Unsupported URL scheme: {url}", kind=SCHEME)
    if is_internal_host(parsed.hostname):
        raise FetchError(
            f"Refusing to fetch internal address: {url}", kind=INTERNAL
        )


def _redirect_target(res, current: str, max_redirects: int) -> str | None:
    """Return the validated next hop, or None when *res* is a final response."""
    if not (res.is_redirect or res.is_permanent_redirect):
        return None
    next_url = urljoin(current, res.headers.get("location", ""))
    if urlparse(current).scheme == "https" and urlparse(next_url).scheme == "http":
        raise FetchError(
            f"Redirect downgraded https to http, blocked: {current} -> {next_url}",
            kind=DOWNGRADE,
        )
    return next_url


def _read_body(res, url: str, max_bytes: int, end: float, deadline: float) -> bytes:
    """Stream the response body, bounded in size and in wall-clock time."""
    length = res.headers.get("content-length")
    if length:
        try:
            if int(str(length).strip()) > max_bytes:
                raise FetchError(f"Response too large: {url}", kind=SIZE)
        except ValueError:
            # Malformed content-length: the streaming cap below still bounds
            # the download.
            pass

    body = bytearray()
    for chunk in res.iter_content(chunk_size=CHUNK_SIZE):
        if not chunk:
            continue
        body.extend(chunk)
        if len(body) > max_bytes:
            raise FetchError(f"Response too large: {url}", kind=SIZE)
        if time.monotonic() > end:
            raise FetchError(f"Fetching {url} exceeded {deadline}s", kind=DEADLINE)
    return bytes(body)
