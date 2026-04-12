from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aster_lang.backend import BackendArtifact, BackendBuildOptions, BackendRegistry


@dataclass
class _DummyAdapter:
    name: str
    supported_formats: tuple[str, ...] = ("dummy",)

    def build(self, options: BackendBuildOptions) -> BackendArtifact:
        return BackendArtifact(entry_path=options.entry_path, outputs=[options.entry_path])


def test_backend_registry_registers_and_resolves() -> None:
    registry = BackendRegistry()
    adapter = _DummyAdapter(name="dummy")
    registry.register(adapter)

    resolved = registry.get("dummy")
    assert resolved is adapter


def test_backend_registry_names_sorted() -> None:
    registry = BackendRegistry()
    registry.register(_DummyAdapter(name="zeta"))
    registry.register(_DummyAdapter(name="alpha"))

    assert registry.names() == ("alpha", "zeta")


def test_backend_build_options_defaults() -> None:
    entry = Path("main.aster")
    options = BackendBuildOptions(entry_path=entry)
    assert options.entry_path == entry
    assert options.entry_module is None
    assert options.dep_overrides is None
    assert options.extra_roots == ()
    assert options.out_dir is None
    assert options.clean is False
    assert options.resolver_config is None
    assert options.artifact_format is None
