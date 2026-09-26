from __future__ import annotations

import tomllib
from pathlib import Path


def test_lsp_dependencies_are_available_to_users_and_contributors() -> None:
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    extras = metadata["project"]["optional-dependencies"]

    for dependency in ("lsprotocol", "pygls"):
        assert any(item.startswith(dependency) for item in extras["lsp"])
        assert any(item.startswith(dependency) for item in extras["dev"])
