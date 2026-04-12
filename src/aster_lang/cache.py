"""Caching and incremental compilation support.

Cache structure:
    .aster_cache/
        v1/                          # Cache format version
            modules/                 # Per-module cached artifacts
                <hash>/              # Cache key = hash(source + config)
                    metadata.json    # Source path, mtime, dependencies, build config
                    artifact         # Backend-specific output
            deps/                    # Dependency graph for invalidation
                <module_hash>.deps   # List of dependency hashes

Cache key inputs:
    - Source file content (SHA256)
    - Compiler flags (--backend, --ownership, --types, artifact format)
    - Module resolver config (manifest contents, lockfile, search roots)
    - Toolchain version (aster-lang package version)
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CACHE_VERSION = "v1"
CACHE_DIR_NAME = ".aster_cache"


def get_cache_root(project_root: Path | None = None) -> Path:
    """Get the cache root directory.

    Priority:
    1. Project root (if aster.toml exists or .aster_cache already exists)
    2. Current directory (if it has aster.toml or .aster_cache)
    3. Global cache directory (fallback)
    """
    if project_root is not None:
        return project_root / CACHE_DIR_NAME / CACHE_VERSION

    # Check current directory first
    cwd = Path.cwd()
    if (cwd / "aster.toml").exists() or (cwd / CACHE_DIR_NAME).exists():
        return cwd / CACHE_DIR_NAME / CACHE_VERSION

    # Fall back to global cache
    home = Path.home()
    return home / ".cache" / "aster-lang" / CACHE_VERSION


@dataclass(slots=True)
class CacheKey:
    """Cache key components."""

    source_hash: str
    config_hash: str

    def full_hash(self) -> str:
        """Compute the full cache key hash."""
        data = f"{self.source_hash}:{self.config_hash}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]


@dataclass(slots=True)
class CacheMetadata:
    """Metadata stored with cached artifacts."""

    source_path: str
    source_mtime: float
    source_size: int
    source_hash: str
    config_hash: str
    backend: str
    artifact_format: str | None
    ownership_mode: str
    types_mode: str
    dependencies: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: __import__("time").time())

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "source_mtime": self.source_mtime,
            "source_size": self.source_size,
            "source_hash": self.source_hash,
            "config_hash": self.config_hash,
            "backend": self.backend,
            "artifact_format": self.artifact_format,
            "ownership_mode": self.ownership_mode,
            "types_mode": self.types_mode,
            "dependencies": self.dependencies,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CacheMetadata:
        return cls(
            source_path=data["source_path"],
            source_mtime=data["source_mtime"],
            source_size=data["source_size"],
            source_hash=data["source_hash"],
            config_hash=data["config_hash"],
            backend=data["backend"],
            artifact_format=data.get("artifact_format"),
            ownership_mode=data["ownership_mode"],
            types_mode=data["types_mode"],
            dependencies=data.get("dependencies", []),
            created_at=data.get("created_at", 0),
        )


class CacheManager:
    """Manages the build cache."""

    def __init__(self, project_root: Path | None = None, enabled: bool = True) -> None:
        self.enabled = enabled
        self.cache_root = get_cache_root(project_root)
        self.modules_dir = self.cache_root / "modules"
        self.deps_dir = self.cache_root / "deps"

        if enabled:
            self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Ensure cache directories exist."""
        self.modules_dir.mkdir(parents=True, exist_ok=True)
        self.deps_dir.mkdir(parents=True, exist_ok=True)

    def _source_hash(self, source_path: Path) -> str:
        """Compute SHA256 hash of source file content."""
        content = source_path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def _config_hash(
        self,
        *,
        backend: str,
        artifact_format: str | None,
        ownership_mode: str,
        types_mode: str,
        resolver_config: Any | None = None,
        extra_flags: dict[str, Any] | None = None,
    ) -> str:
        """Compute hash of build configuration."""
        config: dict[str, Any] = {
            "backend": backend,
            "artifact_format": artifact_format,
            "ownership_mode": ownership_mode,
            "types_mode": types_mode,
            "toolchain_version": self._toolchain_version(),
        }
        if resolver_config is not None:
            config["resolver"] = str(resolver_config)
        if extra_flags:
            config["extra_flags"] = extra_flags

        config_str = json.dumps(config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()

    def _toolchain_version(self) -> str:
        """Get the current toolchain version."""
        # For now, use a hash of the source files as the version
        # In production, this would be the package version
        try:
            from aster_lang import __file__ as pkg_file

            pkg_dir = Path(pkg_file).parent
            version_file = pkg_dir / "__init__.py"
            if version_file.exists():
                return hashlib.sha256(version_file.read_bytes()).hexdigest()[:16]
        except Exception:
            pass
        return "dev"

    def compute_key(
        self,
        source_path: Path,
        *,
        backend: str,
        artifact_format: str | None = None,
        ownership_mode: str = "standard",
        types_mode: str = "standard",
        resolver_config: Any | None = None,
    ) -> CacheKey:
        """Compute cache key for a source file."""
        source_hash = self._source_hash(source_path)
        config_hash = self._config_hash(
            backend=backend,
            artifact_format=artifact_format,
            ownership_mode=ownership_mode,
            types_mode=types_mode,
            resolver_config=resolver_config,
        )
        return CacheKey(source_hash=source_hash, config_hash=config_hash)

    def _cache_dir(self, key: CacheKey) -> Path:
        """Get the cache directory for a given key."""
        return self.modules_dir / key.full_hash()

    def _metadata_path(self, key: CacheKey) -> Path:
        """Get the metadata file path for a given key."""
        return self._cache_dir(key) / "metadata.json"

    def _artifact_path(self, key: CacheKey, backend: str, artifact_format: str | None) -> Path:
        """Get the artifact file path for a given key."""
        ext = self._artifact_extension(backend, artifact_format)
        return self._cache_dir(key) / f"artifact{ext}"

    def _artifact_extension(self, backend: str, artifact_format: str | None) -> str:
        """Get the file extension for an artifact."""
        if backend == "python":
            return ".py"
        if backend == "vm":
            if artifact_format == "binary":
                return ".asterbc"
            return ".asterbc.json"
        if backend == "c":
            return ".c"
        return ""

    def get(
        self,
        source_path: Path,
        key: CacheKey,
        backend: str,
        artifact_format: str | None = None,
    ) -> tuple[CacheMetadata, Path] | None:
        """Get cached artifact if it exists and is valid.

        Returns (metadata, artifact_path) if cache hit, None otherwise.
        """
        if not self.enabled:
            return None

        metadata_path = self._metadata_path(key)
        artifact_path = self._artifact_path(key, backend, artifact_format)

        if not metadata_path.exists() or not artifact_path.exists():
            return None

        try:
            metadata = CacheMetadata.from_dict(json.loads(metadata_path.read_text()))
        except (json.JSONDecodeError, KeyError):
            return None

        # Verify source hasn't changed
        current_stat = source_path.stat()
        if (
            current_stat.st_mtime != metadata.source_mtime
            or current_stat.st_size != metadata.source_size
        ):
            return None

        # Verify source hash matches (definitive check)
        current_hash = self._source_hash(source_path)
        if current_hash != metadata.source_hash:
            return None

        # Check dependencies are still valid
        if metadata.dependencies:
            for dep_hash in metadata.dependencies:
                dep_cache_dir = self.modules_dir / dep_hash
                if not dep_cache_dir.exists():
                    return None

        return metadata, artifact_path

    def put(
        self,
        source_path: Path,
        key: CacheKey,
        backend: str,
        artifact_format: str | None,
        ownership_mode: str,
        types_mode: str,
        artifact_path: Path,
        dependencies: list[str] | None = None,
    ) -> None:
        """Store an artifact in the cache."""
        if not self.enabled:
            return

        cache_dir = self._cache_dir(key)
        cache_dir.mkdir(parents=True, exist_ok=True)

        stat = source_path.stat()
        metadata = CacheMetadata(
            source_path=str(source_path),
            source_mtime=stat.st_mtime,
            source_size=stat.st_size,
            source_hash=key.source_hash,
            config_hash=key.config_hash,
            backend=backend,
            artifact_format=artifact_format,
            ownership_mode=ownership_mode,
            types_mode=types_mode,
            dependencies=dependencies or [],
        )

        metadata_path = self._metadata_path(key)
        metadata_path.write_text(json.dumps(metadata.to_dict(), indent=2))

        # Copy artifact into cache directory
        dest_artifact = self._artifact_path(key, backend, artifact_format)
        shutil.copy2(artifact_path, dest_artifact)

        # Store dependency info
        if dependencies:
            deps_path = self.deps_dir / f"{key.full_hash()}.deps"
            deps_path.write_text(json.dumps(dependencies))

    def invalidate(self, source_path: Path) -> None:
        """Invalidate cache entries for a source file."""
        if not self.enabled:
            return

        # Find all cache entries for this source path
        source_str = str(source_path)
        for cache_dir in self.modules_dir.iterdir():
            metadata_path = cache_dir / "metadata.json"
            if metadata_path.exists():
                try:
                    metadata = CacheMetadata.from_dict(json.loads(metadata_path.read_text()))
                    if metadata.source_path == source_str:
                        # Remove cache entry
                        import shutil

                        shutil.rmtree(cache_dir)
                        # Remove deps file if exists
                        deps_path = self.deps_dir / f"{cache_dir.name}.deps"
                        if deps_path.exists():
                            deps_path.unlink()
                except (json.JSONDecodeError, KeyError):
                    pass

    def clear(self) -> int:
        """Clear all cached artifacts. Returns number of entries removed."""
        if not self.cache_root.exists():
            return 0

        count = 0
        for cache_dir in self.modules_dir.iterdir():
            import shutil

            shutil.rmtree(cache_dir)
            count += 1

        for deps_file in self.deps_dir.iterdir():
            deps_file.unlink()

        return count

    def stats(self) -> dict[str, int]:
        """Get cache statistics."""
        if not self.enabled or not self.cache_root.exists():
            return {"entries": 0, "size_bytes": 0}

        entries = sum(1 for _ in self.modules_dir.iterdir() if _.is_dir())
        size_bytes = sum(f.stat().st_size for f in self.cache_root.rglob("*") if f.is_file())
        return {"entries": entries, "size_bytes": size_bytes}
