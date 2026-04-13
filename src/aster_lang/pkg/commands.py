"""Aster package manager CLI command implementations.

Each public function corresponds to an `aster pkg <verb>` subcommand.
Functions return an exit code (0 = success, non-zero = failure).
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from aster_lang.pkg.manifest import Manifest, ManifestError, load_manifest

MANIFEST_NAME = "aster.toml"
LOCKFILE_NAME = "aster.lock"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _find_manifest(start: Path) -> Path | None:
    """Search upward for aster.toml."""
    current = start.resolve()
    while True:
        candidate = current / MANIFEST_NAME
        if candidate.exists():
            return candidate
        if current.parent == current:
            return None
        current = current.parent


def _print_errors(errors: list[ManifestError]) -> None:
    for e in errors:
        print(f"  {e}", file=sys.stderr)


# ---------------------------------------------------------------------------
# aster pkg init
# ---------------------------------------------------------------------------

_MANIFEST_TEMPLATE = """\
[package]
name = "{name}"
version = "0.1.0"
type = "{pkg_type}"
description = "A new Aster {pkg_type}."
license = "MIT"
readme = "README.md"

[[package.authors]]
name = "{author}"

[aster]
min_version = "0.1.0"

[{role}]
entry = "src/{name}/lib.aster"
"""

_MAIN_ASTER = """\
# {name} — entry point

fn main():
    print("Hello from {name}!")
"""

_TEST_ASTER = """\
# Basic test for {name}

fn test_placeholder() -> Bool:
    return true
"""

_README = """\
# {name}

A new Aster {pkg_type}.

## Usage

```bash
aster run src/{name}/lib.aster
```
"""

_GITIGNORE = """\
__aster_build__/
dist/
*.apkg
.aster_cache/
"""


def cmd_init(name: str | None, pkg_type: str, author: str, output_dir: Path) -> int:
    """Implement `aster pkg init`."""
    if name is None:
        name = output_dir.name
        if not name or name == ".":
            name = "my-package"

    pkg_dir = output_dir / name
    if pkg_dir.exists():
        print(f"error: directory already exists: {pkg_dir}", file=sys.stderr)
        return 1

    role_map = {"library": "lib", "application": "app", "tool": "tool"}
    role = role_map[pkg_type]

    # Create layout
    src_dir = pkg_dir / "src" / name
    src_dir.mkdir(parents=True)
    (pkg_dir / "tests").mkdir()

    # Write files
    (pkg_dir / MANIFEST_NAME).write_text(
        _MANIFEST_TEMPLATE.format(name=name, pkg_type=pkg_type, author=author, role=role)
    )
    (src_dir / "lib.aster").write_text(_MAIN_ASTER.format(name=name))
    (pkg_dir / "tests" / "test_basic.aster").write_text(_TEST_ASTER.format(name=name))
    (pkg_dir / "README.md").write_text(_README.format(name=name, pkg_type=pkg_type))
    (pkg_dir / ".gitignore").write_text(_GITIGNORE)

    print(f"Created package '{name}' in {pkg_dir}/")
    print("\nNext steps:")
    print(f"  cd {name}")
    print("  aster pkg check")
    print("  aster pkg build")
    return 0


# ---------------------------------------------------------------------------
# aster pkg check
# ---------------------------------------------------------------------------


def cmd_check(manifest_path: Path | None = None) -> int:
    """Implement `aster pkg check` — validate manifest without building."""
    if manifest_path is None:
        found = _find_manifest(Path.cwd())
        if found is None:
            print(
                f"error: no {MANIFEST_NAME} found in current directory or any parent",
                file=sys.stderr,
            )
            return 1
        manifest_path = found

    print(f"Checking {manifest_path} ...")
    manifest, errors = load_manifest(manifest_path)

    if errors:
        print(f"\n{len(errors)} error(s) found:\n", file=sys.stderr)
        _print_errors(errors)
        return 1

    if manifest is not None:
        print(f"  package : {manifest.name} v{manifest.version}")
        print(f"  type    : {manifest.pkg_type}")
        print(f"  license : {manifest.license}")
        print(f"  authors : {', '.join(a.name for a in manifest.authors)}")
        if manifest.dependencies:
            print(f"  deps    : {', '.join(manifest.dependencies)}")
        print("\nOK — manifest is valid.")
    return 0


# ---------------------------------------------------------------------------
# aster pkg build
# ---------------------------------------------------------------------------


def _collect_files(pkg_dir: Path, manifest: Manifest) -> list[Path]:
    """Collect all files to include in the archive."""
    src_root = pkg_dir / manifest.source_root
    files: list[Path] = []

    # Source files
    if src_root.exists():
        for f in sorted(src_root.rglob("*")):
            if f.is_file():
                files.append(f)

    # Tests
    tests_dir = pkg_dir / "tests"
    if tests_dir.exists():
        for f in sorted(tests_dir.rglob("*")):
            if f.is_file():
                files.append(f)

    # Docs / readme
    for name in ("README.md", "README.txt", "README", "LICENSE", "LICENSE.txt", "CHANGELOG.md"):
        candidate = pkg_dir / name
        if candidate.exists():
            files.append(candidate)

    # Manifest itself
    manifest_file = pkg_dir / MANIFEST_NAME
    if manifest_file not in files:
        files.append(manifest_file)

    return files


def _archive_path(pkg_dir: Path, file: Path, manifest: Manifest) -> str:
    """Map a filesystem path to its in-archive path."""
    rel = file.relative_to(pkg_dir)
    parts = rel.parts
    name = manifest.name
    version = str(manifest.version)

    # manifest → manifest/aster.toml
    if rel == Path(MANIFEST_NAME):
        return f"{name}-{version}/manifest/aster.toml"
    # everything else → name-version/<rel>
    return f"{name}-{version}/{'/'.join(parts)}"


def cmd_build(
    manifest_path: Path | None = None,
    out_dir: Path | None = None,
) -> int:
    """Implement `aster pkg build` — produce a .apkg archive."""
    if manifest_path is None:
        found = _find_manifest(Path.cwd())
        if found is None:
            print(f"error: no {MANIFEST_NAME} found", file=sys.stderr)
            return 1
        manifest_path = found

    manifest, errors = load_manifest(manifest_path)
    if errors:
        print("error: manifest validation failed:", file=sys.stderr)
        _print_errors(errors)
        return 1
    if manifest is None:
        return 1

    pkg_dir = manifest_path.parent
    dist_dir = out_dir or (pkg_dir / "dist")
    dist_dir.mkdir(parents=True, exist_ok=True)

    artifact_name = f"{manifest.name}-{manifest.version}.apkg"
    artifact_path = dist_dir / artifact_name

    print(f"Building {manifest.name} v{manifest.version} ...")

    files = _collect_files(pkg_dir, manifest)
    if not files:
        print("error: no source files found", file=sys.stderr)
        return 1

    # Build checksums table
    checksums: dict[str, str] = {}
    for f in files:
        arc_path = _archive_path(pkg_dir, f, manifest)
        checksums[arc_path] = _sha256_file(f)

    # Build buildinfo
    buildinfo = {
        "name": manifest.name,
        "version": str(manifest.version),
        "built_at": _now_iso(),
        "source_file_count": len(files),
        "tool": "aster-pkg/0.1.0",
    }
    buildinfo_bytes = json.dumps(buildinfo, indent=2).encode()
    name_ver = f"{manifest.name}-{manifest.version}"
    checksums[f"{name_ver}/meta/buildinfo.json"] = _sha256_bytes(buildinfo_bytes)

    sha256sums_lines = "\n".join(f"{chk}  {path}" for path, chk in sorted(checksums.items())) + "\n"
    sha256sums_bytes = sha256sums_lines.encode()

    # Write archive (deterministic tar.gz — zstd optional)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        # Normalised fixed mtime for reproducibility
        fixed_mtime = 0

        def _add_bytes(arc_path: str, data: bytes) -> None:
            info = tarfile.TarInfo(name=arc_path)
            info.size = len(data)
            info.mtime = fixed_mtime
            info.mode = 0o644
            tf.addfile(info, io.BytesIO(data))

        # Source files in deterministic order
        for f in sorted(files, key=lambda p: _archive_path(pkg_dir, p, manifest)):
            arc_path = _archive_path(pkg_dir, f, manifest)
            info = tarfile.TarInfo(name=arc_path)
            info.size = f.stat().st_size
            info.mtime = fixed_mtime
            info.mode = 0o644
            with f.open("rb") as fh:
                tf.addfile(info, fh)

        # Metadata files
        _add_bytes(f"{name_ver}/meta/buildinfo.json", buildinfo_bytes)
        _add_bytes(f"{name_ver}/checksums/SHA256SUMS", sha256sums_bytes)

    artifact_bytes = buf.getvalue()
    artifact_path.write_bytes(artifact_bytes)
    artifact_checksum = _sha256_bytes(artifact_bytes)

    # Write sidecar checksum file
    checksum_file = artifact_path.with_suffix(".apkg.sha256")
    checksum_file.write_text(f"{artifact_checksum}  {artifact_name}\n")

    size_kb = len(artifact_bytes) / 1024
    print(f"\n  {artifact_path.relative_to(pkg_dir)}  ({size_kb:.1f} KB)")
    print(f"  {checksum_file.name}")
    print("\nBuild complete.")
    return 0


# ---------------------------------------------------------------------------
# aster pkg list (installed deps — stub for now)
# ---------------------------------------------------------------------------


def cmd_list(manifest_path: Path | None = None) -> int:
    """Implement `aster pkg list` — show declared dependencies."""
    if manifest_path is None:
        found = _find_manifest(Path.cwd())
        if found is None:
            print(f"error: no {MANIFEST_NAME} found", file=sys.stderr)
            return 1
        manifest_path = found

    manifest, errors = load_manifest(manifest_path)
    if errors:
        _print_errors(errors)
        return 1
    if manifest is None:
        return 1

    if not manifest.dependencies and not manifest.dev_dependencies:
        print("No dependencies declared.")
        return 0

    if manifest.dependencies:
        print("Dependencies:")
        for name, constraint in sorted(manifest.dependencies.items()):
            print(f"  {name:<20} {constraint}")

    if manifest.dev_dependencies:
        print("Dev dependencies:")
        for name, constraint in sorted(manifest.dev_dependencies.items()):
            print(f"  {name:<20} {constraint}")

    return 0
