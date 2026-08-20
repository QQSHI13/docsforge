"""DocsForge incremental build cache - tracks file hashes and dependencies for dirty builds."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

log = logging.getLogger(__name__)

CACHE_DIR = Path(".docsforge/cache")
CACHE_VERSION = 1

# Match pymdownx.snippets include lines: `--8<-- "path"` and `-8<-- 'path'`.
# The "tear here" marker may be one or two leading dashes; the path may be
# quoted or bare, and may carry a trailing line range (e.g. `file:5,10`).
_SNIPPET_INCLUDE_RE = re.compile(
    r'^[ \t]*-{1,2}8<--[ \t]*["\']?(?P<path>[^"\'\n:#]+)(?:[:#][^"\'\n]*)?["\']?[ \t]*$',
    re.MULTILINE,
)


class FileHasher:
    """Compute SHA-256 hashes of files."""

    @staticmethod
    def hash_file(path: Path) -> str:
        """Compute SHA-256 hash of a file's content."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def hash_string(content: str) -> str:
        """Compute SHA-256 hash of a string."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


class CacheManager:
    """Read and write build cache files."""

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.hashes_file = cache_dir / "hashes.json"
        self.deps_file = cache_dir / "deps.json"
        self.config_hash_file = cache_dir / "config_hash"
        self.version_file = cache_dir / "version"
        self.sources_file = cache_dir / "sources.json"
        self.meta_file = cache_dir / "meta.json"
        self.pkg_version_file = cache_dir / "pkg_version"
        self.theme_sig_file = cache_dir / "theme_sig"
        self.nav_sig_file = cache_dir / "nav_sig"
        self.validation_file = cache_dir / "validation.json"
        self.tikz_file = cache_dir / "tikz.json"

    def _read_json(self, path: Path) -> dict[str, Any]:
        """Read JSON file, return empty dict if missing."""
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            log.warning(f"Corrupted cache file: {path}, rebuilding from scratch")
            return {}

    def _write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON file atomically."""
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        tmp.replace(path)

    def get_hashes(self) -> dict[str, str]:
        """Get cached file hashes."""
        return self._read_json(self.hashes_file)

    def set_hashes(self, hashes: dict[str, str]) -> None:
        """Save file hashes to cache."""
        self._write_json(self.hashes_file, hashes)

    def get_deps(self) -> dict[str, list[str]]:
        """Get cached dependency graph."""
        return self._read_json(self.deps_file)

    def set_deps(self, deps: dict[str, list[str]]) -> None:
        """Save dependency graph to cache."""
        self._write_json(self.deps_file, deps)

    def get_config_hash(self) -> str | None:
        """Get cached config hash."""
        if self.config_hash_file.exists():
            return self.config_hash_file.read_text().strip()
        return None

    def set_config_hash(self, hash: str) -> None:
        """Save config hash to cache."""
        self.config_hash_file.write_text(hash)

    def get_version(self) -> int:
        """Get cache format version."""
        if self.version_file.exists():
            try:
                return int(self.version_file.read_text().strip())
            except ValueError:
                return 0
        return 0

    def set_version(self, version: int) -> None:
        """Save cache format version."""
        self.version_file.write_text(str(version))

    def get_sources(self) -> list[str]:
        """Get the set of source URIs from the last build."""
        return self._read_json(self.sources_file).get("sources", [])

    def set_sources(self, sources: list[str]) -> None:
        """Save the set of source URIs for this build."""
        self._write_json(self.sources_file, {"sources": sorted(sources)})

    def get_meta(self) -> dict[str, dict]:
        """Get the {path: {mtime, size, hash}} cache for fast re-hashing."""
        return self._read_json(self.meta_file)

    def set_meta(self, meta: dict[str, dict]) -> None:
        """Save the mtime/size/hash metadata."""
        self._write_json(self.meta_file, meta)

    def get_validation(self) -> dict[str, dict]:
        """Get the per-source link/anchor validation cache.

        Each entry: {warnings: [[level, msg], ...], links: {target_uri:
        {anchor: url}}, anchors: [id, ...]} — persisted so link problems are
        re-reported on incremental builds even when a page isn't re-rendered.
        """
        return self._read_json(self.validation_file)

    def set_validation(self, validation: dict[str, dict]) -> None:
        """Save the per-source link/anchor validation cache."""
        self._write_json(self.validation_file, validation)

    def get_tikz_hashes(self) -> dict[str, str]:
        """Get the {tex path: source hash} cache for TikZ diagram rebuilds."""
        return self._read_json(self.tikz_file)

    def set_tikz_hashes(self, hashes: dict[str, str]) -> None:
        """Save the {tex path: source hash} cache for TikZ diagram rebuilds."""
        self._write_json(self.tikz_file, hashes)

    def get_pkg_version(self) -> str | None:
        """Get the docsforge version that produced this cache."""
        if self.pkg_version_file.exists():
            return self.pkg_version_file.read_text().strip() or None
        return None

    def set_pkg_version(self, version: str) -> None:
        """Save the docsforge version for this cache."""
        self.pkg_version_file.write_text(version)

    def get_theme_sig(self) -> str | None:
        """Get the theme-template signature from the last build."""
        if self.theme_sig_file.exists():
            return self.theme_sig_file.read_text().strip() or None
        return None

    def set_theme_sig(self, sig: str) -> None:
        """Save the theme-template signature for this build."""
        self.theme_sig_file.write_text(sig)

    def get_nav_sig(self) -> str | None:
        """Get the navigation signature from the last build."""
        if self.nav_sig_file.exists():
            return self.nav_sig_file.read_text().strip() or None
        return None

    def set_nav_sig(self, sig: str) -> None:
        """Save the navigation signature for this build."""
        self.nav_sig_file.write_text(sig)

    def invalidate(self) -> None:
        """Clear all cache files tracked by the manager."""
        for f in [
            self.hashes_file,
            self.deps_file,
            self.config_hash_file,
            self.version_file,
            self.sources_file,
            self.meta_file,
            self.pkg_version_file,
            self.theme_sig_file,
            self.nav_sig_file,
            self.tikz_file,
        ]:
            if f.exists():
                f.unlink()
        log.info("Build cache invalidated")


class DependencyTracker:
    """Track which files depend on templates and config."""

    GLOBAL_DEPS = [
        "docsforge.yml",
        "docsforge.yaml",
    ]

    @staticmethod
    def get_file_deps(
        source_path: Path,
        content: str | None = None,
        base_paths: list[Path] | None = None,
    ) -> list[str]:
        """Extract snippet-include dependencies from markdown source.

        Tracks ``pymdownx.snippets`` includes (``--8<-- "path"``). The
        rendered HTML (``page.content``) cannot be used because the markers
        are consumed during ``md.convert()``; callers must pass the raw
        markdown (``page.markdown``) or leave ``content`` None to read the
        source file from disk.

        Include paths are resolved against a list of candidate base
        directories, because ``pymdownx.snippets`` resolves relative to its
        configured ``base_path`` (docsforge does not set one, so the default
        is the current working directory, i.e. the project root). We also try
        the docs_dir and the source file's own directory as a fallback. Only
        existing files are returned, so a non-matching resolution is a safe
        no-op (the page simply isn't tracked for that include).

        Absolute includes (e.g. ``--8<-- "/etc/passwd"``) are rejected, and a
        resolved path must stay under the base directory it resolved against,
        so ``../..`` traversal cannot escape the project's include roots.
        Otherwise arbitrary files outside the project would be tracked (and
        hashed) as dependencies.
        """
        if content is None:
            try:
                content = source_path.read_text(encoding="utf-8")
            except OSError:
                return []

        # Candidate base directories, in priority order.
        bases: list[Path] = []
        if base_paths:
            bases.extend(base_paths)
        bases.append(source_path.parent)  # source file's own directory
        bases.append(Path.cwd())           # pymdownx.snippets default base_path is ["."]

        deps: list[str] = []
        seen: set[str] = set()
        for match in _SNIPPET_INCLUDE_RE.finditer(content):
            target = match.group('path').strip()
            if not target:
                continue
            # Reject absolute includes (e.g. --8<-- "/etc/passwd"): they would
            # point outside the project's include roots. Checked for both
            # POSIX and Windows semantics so the guard is platform-independent.
            if PurePosixPath(target).is_absolute() or PureWindowsPath(target).is_absolute():
                continue
            for base in bases:
                resolved = (base / target).resolve()
                # The resolved path must stay under the base it resolved
                # against, otherwise `../..` traversal could track (and hash)
                # arbitrary files outside the project.
                if not resolved.is_relative_to(base.resolve()):
                    continue
                key = str(resolved)
                if key in seen:
                    break
                if resolved.is_file():
                    seen.add(key)
                    deps.append(key)
                    break
        return deps

    @staticmethod
    def get_global_deps() -> list[str]:
        """Get list of files that affect all pages."""
        return [p for p in DependencyTracker.GLOBAL_DEPS if Path(p).exists()]


class BuildPlanner:
    """Decide which files need rebuilding."""

    def __init__(self, cache: CacheManager, hasher: FileHasher):
        self.cache = cache
        self.hasher = hasher
        self.hashes = cache.get_hashes()
        self.deps = cache.get_deps()
        self.config_hash = cache.get_config_hash()
        self.pkg_version = cache.get_pkg_version()
        self.theme_sig = cache.get_theme_sig()
        self.nav_sig = cache.get_nav_sig()
        # {path: {mtime, size, hash}} — lets us skip re-reading+hashing a file
        # whose mtime+size are unchanged since last build.
        self.meta = cache.get_meta()
        # {source: {warnings, links, anchors}} — link/anchor validation data
        # persisted so problems are re-reported on incremental builds.
        self.validation = cache.get_validation()

    def theme_signature(self, dirs) -> str:
        """Content hash of all .html/.xml templates in the theme dirs.

        A change triggers a full rebuild so edits to base.html, a partial, or
        a custom_dir template propagate to every page. Only .html/.xml are
        tracked (rendering-affecting); the 14k+ .icons/ and asset directories
        are skipped by globbing for the exact suffixes. Content hashing (not
        mtimes) keeps the signature stable across git checkouts and CI cache
        restores — and across re-installs of the docsforge package, which
        stamp fresh mtimes on identical files.
        """
        import hashlib
        items = []
        seen = set()
        for d in dirs:
            dpath = Path(d)
            key = dpath.resolve()
            if key in seen or not dpath.is_dir():
                continue
            seen.add(key)
            for pattern in ('*.html', '*.xml'):
                for p in dpath.rglob(pattern):
                    try:
                        data = p.read_bytes()
                    except OSError:
                        continue
                    items.append((str(p), hashlib.sha256(data).hexdigest()[:16]))
        items.sort()
        h = hashlib.sha256()
        for path, digest in items:
            h.update(f"{path}|{digest}".encode())
        return h.hexdigest()[:16]

    def _current_hash(self, path: Path) -> str:
        """Hash a file, reusing the cached hash if mtime+size are unchanged.

        This avoids re-reading the file on every build when it hasn't changed
        — a stat() is enough. mtime+size collision is astronomically unlikely
        for a real edit.
        """
        try:
            st = path.stat()
        except OSError:
            return ""
        key = str(path)
        cached = self.meta.get(key)
        if (
            cached
            and cached.get("mtime") == st.st_mtime_ns
            and cached.get("size") == st.st_size
        ):
            return cached["hash"]
        h = self.hasher.hash_file(path)
        self.meta[key] = {"mtime": st.st_mtime_ns, "size": st.st_size, "hash": h}
        return h

    def should_rebuild(self, source: Path, output: Path) -> bool:
        """Check if a source file needs rebuilding.
        
        Returns True if:
        - Output doesn't exist
        - Source hash changed
        - Any dependency changed
        - Config changed
        """
        # 1. Output doesn't exist
        if not output.exists():
            return True

        # 2. Source file changed or missing
        if not source.exists():
            return True

        current_source_hash = self._current_hash(source)
        cached_source_hash = self.hashes.get(str(source))
        if cached_source_hash != current_source_hash:
            return True

        # 3. Dependencies changed
        file_deps = self.deps.get(str(source), [])
        for dep in file_deps:
            dep_path = Path(dep)
            if not dep_path.exists():
                # A recorded dependency disappeared; force a rebuild so the
                # page is rebuilt against the current state of the project.
                return True
            current_dep_hash = self._current_hash(dep_path)
            cached_dep_hash = self.hashes.get(dep)
            if cached_dep_hash != current_dep_hash:
                return True

        return False

    def deps_changed(self, source: Path, current_deps: list[str]) -> bool:
        """Return True when the recorded dependency set differs from the current one.

        Catches added/removed dependencies. A dependency whose *content*
        changed is detected by `should_rebuild`'s per-dep hash check, but a
        newly-added or removed dep is only visible as a set difference here.
        """
        return set(self.deps.get(str(source), [])) != set(current_deps)

    def should_full_rebuild(self, config_path: Path, pkg_version: str | None = None, theme_sig: str | None = None) -> bool:
        """Check if config/global changes require full rebuild.
        
        Returns True if docsforge.yml hash changed, the docsforge package
        version changed, or the theme templates changed.
        """
        # Package version change -> full rebuild (theme/templates/SW updated).
        if pkg_version is not None and self.pkg_version != pkg_version:
            return True
        # Theme template change -> full rebuild (base.html/partials/custom_dir).
        if theme_sig is not None and self.theme_sig != theme_sig:
            return True

        if not config_path.exists():
            return True

        current_config_hash = self.hasher.hash_file(config_path)
        if self.config_hash is None:
            return True
        if self.config_hash != current_config_hash:
            return True

        return False

    def find_orphaned_outputs(self, source_dir: Path, output_dir: Path) -> list[Path]:
        """Find output files that don't have corresponding source files.
        
        Returns list of orphaned output files to delete.
        """
        orphaned = []
        if not output_dir.exists():
            return orphaned

        for output_file in output_dir.rglob("*"):
            if output_file.is_dir():
                continue

            # Try to find corresponding source
            rel_path = output_file.relative_to(output_dir)
            source_file = source_dir / rel_path

            # Handle .html outputs from .md sources. With the default
            # `use_directory_urls=True`, docs/foo.md builds to site/foo/index.html
            # and docs/foo/index.md builds to site/foo/index.html, so we must
            # check several candidate source paths before declaring orphaned.
            if output_file.suffix == ".html":
                # Non-directory style: site/foo.html <- docs/foo.md
                if source_file.with_suffix(".md").exists():
                    continue
                # Directory style: site/<name>/index.html <- docs/<name>.md
                if output_file.name == "index.html":
                    rel_parent = output_file.parent.relative_to(output_dir)
                    if str(rel_parent) not in (".", ""):
                        # docs/<rel_parent>.md  (e.g. docs/foo.md)
                        if (source_dir / rel_parent).with_suffix(".md").exists():
                            continue
                        # docs/<rel_parent>/index.md
                        if (source_dir / rel_parent / "index.md").exists():
                            continue

            if not source_file.exists():
                orphaned.append(output_file)

        return orphaned

    def invalidate(self) -> None:
        """Clear cached hashes/deps (in-memory + disk) for a full rebuild.

        Retains `meta` (the mtime/size hash cache) because source file
        contents don't change just because the config or package version did —
        so the rebuild still avoids re-reading unchanged sources.
        """
        self.hashes = {}
        self.deps = {}
        self.config_hash = None
        self.pkg_version = None
        self.theme_sig = None
        self.cache.invalidate()

    def update_cache(self, source: Path, output: Path, deps: list[str] | None = None) -> None:
        """Update cache after successful rebuild."""
        self.hashes[str(source)] = self._current_hash(source)
        if deps:
            self.deps[str(source)] = deps
            # Record dependency hashes so `should_rebuild` can detect when an
            # included file changes. Without this the dep check always saw a
            # missing cached hash and rebuilt every time.
            for dep in deps:
                dep_path = Path(dep)
                if dep_path.exists():
                    self.hashes[dep] = self._current_hash(dep_path)

    def should_scan_orphans(self, current_sources: set[str]) -> bool:
        """Return True only if a source file was removed since the last build.

        Orphaned outputs (a built page whose source .md was deleted) can only
        appear when a source is removed, so when the source set is unchanged
        or only grew we skip the full site_dir walk.
        """
        cached = set(self.cache.get_sources())
        if not cached:
            return True  # first build, or cache lost — scan to be safe
        return bool(cached - current_sources)  # something was removed

    def update_sources(self, current_sources: set[str]) -> None:
        """Record the source set for this build."""
        self.cache.set_sources(list(current_sources))

    def save(self, config_hash: str | None = None, pkg_version: str | None = None, theme_sig: str | None = None, nav_sig: str | None = None) -> None:
        """Save all cache state."""
        self.cache.set_hashes(self.hashes)
        self.cache.set_deps(self.deps)
        self.cache.set_meta(self.meta)
        self.cache.set_validation(self.validation)
        if config_hash:
            self.cache.set_config_hash(config_hash)
            self.config_hash = config_hash
        if pkg_version:
            self.cache.set_pkg_version(pkg_version)
            self.pkg_version = pkg_version
        if theme_sig:
            self.cache.set_theme_sig(theme_sig)
            self.theme_sig = theme_sig
        if nav_sig:
            self.cache.set_nav_sig(nav_sig)
            self.nav_sig = nav_sig
        self.cache.set_version(CACHE_VERSION)
