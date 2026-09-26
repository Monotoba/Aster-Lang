from __future__ import annotations

import tomllib
from pathlib import Path

REPOSITORY_URL = "https://github.com/Monotoba/Aster-Lang"


def test_lsp_dependencies_are_available_to_users_and_contributors() -> None:
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    extras = metadata["project"]["optional-dependencies"]

    for dependency in ("lsprotocol", "pygls"):
        assert any(item.startswith(dependency) for item in extras["lsp"])
        assert any(item.startswith(dependency) for item in extras["dev"])


def test_package_metadata_identifies_the_project_and_maintainer() -> None:
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]

    assert metadata["authors"] == [{"name": "R Morgan"}]
    assert metadata["license"] == "GPL-2.0-only"
    assert metadata["license-files"] == ["LICENSE"]
    assert metadata["urls"]["Repository"] == REPOSITORY_URL
    assert metadata["urls"]["Issues"] == f"{REPOSITORY_URL}/issues"
    assert {"compiler", "interpreter", "programming-language"} <= set(metadata["keywords"])


def test_readme_displays_project_status_badges() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "actions/workflows/ci.yml/badge.svg" in readme
    assert "github/v/release/Monotoba/Aster-Lang" in readme
    assert "github/license/Monotoba/Aster-Lang" in readme
