"""Aster package manifest loader and validator.

Implements the aster.toml specification from PACKAGE-MANAGER-DESIGN.md section 10.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from aster_lang.pkg.semver import Constraint, SemVerError, Version, parse_constraint, parse_version

# ---------------------------------------------------------------------------
# Error codes (from spec section 22.4)
# ---------------------------------------------------------------------------

APKG001 = "APKG001"  # invalid manifest
APKG002 = "APKG002"  # missing required field
APKG003 = "APKG003"  # invalid package name
APKG004 = "APKG004"  # invalid version
APKG005 = "APKG005"  # invalid dependency constraint
APKG006 = "APKG006"  # missing author record
APKG007 = "APKG007"  # invalid supported platform
APKG008 = "APKG008"  # entry file missing
APKG012 = "APKG012"  # incompatible Aster version
APKG017 = "APKG017"  # reserved package name

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_PLATFORMS: frozenset[str] = frozenset({"linux", "mac", "win"})
VALID_TYPES: frozenset[str] = frozenset({"library", "application", "tool"})
RESERVED_NAMES: frozenset[str] = frozenset(
    {
        "aster",
        "std",
        "core",
        "builtin",
        "registry",
        "system",
    }
)
_NAME_RE = re.compile(r"^[a-z](?:[a-z0-9]|-(?=[a-z0-9])){1,63}$")

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Author:
    name: str
    email: str = ""
    web_url: str = ""
    contact: str = ""
    country: str = ""
    organization: str = ""


@dataclass
class AsterCompat:
    min_version: Version
    max_version: Version | None = None


@dataclass
class RoleEntry:
    """Entry point for lib / app / tool."""

    entry: str
    command: str = ""  # tool only


@dataclass
class Manifest:
    """Parsed and validated aster.toml manifest."""

    # [package]
    name: str
    version: Version
    pkg_type: str  # library | application | tool
    description: str
    license: str
    authors: list[Author]
    keywords: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    supported_platforms: list[str] = field(default_factory=list)
    repository: str = ""
    documentation: str = ""
    homepage: str = ""
    readme: str = ""
    changes: str = ""
    source_root: str = "src"

    # [aster]
    aster: AsterCompat | None = None

    # role table
    role: RoleEntry | None = None

    # [dependencies] / [dev-dependencies]
    dependencies: dict[str, Constraint] = field(default_factory=dict)
    dev_dependencies: dict[str, Constraint] = field(default_factory=dict)

    # raw TOML data (preserved for tooling)
    _raw: dict[str, object] = field(default_factory=dict, repr=False)


# ---------------------------------------------------------------------------
# Validation error
# ---------------------------------------------------------------------------


@dataclass
class ManifestError:
    code: str
    field: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message} (field: {self.field})"


# ---------------------------------------------------------------------------
# Loader / validator
# ---------------------------------------------------------------------------


class ManifestLoader:
    """Load and validate an aster.toml manifest."""

    def __init__(self) -> None:
        self.errors: list[ManifestError] = []

    def _err(self, code: str, fld: str, msg: str) -> None:
        self.errors.append(ManifestError(code=code, field=fld, message=msg))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_file(self, path: Path) -> Manifest | None:
        """Load and validate a manifest file. Returns None if unreadable."""
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            self._err(APKG001, "manifest", f"Cannot read {path}: {exc}")
            return None
        return self.load_text(text, base_dir=path.parent)

    def load_text(self, text: str, *, base_dir: Path | None = None) -> Manifest | None:
        """Parse and validate TOML text. Returns None if TOML is invalid."""
        try:
            raw = tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            self._err(APKG001, "manifest", f"TOML parse error: {exc}")
            return None
        return self._build(raw, base_dir=base_dir)

    # ------------------------------------------------------------------
    # Internal builder
    # ------------------------------------------------------------------

    def _build(self, raw: dict[str, object], *, base_dir: Path | None) -> Manifest | None:
        pkg = raw.get("package", {})
        if not isinstance(pkg, dict):
            self._err(APKG001, "package", "[package] must be a table")
            return None

        name = self._req_str(pkg, "package.name", APKG002)
        if name:
            self._validate_name(name)

        version_str = self._req_str(pkg, "package.version", APKG002)
        version = self._parse_version(version_str or "", "package.version")

        pkg_type = self._req_str(pkg, "package.type", APKG002)
        if pkg_type and pkg_type not in VALID_TYPES:
            self._err(APKG001, "package.type", f"must be one of: {', '.join(sorted(VALID_TYPES))}")
            pkg_type = ""

        description = self._req_str(pkg, "package.description", APKG002)
        license_ = self._req_str(pkg, "package.license", APKG002)

        authors = self._load_authors(pkg)
        keywords = self._str_list(pkg, "package.keywords", max_items=20, max_len=32)
        categories = self._str_list(pkg, "package.categories", max_items=10)
        platforms = self._load_platforms(pkg)

        aster_compat = self._load_aster_compat(raw)
        role = self._load_role(raw, pkg_type or "", base_dir)
        dependencies = self._load_deps(raw, "dependencies")
        dev_dependencies = self._load_deps(raw, "dev-dependencies")

        if self.errors:
            # Return a partial manifest so callers can inspect errors but
            # still access parsed fields that succeeded.
            pass

        return Manifest(
            name=name or "",
            version=version or Version(0, 0, 0),
            pkg_type=pkg_type or "",
            description=description or "",
            license=license_ or "",
            authors=authors,
            keywords=keywords,
            categories=categories,
            supported_platforms=platforms,
            repository=self._opt_str(pkg, "package.repository"),
            documentation=self._opt_str(pkg, "package.documentation"),
            homepage=self._opt_str(pkg, "package.homepage"),
            readme=self._opt_str(pkg, "package.readme"),
            changes=self._opt_str(pkg, "package.changes"),
            source_root=self._opt_str(pkg, "package.source_root") or "src",
            aster=aster_compat,
            role=role,
            dependencies=dependencies,
            dev_dependencies=dev_dependencies,
            _raw=raw,
        )

    # ------------------------------------------------------------------
    # Field helpers
    # ------------------------------------------------------------------

    def _req_str(self, table: dict[str, object], key: str, code: str) -> str | None:
        short = key.split(".")[-1]
        val = table.get(short)
        if val is None:
            self._err(code, key, f"'{key}' is required")
            return None
        if not isinstance(val, str) or not val.strip():
            self._err(code, key, f"'{key}' must be a non-empty string")
            return None
        return val.strip()

    def _opt_str(self, table: dict[str, object], key: str) -> str:
        short = key.split(".")[-1]
        val = table.get(short, "")
        return str(val).strip() if isinstance(val, str) else ""

    def _str_list(
        self,
        table: dict[str, object],
        key: str,
        *,
        max_items: int = 100,
        max_len: int = 200,
    ) -> list[str]:
        short = key.split(".")[-1]
        raw = table.get(short, [])
        if not isinstance(raw, list):
            self._err(APKG001, key, f"'{key}' must be a list of strings")
            return []
        result: list[str] = []
        seen: set[str] = set()
        for item in raw[:max_items]:
            if not isinstance(item, str):
                self._err(APKG001, key, f"'{key}' entries must be strings")
                continue
            item = item.strip()
            if len(item) > max_len:
                self._err(APKG001, key, f"'{key}' entry too long: {item!r}")
                continue
            if item in seen:
                self._err(APKG001, key, f"'{key}' has duplicate entry: {item!r}")
                continue
            seen.add(item)
            result.append(item)
        return result

    def _validate_name(self, name: str) -> None:
        if name in RESERVED_NAMES:
            self._err(APKG017, "package.name", f"'{name}' is a reserved package name")
            return
        if not _NAME_RE.match(name):
            self._err(
                APKG003,
                "package.name",
                f"'{name}' is not a valid package name "
                f"(must match ^[a-z][a-z0-9-]{{1,63}}$ with no adjacent hyphens)",
            )

    def _parse_version(self, text: str, field_name: str) -> Version | None:
        if not text:
            return None
        try:
            return parse_version(text)
        except SemVerError as exc:
            self._err(APKG004, field_name, str(exc))
            return None

    def _load_authors(self, pkg: dict[str, object]) -> list[Author]:
        raw = pkg.get("authors", [])
        if not isinstance(raw, list) or len(raw) == 0:
            self._err(
                APKG006,
                "package.authors",
                "package.authors must be a non-empty list of author records",
            )
            return []
        authors: list[Author] = []
        for i, item in enumerate(raw):
            if not isinstance(item, dict):
                self._err(APKG006, f"package.authors[{i}]", f"authors[{i}] must be a table")
                continue
            aname = item.get("name", "")
            if not isinstance(aname, str) or not aname.strip():
                self._err(
                    APKG006,
                    f"package.authors[{i}].name",
                    f"authors[{i}].name is required and must be non-empty",
                )
                continue
            authors.append(
                Author(
                    name=aname.strip(),
                    email=str(item.get("email", "")).strip(),
                    web_url=str(item.get("web_url", "")).strip(),
                    contact=str(item.get("contact", "")).strip(),
                    country=str(item.get("country", "")).strip(),
                    organization=str(item.get("organization", "")).strip(),
                )
            )
        return authors

    def _load_platforms(self, pkg: dict[str, object]) -> list[str]:
        raw = pkg.get("supported_platforms", [])
        if not isinstance(raw, list):
            self._err(APKG007, "package.supported_platforms", "supported_platforms must be a list")
            return []
        seen: set[str] = set()
        result: list[str] = []
        for p in raw:
            if not isinstance(p, str) or p not in VALID_PLATFORMS:
                self._err(
                    APKG007,
                    "package.supported_platforms",
                    f"unsupported platform {p!r} — allowed: linux, mac, win",
                )
                continue
            if p in seen:
                self._err(
                    APKG007, "package.supported_platforms", f"duplicate platform entry: {p!r}"
                )
                continue
            seen.add(p)
            result.append(p)
        return result

    def _load_aster_compat(self, raw: dict[str, object]) -> AsterCompat | None:
        aster = raw.get("aster", {})
        if not isinstance(aster, dict):
            self._err(APKG001, "aster", "[aster] must be a table")
            return None
        min_str = aster.get("min_version")
        if not isinstance(min_str, str) or not min_str.strip():
            self._err(APKG012, "aster.min_version", "aster.min_version is required")
            return None
        min_ver = self._parse_version(min_str.strip(), "aster.min_version")
        if min_ver is None:
            return None
        max_ver: Version | None = None
        max_str = aster.get("max_version")
        if isinstance(max_str, str) and max_str.strip():
            max_ver = self._parse_version(max_str.strip(), "aster.max_version")
            if max_ver is not None and max_ver < min_ver:
                self._err(
                    APKG012, "aster.max_version", "aster.max_version must be >= aster.min_version"
                )
        return AsterCompat(min_version=min_ver, max_version=max_ver)

    def _load_role(
        self,
        raw: dict[str, object],
        pkg_type: str,
        base_dir: Path | None,
    ) -> RoleEntry | None:
        role_map = {"library": "lib", "application": "app", "tool": "tool"}
        key = role_map.get(pkg_type)
        if not key:
            return None
        table = raw.get(key)
        if table is None:
            self._err(APKG001, key, f"package.type='{pkg_type}' requires a [{key}] table")
            return None
        if not isinstance(table, dict):
            self._err(APKG001, key, f"[{key}] must be a table")
            return None
        entry_str = table.get("entry")
        if not isinstance(entry_str, str) or not entry_str.strip():
            self._err(APKG008, f"{key}.entry", f"[{key}].entry is required")
            return None
        entry = entry_str.strip()
        if base_dir is not None:
            entry_path = base_dir / entry
            if not entry_path.exists():
                self._err(APKG008, f"{key}.entry", f"entry file does not exist: {entry}")
        command = str(table.get("command", "")).strip()
        return RoleEntry(entry=entry, command=command)

    def _load_deps(
        self,
        raw: dict[str, object],
        section: str,
    ) -> dict[str, Constraint]:
        table = raw.get(section, {})
        if not isinstance(table, dict):
            self._err(APKG001, section, f"[{section}] must be a table")
            return {}
        result: dict[str, Constraint] = {}
        for dep_name, spec in table.items():
            if not isinstance(spec, str):
                self._err(
                    APKG005,
                    f"{section}.{dep_name}",
                    f"dependency '{dep_name}' value must be a constraint string",
                )
                continue
            try:
                result[dep_name] = parse_constraint(spec)
            except SemVerError as exc:
                self._err(APKG005, f"{section}.{dep_name}", str(exc))
        return result


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------


def load_manifest(path: Path) -> tuple[Manifest | None, list[ManifestError]]:
    """Load and validate a manifest file.

    Returns ``(manifest, errors)``.  Errors is empty on success.
    A non-None manifest may still have errors if partial parsing succeeded.
    """
    loader = ManifestLoader()
    manifest = loader.load_file(path)
    return manifest, loader.errors


def load_manifest_text(
    text: str, *, base_dir: Path | None = None
) -> tuple[Manifest | None, list[ManifestError]]:
    """Load and validate manifest from a TOML string."""
    loader = ManifestLoader()
    manifest = loader.load_text(text, base_dir=base_dir)
    return manifest, loader.errors
