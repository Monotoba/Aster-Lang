"""Lockfile support for reproducible module resolution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from aster_lang.module_resolution import ModuleSearchConfig

LOCKFILE_VERSION = 1


@dataclass(frozen=True)
class Lockfile:
    version: int
    project_root: Path
    package_name: str | None
    search_roots: tuple[Path, ...]
    dependencies: tuple[tuple[str, Path], ...]

    def to_config(self) -> ModuleSearchConfig:
        return ModuleSearchConfig(
            project_root=self.project_root,
            package_name=self.package_name,
            search_roots=self.search_roots,
            dependencies=self.dependencies,
        )


class LockfileError(Exception):
    """Raised when reading/writing a lockfile fails."""


def write_lockfile(path: Path, lock: Lockfile) -> None:
    data = {
        "version": lock.version,
        "project_root": str(lock.project_root),
        "package_name": lock.package_name,
        "search_roots": [str(p) for p in lock.search_roots],
        "dependencies": {name: str(p) for name, p in lock.dependencies},
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_lockfile(path: Path) -> Lockfile:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise LockfileError(f"Cannot read lockfile: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LockfileError(f"Invalid lockfile JSON: {path}") from exc

    if not isinstance(raw, dict):
        raise LockfileError(f"Invalid lockfile: expected an object: {path}")

    version = raw.get("version")
    if version != LOCKFILE_VERSION:
        raise LockfileError(f"Unsupported lockfile version: {version!r}")

    project_root_raw = raw.get("project_root")
    if not isinstance(project_root_raw, str):
        raise LockfileError("Invalid lockfile: project_root must be a string")
    project_root = Path(project_root_raw).resolve()

    package_name = raw.get("package_name")
    if package_name is not None and not isinstance(package_name, str):
        raise LockfileError("Invalid lockfile: package_name must be a string or null")

    search_roots_raw = raw.get("search_roots")
    if not isinstance(search_roots_raw, list) or not all(
        isinstance(p, str) for p in search_roots_raw
    ):
        raise LockfileError("Invalid lockfile: search_roots must be a list of strings")
    search_roots = tuple(Path(p).resolve() for p in search_roots_raw)

    deps_raw = raw.get("dependencies")
    if not isinstance(deps_raw, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in deps_raw.items()
    ):
        raise LockfileError("Invalid lockfile: dependencies must be an object of string paths")
    dependencies = tuple((name, Path(p).resolve()) for name, p in deps_raw.items())

    return Lockfile(
        version=LOCKFILE_VERSION,
        project_root=project_root,
        package_name=package_name,
        search_roots=search_roots,
        dependencies=dependencies,
    )
