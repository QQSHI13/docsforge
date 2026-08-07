import subprocess
import os
import logging
from datetime import datetime

log = logging.getLogger(__name__)

# Small cache keyed by file path, invalidated when the file's mtime changes.
_PAGE_INFO_CACHE: dict[str, tuple[float | None, dict | None]] = {}


def _format_git_date(iso_string: str) -> str | None:
    """Format an ISO 8601 git date string to a human-readable form."""
    if not iso_string:
        return None
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime('%b %d, %Y')
    except ValueError:
        return iso_string


def _get_git_page_info(file_path: str) -> dict | None:
    """Uncached git revision info lookup for a documentation page file."""
    try:
        # Check if we're in a git repo by finding the top-level
        cwd = os.path.dirname(file_path) or '.'
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            cwd=cwd, capture_output=True, text=True, check=True, timeout=5
        )
        repo_root = result.stdout.strip()

        # Get relative path from repo root
        rel_path = os.path.relpath(file_path, repo_root)

        # Last updated date
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%cI', '--', rel_path],
            cwd=repo_root, capture_output=True, text=True, check=True, timeout=5
        )
        updated = result.stdout.strip()

        # Creation date (first commit that touched this file)
        result = subprocess.run(
            ['git', 'log', '--follow', '--format=%cI', '--', rel_path],
            cwd=repo_root, capture_output=True, text=True, check=True, timeout=5
        )
        lines = [l for l in result.stdout.strip().split('\n') if l.strip()]
        created = lines[-1] if lines else None

        return {
            'updated': updated,
            'created': created,
            'updated_display': _format_git_date(updated),
            'created_display': _format_git_date(created) if created else None,
        }
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None


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
    try:
        mtime = os.path.getmtime(file_path)
    except OSError:
        mtime = None

    cached = _PAGE_INFO_CACHE.get(file_path)
    if cached is not None and cached[0] == mtime:
        return cached[1]

    result = _get_git_page_info(file_path)
    _PAGE_INFO_CACHE[file_path] = (mtime, result)
    return result
