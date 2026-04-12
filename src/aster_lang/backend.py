"""Backend interface layer for multi-backend support."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from aster_lang import ast
from aster_lang.module_resolution import ModuleSearchConfig


@dataclass(slots=True)
class BackendArtifact:
    """Artifact bundle produced by a backend adapter."""

    entry_path: Path
    outputs: list[Path]
    metadata: dict[str, object] = field(default_factory=dict)
    format: str | None = None
    errors: list[str] = field(default_factory=list)
    cache_hit: bool = False  # True if artifact was retrieved from cache


@dataclass(slots=True)
class BackendBuildOptions:
    entry_path: Path
    entry_module: ast.Module | None = None
    dep_overrides: dict[str, Path] | None = None
    extra_roots: tuple[Path, ...] = ()
    out_dir: Path | None = None
    clean: bool = False
    resolver_config: ModuleSearchConfig | None = None
    artifact_format: str | None = None
    # Caching options
    cache_enabled: bool = False
    cache_manager: Any | None = None  # CacheManager instance
    ownership_mode: str = "standard"  # For cache key computation
    types_mode: str = "standard"  # For cache key computation


class BackendAdapter(Protocol):
    """Interface for backend adapters."""

    name: str
    supported_formats: tuple[str, ...]

    def build(self, options: BackendBuildOptions) -> BackendArtifact:
        """Build a backend artifact for the given entry file."""
        raise NotImplementedError


class BackendRegistry:
    """Registry for backend adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, BackendAdapter] = {}

    def register(self, adapter: BackendAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> BackendAdapter:
        if name not in self._adapters:
            available = ", ".join(self.names())
            raise KeyError(f"Unknown backend '{name}'. Available: {available}")
        return self._adapters[name]

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))

    def validate_format(self, adapter: BackendAdapter, artifact_format: str | None) -> None:
        if artifact_format is None:
            return
        if artifact_format not in adapter.supported_formats:
            raise ValueError(
                f"Backend '{adapter.name}' does not support artifact format '{artifact_format}'"
            )
