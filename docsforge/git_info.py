import concurrent.futures
import logging
import os
import subprocess
import threading
from datetime import datetime

log = logging.getLogger(__name__)

# Small cache keyed by file path, invalidated when the file's mtime changes.
_PAGE_INFO_CACHE: dict[str, tuple[float | None, dict | None]] = {}
_PAGE_INFO_LOCK = threading.Lock()

# Memoized `git rev-parse --show-toplevel` per start directory: the repo root
# is constant within a build, so per-page lookups must not re-spawn git.
# None means the directory sits outside any repo.
_REPO_ROOT_CACHE: dict[str, str | None] = {}

# Cap for the prefetch worker pool (S1): history walks are fork+exec and
# diff-CPU heavy, so this tracks machine size instead of page count.
def _prefetch_workers() -> int:
    return max(2, min(8, os.cpu_count() or 2))


def _format_git_date(iso_string: str) -> str | None:
    """Format an ISO 8601 git date string to a human-readable form."""
    if not iso_string:
        return None
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except ValueError:
        return iso_string


def _repo_root(start_dir: str) -> str | None:
    """Return the repo root for a start directory, spawning rev-parse at most once."""
    if start_dir in _REPO_ROOT_CACHE:
        return _REPO_ROOT_CACHE[start_dir]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start_dir, capture_output=True, text=True, check=True, timeout=5
        )
        root: str | None = os.path.realpath(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        root = None
    _REPO_ROOT_CACHE[start_dir] = root
    return root


def _get_git_page_info(file_path: str) -> dict | None:
    """Uncached git revision info lookup for a documentation page file."""
    try:
        # Check if we're in a git repo by finding the top-level
        cwd = os.path.dirname(file_path) or "."
        repo_root = _repo_root(cwd)
        if repo_root is None:
            return None

        # Get relative path from repo root. realpath both sides so symlinks
        # don't skew the relative computation and make git log match nothing.
        rel_path = os.path.relpath(os.path.realpath(file_path), repo_root)

        # Creation date (first commit that touched this file)
        # One `--follow` walk serves both dates: its first line is the
        # newest touching commit, which always equals `git log -1` for the
        # same path (verified across all docs/demo pages, including renames
        # and copies) — so no second walk is needed for `updated`.
        result = subprocess.run(
            ["git", "log", "--follow", "--format=%cI", "--", rel_path],
            cwd=repo_root, capture_output=True, text=True, check=True, timeout=5
        )
        lines = [line for line in result.stdout.strip().split("\n") if line.strip()]
        updated = lines[0] if lines else ""
        created = lines[-1] if lines else None

        return {
            "updated": updated,
            "created": created,
            "updated_display": _format_git_date(updated),
            "created_display": _format_git_date(created) if created else None,
        }
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None


def _resolve_and_cache(file_path: str) -> dict | None:
    """Compute one page's info through the mtime cache (thread-safe)."""
    try:
        mtime = os.path.getmtime(file_path)
    except OSError:
        mtime = None
    with _PAGE_INFO_LOCK:
        cached = _PAGE_INFO_CACHE.get(file_path)
        if cached is not None and cached[0] == mtime:
            return cached[1]
    result = _get_git_page_info(file_path)
    with _PAGE_INFO_LOCK:
        _PAGE_INFO_CACHE[file_path] = (mtime, result)
    return result


def prefetch_git_page_info(file_paths: list[str]) -> None:
    """Warm the git-info cache for many pages concurrently (S1).

    A full build needs dates for every rendered page; walking histories one
    by one costs ~100ms per page serially. The walks are independent blocking
    subprocess calls, so a small bounded pool cuts wall time ~8x. Every entry
    goes through the exact same per-file git commands as a lazy lookup, so
    output is identical with or without prefetching — only speed changes.
    Files already fresh in the mtime cache are skipped (no git at all).
    """
    todo = []
    for path in dict.fromkeys(file_paths):
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = None
        with _PAGE_INFO_LOCK:
            cached = _PAGE_INFO_CACHE.get(path)
            if cached is not None and cached[0] == mtime:
                continue
        todo.append(path)
    if not todo:
        return
    workers = min(_prefetch_workers(), len(todo))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(_resolve_and_cache, todo))


def get_git_page_info(file_path: str) -> dict | None:
    """Get git revision info for a documentation page file.

    Returns a dict with:
        - updated: ISO date of last commit
        - created: ISO date of first commit
        - updated_display: Human-readable last update date
        - created_display: Human-readable creation date

    Returns None if the file is not in a git repository or git is not available.

    The result is cached per path and invalidated when the file's mtime changes.
    """
    return _resolve_and_cache(file_path)
