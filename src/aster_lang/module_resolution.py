"""Shared module-resolution logic for the Aster toolchain."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

MANIFEST_NAME = "aster.toml"


def get_stdlib_path() -> Path:
    """Return the absolute path to the bundled stdlib .aster source files."""
    return Path(__file__).parent / "stdlib"


class ModuleResolutionError(Exception):
    """Raised when module resolution or manifest loading fails."""


@dataclass(frozen=True)
class ModuleSearchConfig:
    """Resolved module search configuration for a base directory."""

    project_root: Path
    package_name: str | None
    search_roots: tuple[Path, ...]
    dependencies: tuple[tuple[str, Path], ...]  # (dep_name, dep_root) pairs


def resolve_module_path(
    base_dir: Path | None,
    module_parts: list[str],
    dep_overrides: dict[str, Path] | None = None,
    extra_roots: tuple[Path, ...] = (),
    config: ModuleSearchConfig | None = None,
) -> Path:
    """Resolve a module path from a base directory.

    *dep_overrides* maps dependency names to directory paths and takes priority
    over any manifest ``[dependencies]`` entries with the same name.
    *extra_roots* are prepended to the effective search roots.
    """
    module_label = ".".join(module_parts)
    if base_dir is None:
        raise ModuleResolutionError(
            f"Cannot resolve module '{module_label}' without a base directory"
        )

    search_config = config if config is not None else discover_module_search_config(base_dir)
    effective = _apply_cli_overrides(search_config, dep_overrides or {}, extra_roots, base_dir)

    if effective is not None:
        # 1. Check dependencies (CLI overrides shadow manifest entries).
        if module_parts:
            for dep_name, dep_root in effective.dependencies:
                if module_parts[0] == dep_name:
                    if not dep_root.exists():
                        raise ModuleResolutionError(
                            f"Dependency '{dep_name}' path not found: {dep_root}"
                        )
                    tail = module_parts[1:]
                    if not tail:
                        raise ModuleResolutionError(
                            f"Cannot import dependency package '{dep_name}' directly; "
                            "specify a module within it"
                        )
                    module_path = dep_root.joinpath(*tail).with_suffix(".aster")
                    if module_path.exists():
                        return module_path.resolve()
                    raise ModuleResolutionError(
                        f"Module not found: {module_label} "
                        f"(searched dependency '{dep_name}' at {dep_root})"
                    )

        # 2. Strip current-package prefix, then search configured roots.
        relative_parts = _manifest_relative_parts(effective, module_parts)
        for search_root in effective.search_roots:
            module_path = search_root.joinpath(*relative_parts).with_suffix(".aster")
            if module_path.exists():
                return module_path.resolve()
        # 3. Fall through to bundled stdlib.
        stdlib_module = get_stdlib_path().joinpath(*relative_parts).with_suffix(".aster")
        if stdlib_module.exists():
            return stdlib_module.resolve()
        raise ModuleResolutionError(
            f"Module not found: {module_label} (searched project root {effective.project_root})"
        )

    search_dir = base_dir.resolve()
    while True:
        module_path = search_dir.joinpath(*module_parts).with_suffix(".aster")
        if module_path.exists():
            return module_path.resolve()
        if search_dir.parent == search_dir:
            break
        search_dir = search_dir.parent

    # Check bundled stdlib before giving up.
    stdlib_module = get_stdlib_path().joinpath(*module_parts).with_suffix(".aster")
    if stdlib_module.exists():
        return stdlib_module.resolve()
    raise ModuleResolutionError(f"Module not found: {module_label}")


def discover_module_search_config(base_dir: Path) -> ModuleSearchConfig | None:
    """Discover manifest-based module search roots for a base directory."""
    manifest_path = find_manifest(base_dir.resolve())
    if manifest_path is None:
        return None

    project_root = manifest_path.parent.resolve()
    data = _load_manifest_data(manifest_path)
    package_name = _load_manifest_package_name(manifest_path, data)
    configured_roots = _load_manifest_search_roots(manifest_path, project_root, data)
    search_roots = _dedupe_paths((project_root, *configured_roots))
    dependencies = _load_manifest_dependencies(manifest_path, project_root, data)
    return ModuleSearchConfig(
        project_root=project_root,
        package_name=package_name,
        search_roots=search_roots,
        dependencies=dependencies,
    )


def find_manifest(start_dir: Path) -> Path | None:
    """Search upward for ``aster.toml``."""
    current = start_dir.resolve()
    while True:
        manifest_path = current / MANIFEST_NAME
        if manifest_path.exists():
            return manifest_path
        if current.parent == current:
            return None
        current = current.parent


def _load_manifest_data(manifest_path: Path) -> dict[str, object]:
    """Load manifest TOML data."""
    try:
        data = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ModuleResolutionError(f"Invalid manifest at {manifest_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ModuleResolutionError(f"Invalid manifest at {manifest_path}: expected a TOML table")
    return data


def _load_manifest_package_name(
    manifest_path: Path,
    data: dict[str, object],
) -> str | None:
    """Load optional package name from a manifest."""
    package = data.get("package")
    if package is None:
        return None
    if not isinstance(package, dict):
        raise ModuleResolutionError(
            f"Invalid manifest at {manifest_path}: [package] must be a table"
        )
    package_name = package.get("name")
    if package_name is None:
        return None
    if not isinstance(package_name, str):
        raise ModuleResolutionError(
            f"Invalid manifest at {manifest_path}: package.name must be a string"
        )
    if package_name == "":
        raise ModuleResolutionError(
            f"Invalid manifest at {manifest_path}: package.name must not be empty"
        )
    return package_name


def _load_manifest_search_roots(
    manifest_path: Path,
    project_root: Path,
    data: dict[str, object],
) -> tuple[Path, ...]:
    """Load additional relative module roots from a manifest."""

    modules = data.get("modules", {})
    if not isinstance(modules, dict):
        raise ModuleResolutionError(
            f"Invalid manifest at {manifest_path}: [modules] must be a table"
        )

    search_roots = modules.get("search_roots", [])
    if not isinstance(search_roots, list):
        raise ModuleResolutionError(
            f"Invalid manifest at {manifest_path}: modules.search_roots must be a list"
        )

    resolved_roots: list[Path] = []
    for entry in search_roots:
        if not isinstance(entry, str):
            raise ModuleResolutionError(
                f"Invalid manifest at {manifest_path}: search roots must be strings"
            )
        entry_path = Path(entry)
        if entry_path.is_absolute() or ".." in entry_path.parts:
            raise ModuleResolutionError(
                f"Invalid manifest at {manifest_path}: search roots must be relative paths"
            )
        resolved_roots.append((project_root / entry_path).resolve())

    return tuple(resolved_roots)


def _apply_cli_overrides(
    config: ModuleSearchConfig | None,
    dep_overrides: dict[str, Path],
    extra_roots: tuple[Path, ...],
    base_dir: Path,
) -> ModuleSearchConfig | None:
    """Return a config with CLI dep overrides and extra roots applied.

    CLI dep overrides replace manifest entries with the same name; new names are
    appended.  Extra roots are prepended to the search roots.  If there was no
    manifest config and no overrides, returns None so the parent-dir walk fires.
    """
    if not dep_overrides and not extra_roots:
        return config

    if config is None:
        # No manifest — synthesise a minimal config from CLI flags alone.
        if not dep_overrides and not extra_roots:
            return None
        resolved_base = base_dir.resolve()
        return ModuleSearchConfig(
            project_root=resolved_base,
            package_name=None,
            search_roots=_dedupe_paths((resolved_base, *extra_roots)),
            dependencies=tuple((n, p.resolve()) for n, p in dep_overrides.items()),
        )

    # Merge: CLI overrides shadow manifest deps with the same name.
    manifest_deps = {name: path for name, path in config.dependencies}
    manifest_deps.update({n: p.resolve() for n, p in dep_overrides.items()})
    merged_deps = tuple(manifest_deps.items())

    merged_roots = _dedupe_paths((*extra_roots, *config.search_roots))

    return ModuleSearchConfig(
        project_root=config.project_root,
        package_name=config.package_name,
        search_roots=merged_roots,
        dependencies=merged_deps,
    )


def _load_manifest_dependencies(
    manifest_path: Path,
    project_root: Path,
    data: dict[str, object],
) -> tuple[tuple[str, Path], ...]:
    """Load declared dependencies from a manifest's [dependencies] table."""
    deps_raw = data.get("dependencies", {})
    if not isinstance(deps_raw, dict):
        raise ModuleResolutionError(
            f"Invalid manifest at {manifest_path}: [dependencies] must be a table"
        )

    result: list[tuple[str, Path]] = []
    for dep_name, dep_value in deps_raw.items():
        if not isinstance(dep_value, dict):
            raise ModuleResolutionError(
                f"Invalid manifest at {manifest_path}: "
                f"dependency '{dep_name}' must be a table (e.g. {{ path = \"...\" }})"
            )
        raw_path = dep_value.get("path")
        if raw_path is None:
            raise ModuleResolutionError(
                f"Invalid manifest at {manifest_path}: "
                f"dependency '{dep_name}' is missing a 'path' key"
            )
        if not isinstance(raw_path, str):
            raise ModuleResolutionError(
                f"Invalid manifest at {manifest_path}: "
                f"dependency '{dep_name}'.path must be a string"
            )
        dep_path = (project_root / raw_path).resolve()
        result.append((dep_name, dep_path))

    return tuple(result)


def _manifest_relative_parts(
    search_config: ModuleSearchConfig,
    module_parts: list[str],
) -> list[str]:
    """Strip the current package prefix from a manifest-aware import path."""
    if search_config.package_name is None:
        return module_parts
    if module_parts and module_parts[0] == search_config.package_name:
        return module_parts[1:]
    return module_parts


def _dedupe_paths(paths: tuple[Path, ...]) -> tuple[Path, ...]:
    """Preserve order while removing duplicate paths."""
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        result.append(path)
    return tuple(result)
