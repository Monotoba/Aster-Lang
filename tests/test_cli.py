from __future__ import annotations

from aster_lang.cli import main


def test_version_command_returns_zero() -> None:
    assert main(["version"]) == 0
