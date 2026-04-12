"""Backend interface layer for multi-backend support."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(slots=True)
class BackendArtifact:
    """Artifact bundle produced by a backend adapter."""

    entry_path: Path
    outputs: list[Path]
    metadata: dict[str, object] = field(default_factory=dict)
    format: str | None = None


class BackendAdapter(Protocol):
    """Interface for backend adapters."""

    name: str
    supported_formats: tuple[str, ...]

    def build(self, *, entry_path: Path, artifact_format: str | None = None) -> BackendArtifact:
        """Build a backend artifact for the given entry file."""
        raise NotImplementedError


class BackendRegistry:
    """Registry for backend adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, BackendAdapter] = {}

    def register(self, adapter: BackendAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> BackendAdapter:
        return self._adapters[name]

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))
