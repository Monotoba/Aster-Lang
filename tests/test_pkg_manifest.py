"""Tests for the Aster package manifest loader and validator."""

from __future__ import annotations

from pathlib import Path

from aster_lang.pkg.manifest import (
    APKG001,
    APKG003,
    APKG004,
    APKG005,
    APKG006,
    APKG007,
    APKG008,
    APKG012,
    APKG017,
    Manifest,
    ManifestError,
    load_manifest_text,
)

# ---------------------------------------------------------------------------
# Minimal valid manifest
# ---------------------------------------------------------------------------

MINIMAL = """\
[package]
name = "mylib"
version = "1.0.0"
type = "library"
description = "A minimal test library for Aster."
license = "MIT"

[[package.authors]]
name = "Test Author"

[aster]
min_version = "0.1.0"

[lib]
entry = "src/mylib/lib.aster"
"""


def load(text: str, base_dir: Path | None = None) -> tuple[Manifest | None, list[ManifestError]]:
    return load_manifest_text(text, base_dir=base_dir)


def errors_for(text: str, base_dir: Path | None = None) -> list[str]:
    _, errs = load(text, base_dir=base_dir)
    return [e.code for e in errs]


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestValidManifest:
    def test_minimal_accepted(self) -> None:
        manifest, errs = load(MINIMAL)
        assert not errs
        assert manifest is not None
        assert manifest.name == "mylib"
        assert str(manifest.version) == "1.0.0"
        assert manifest.pkg_type == "library"
        assert manifest.authors[0].name == "Test Author"

    def test_full_manifest(self) -> None:
        text = """\
[package]
name = "httpkit"
version = "1.4.2"
type = "library"
description = "HTTP client library for Aster applications."
license = "MIT"
keywords = ["http", "network"]
categories = ["networking"]
supported_platforms = ["linux", "mac", "win"]
readme = "README.md"
repository = "https://github.com/example/httpkit"

[[package.authors]]
name = "Jane Smith"
email = "jane@example.org"
country = "US"

[aster]
min_version = "0.9.0"
max_version = "2.0.0"

[lib]
entry = "src/httpkit/lib.aster"

[dependencies]
json = "^1.2.0"
tls = ">=2.0.0,<3.0.0"

[dev-dependencies]
testkit = "^0.8.0"
"""
        manifest, errs = load(text)
        assert not errs
        assert manifest is not None
        assert manifest.keywords == ["http", "network"]
        assert manifest.supported_platforms == ["linux", "mac", "win"]
        assert "json" in manifest.dependencies
        assert "testkit" in manifest.dev_dependencies

    def test_application_type(self) -> None:
        text = MINIMAL.replace('type = "library"', 'type = "application"')
        text = text.replace("[lib]", "[app]")
        manifest, errs = load(text)
        assert not errs
        assert manifest is not None
        assert manifest.pkg_type == "application"

    def test_tool_type(self) -> None:
        text = MINIMAL.replace('type = "library"', 'type = "tool"')
        text = text.replace("[lib]", "[tool]")
        manifest, errs = load(text)
        assert not errs

    def test_multiple_authors(self) -> None:
        text = MINIMAL + '\n[[package.authors]]\nname = "Second Author"\n'
        manifest, errs = load(text)
        assert not errs
        assert manifest is not None
        assert len(manifest.authors) == 2


# ---------------------------------------------------------------------------
# Package name validation (APKG003, APKG017)
# ---------------------------------------------------------------------------


class TestPackageNameValidation:
    def _swap_name(self, name: str) -> str:
        return MINIMAL.replace('name = "mylib"', f'name = "{name}"')

    def test_valid_name(self) -> None:
        assert not errors_for(self._swap_name("my-lib"))

    def test_uppercase_rejected(self) -> None:
        assert APKG003 in errors_for(self._swap_name("MyLib"))

    def test_starts_with_digit_rejected(self) -> None:
        assert APKG003 in errors_for(self._swap_name("1parser"))

    def test_underscore_rejected(self) -> None:
        assert APKG003 in errors_for(self._swap_name("my_lib"))

    def test_adjacent_hyphens_rejected(self) -> None:
        assert APKG003 in errors_for(self._swap_name("my--lib"))

    def test_trailing_hyphen_rejected(self) -> None:
        assert APKG003 in errors_for(self._swap_name("mylib-"))

    def test_single_char_rejected(self) -> None:
        assert APKG003 in errors_for(self._swap_name("a"))

    def test_reserved_aster(self) -> None:
        assert APKG017 in errors_for(self._swap_name("aster"))

    def test_reserved_std(self) -> None:
        assert APKG017 in errors_for(self._swap_name("std"))

    def test_reserved_core(self) -> None:
        assert APKG017 in errors_for(self._swap_name("core"))


# ---------------------------------------------------------------------------
# Version validation (APKG004)
# ---------------------------------------------------------------------------


class TestVersionValidation:
    def test_invalid_version(self) -> None:
        text = MINIMAL.replace('version = "1.0.0"', 'version = "1.0"')
        assert APKG004 in errors_for(text)

    def test_prerelease_accepted(self) -> None:
        text = MINIMAL.replace('version = "1.0.0"', 'version = "1.0.0-alpha.1"')
        assert not errors_for(text)


# ---------------------------------------------------------------------------
# Author validation (APKG006)
# ---------------------------------------------------------------------------


class TestAuthorValidation:
    def test_empty_authors_rejected(self) -> None:
        text = MINIMAL.replace('[[package.authors]]\nname = "Test Author"\n', "")
        assert APKG006 in errors_for(text)

    def test_author_missing_name_rejected(self) -> None:
        text = MINIMAL.replace('name = "Test Author"', 'email = "a@b.com"')
        assert APKG006 in errors_for(text)


# ---------------------------------------------------------------------------
# Platform validation (APKG007)
# ---------------------------------------------------------------------------


class TestPlatformValidation:
    def test_valid_platforms(self) -> None:
        text = MINIMAL + '\nsupported_platforms = ["linux", "mac"]\n'
        # Insert into [package] section
        text = MINIMAL.replace(
            'license = "MIT"',
            'license = "MIT"\nsupported_platforms = ["linux", "mac"]',
        )
        assert not errors_for(text)

    def test_invalid_platform(self) -> None:
        text = MINIMAL.replace(
            'license = "MIT"',
            'license = "MIT"\nsupported_platforms = ["linux", "windows"]',
        )
        assert APKG007 in errors_for(text)

    def test_duplicate_platform(self) -> None:
        text = MINIMAL.replace(
            'license = "MIT"',
            'license = "MIT"\nsupported_platforms = ["linux", "linux"]',
        )
        assert APKG007 in errors_for(text)


# ---------------------------------------------------------------------------
# Aster version compatibility (APKG012)
# ---------------------------------------------------------------------------


class TestAsterCompat:
    def test_missing_min_version(self) -> None:
        text = MINIMAL.replace('min_version = "0.1.0"', "")
        assert APKG012 in errors_for(text)

    def test_max_lt_min_rejected(self) -> None:
        text = MINIMAL.replace(
            'min_version = "0.1.0"',
            'min_version = "1.0.0"\nmax_version = "0.9.0"',
        )
        assert APKG012 in errors_for(text)

    def test_max_eq_min_accepted(self) -> None:
        text = MINIMAL.replace(
            'min_version = "0.1.0"',
            'min_version = "1.0.0"\nmax_version = "1.0.0"',
        )
        assert not errors_for(text)


# ---------------------------------------------------------------------------
# Role table validation (APKG001, APKG008)
# ---------------------------------------------------------------------------


class TestRoleValidation:
    def test_missing_lib_table(self) -> None:
        text = MINIMAL.replace('[lib]\nentry = "src/mylib/lib.aster"\n', "")
        codes = errors_for(text)
        assert APKG001 in codes

    def test_missing_entry_field(self) -> None:
        text = MINIMAL.replace('entry = "src/mylib/lib.aster"', "")
        codes = errors_for(text)
        assert APKG008 in codes

    def test_entry_existence_checked_when_base_dir_given(self, tmp_path: Path) -> None:
        # entry file does not exist → APKG008
        _, errs = load(MINIMAL, base_dir=tmp_path)
        assert any(e.code == APKG008 for e in errs)

    def test_entry_existence_ok_when_file_present(self, tmp_path: Path) -> None:
        entry = tmp_path / "src" / "mylib"
        entry.mkdir(parents=True)
        (entry / "lib.aster").write_text("fn main(): pass\n")
        _, errs = load(MINIMAL, base_dir=tmp_path)
        assert not any(e.code == APKG008 for e in errs)


# ---------------------------------------------------------------------------
# Dependency validation (APKG005)
# ---------------------------------------------------------------------------


class TestDependencyValidation:
    def test_valid_dependency(self) -> None:
        text = MINIMAL + '\n[dependencies]\njson = "^1.2.0"\n'
        manifest, errs = load(text)
        assert not errs
        assert manifest is not None
        assert "json" in manifest.dependencies

    def test_invalid_constraint(self) -> None:
        text = MINIMAL + '\n[dependencies]\njson = ">>1.0.0"\n'
        assert APKG005 in errors_for(text)

    def test_invalid_dep_value_type(self) -> None:
        text = MINIMAL + "\n[dependencies]\njson = 123\n"
        assert APKG005 in errors_for(text)
