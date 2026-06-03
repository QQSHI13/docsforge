"""DocsForge incremental build cache - tracks file hashes and dependencies for dirty builds."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

CACHE_DIR = Path(".docsforge/cache")
CACHE_VERSION = 1


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

    def _read_json(self, path: Path) -> dict[str, Any]:
        """Read JSON file, return empty dict if missing."""
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
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

    def invalidate(self) -> None:
        """Clear all cache files."""
        for f in [self.hashes_file, self.deps_file, self.config_hash_file]:
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
    def get_file_deps(source_path: Path, content: str) -> list[str]:
        """Extract dependencies from markdown content.
        
        Currently tracks:
        - Template includes (not yet implemented)
        - Will be extended for admonition, macros, etc.
        """
        deps = []
        # TODO: Parse template references, includes, etc.
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

    def _get_current_hash(self, path: Path) -> str:
        """Get hash of a file, reading from cache if unchanged."""
        str_path = str(path)
        if str_path not in self.hashes or not path.exists():
            return self.hasher.hash_file(path) if path.exists() else ""
        return self.hashes[str_path]

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

        current_source_hash = self.hasher.hash_file(source)
        cached_source_hash = self.hashes.get(str(source))
        if cached_source_hash != current_source_hash:
            return True

        # 3. Dependencies changed
        file_deps = self.deps.get(str(source), [])
        for dep in file_deps:
            dep_path = Path(dep)
            if not dep_path.exists():
                continue
            current_dep_hash = self.hasher.hash_file(dep_path)
            cached_dep_hash = self.hashes.get(dep)
            if cached_dep_hash != current_dep_hash:
                return True

        return False

    def should_full_rebuild(self, config_path: Path) -> bool:
        """Check if config/global changes require full rebuild.
        
        Returns True if docsforge.yml hash changed.
        """
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

            # Handle .html outputs from .md sources
            if output_file.suffix == ".html":
                source_md = source_file.with_suffix(".md")
                if source_md.exists():
                    continue

            if not source_file.exists():
                orphaned.append(output_file)

        return orphaned

    def update_cache(self, source: Path, output: Path, deps: list[str] | None = None) -> None:
        """Update cache after successful rebuild."""
        self.hashes[str(source)] = self.hasher.hash_file(source)
        if deps:
            self.deps[str(source)] = deps

    def save(self, config_hash: str | None = None) -> None:
        """Save all cache state."""
        self.cache.set_hashes(self.hashes)
        self.cache.set_deps(self.deps)
        if config_hash:
            self.cache.set_config_hash(config_hash)
        self.cache.set_version(CACHE_VERSION)
